import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends

from codexa.app.di import (
    get_ast_parser,
    get_code_retriever,
    get_dependency_graph_builder,
    get_index_service,
    get_index_status_registry,
    get_repo_state_store,
    get_repository_loader,
)
from codexa.controllers.repos_controller import purge_repo
from codexa.schemas.analyze import AnalyzeRepoRequest, AnalyzeRepoResponse
from codexa.services.dependency.interfaces import DependencyGraphBuilder
from codexa.services.ingestion.git_loader import _normalize_repo_url
from codexa.services.ingestion.interfaces import RepositoryLoader
from codexa.services.parsing.interfaces import AstParser
from codexa.services.retrieval.faiss_retriever import FaissCodeRetriever
from codexa.services.retrieval.indexing import CodeIndexService
from codexa.services.state.index_status import IndexStatusRegistry
from codexa.services.state.repo_state_store import RepoState, RepoStateStore

router = APIRouter(prefix="/analyze-repo", tags=["analysis"])
logger = logging.getLogger(__name__)


def _run_full_analysis(
    repo_url: str,
    repo_id: str,
    loader: RepositoryLoader,
    parser: AstParser,
    graph_builder: DependencyGraphBuilder,
    index_service: CodeIndexService,
    state_store: RepoStateStore,
    status_registry: IndexStatusRegistry,
) -> None:
    try:
        status_registry.set(repo_id, "processing", stage="cloning")
        repo = loader.load(repo_url, repo_id=repo_id)
        status_registry.set(repo_id, "processing", stage="parsing")
        parsed = parser.parse_repository(repo)
        dependency_graph = graph_builder.build_import_graph(parsed)
        state_store.save(
            repo_id,
            RepoState(
                parsed_repo=parsed,
                import_graph=dependency_graph,
                root_path=repo.root_path,
                name=repo.name,
                url=repo.url,
            ),
        )
        status_registry.set(repo_id, "processing", stage="embedding", file_count=len(parsed.files))
        index_service.index_repository(repo, parsed)
        status_registry.set(
            repo_id,
            "ready",
            file_count=len(parsed.files),
        )
    except Exception as e:
        logger.error("Analysis failed for %s: %s", repo_url, e)
        status_registry.set(repo_id, "failed", error=str(e))


@router.post("", response_model=AnalyzeRepoResponse)
def analyze_repo(
    request: AnalyzeRepoRequest,
    background_tasks: BackgroundTasks,
    loader: RepositoryLoader = Depends(get_repository_loader),
    parser: AstParser = Depends(get_ast_parser),
    graph_builder: DependencyGraphBuilder = Depends(get_dependency_graph_builder),
    index_service: CodeIndexService = Depends(get_index_service),
    state_store: RepoStateStore = Depends(get_repo_state_store),
    status_registry: IndexStatusRegistry = Depends(get_index_status_registry),
    retriever: FaissCodeRetriever = Depends(get_code_retriever),
) -> AnalyzeRepoResponse:
    # Dedup: if this URL was already indexed, remove the old copy first.
    normalized = _normalize_repo_url(str(request.repo_url))
    for existing_id in list(state_store.list_repo_ids()):
        existing = state_store.get(existing_id)
        if existing and existing.url and _normalize_repo_url(existing.url) == normalized:
            purge_repo(existing_id, state_store, retriever, status_registry)

    repo_id = str(uuid.uuid4())
    status_registry.set(repo_id, "processing", stage="queued")
    background_tasks.add_task(
        _run_full_analysis,
        str(request.repo_url),
        repo_id,
        loader,
        parser,
        graph_builder,
        index_service,
        state_store,
        status_registry,
    )
    return AnalyzeRepoResponse(
        repository_id=repo_id,
        file_count=0,
        dependency_edges=0,
        indexing_status="processing",
    )


@router.get("/status/{repo_id}")
def index_status(
    repo_id: str,
    retriever: FaissCodeRetriever = Depends(get_code_retriever),
    state_store: RepoStateStore = Depends(get_repo_state_store),
    status_registry: IndexStatusRegistry = Depends(get_index_status_registry),
) -> dict:
    # In-memory registry is authoritative for repos indexed this session.
    info = status_registry.get(repo_id)
    if info:
        return {"repo_id": repo_id, "record_count": retriever.record_count(repo_id), **info}
    # Repos loaded from disk on a previous run: presence of an index/state = ready.
    record_count = retriever.record_count(repo_id)
    if record_count > 0 or state_store.get(repo_id) is not None:
        return {"repo_id": repo_id, "status": "ready", "record_count": record_count}
    return {"repo_id": repo_id, "status": "not_found", "record_count": 0}
