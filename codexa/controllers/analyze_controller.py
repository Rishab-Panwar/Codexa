import uuid

from fastapi import APIRouter, BackgroundTasks, Depends

from codexa.app.di import (
    get_ast_parser,
    get_dependency_graph_builder,
    get_index_service,
    get_repo_state_store,
    get_repository_loader,
)
from codexa.schemas.analyze import AnalyzeRepoRequest, AnalyzeRepoResponse
from codexa.services.dependency.interfaces import DependencyGraphBuilder
from codexa.services.ingestion.interfaces import RepositoryLoader
from codexa.services.parsing.interfaces import AstParser
from codexa.services.retrieval.indexing import CodeIndexService
from codexa.services.state.repo_state_store import RepoState, RepoStateStore

router = APIRouter(prefix="/analyze-repo", tags=["analysis"])


def _run_full_analysis(
    repo_url: str,
    repo_id: str,
    loader: RepositoryLoader,
    parser: AstParser,
    graph_builder: DependencyGraphBuilder,
    index_service: CodeIndexService,
    state_store: RepoStateStore,
) -> None:
    try:
        repo = loader.load(repo_url, repo_id=repo_id)
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
        index_service.index_repository(repo, parsed)
    except Exception as e:
        import logging

        logging.getLogger(__name__).error("Analysis failed for %s: %s", repo_url, e)


@router.post("", response_model=AnalyzeRepoResponse)
def analyze_repo(
    request: AnalyzeRepoRequest,
    background_tasks: BackgroundTasks,
    loader: RepositoryLoader = Depends(get_repository_loader),
    parser: AstParser = Depends(get_ast_parser),
    graph_builder: DependencyGraphBuilder = Depends(get_dependency_graph_builder),
    index_service: CodeIndexService = Depends(get_index_service),
    state_store: RepoStateStore = Depends(get_repo_state_store),
) -> AnalyzeRepoResponse:
    repo_id = str(uuid.uuid4())
    background_tasks.add_task(
        _run_full_analysis,
        str(request.repo_url),
        repo_id,
        loader,
        parser,
        graph_builder,
        index_service,
        state_store,
    )
    return AnalyzeRepoResponse(
        repository_id=repo_id,
        file_count=0,
        dependency_edges=0,
        indexing_status="processing",
    )
