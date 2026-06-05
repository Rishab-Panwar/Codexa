from functools import lru_cache
from pathlib import Path

from codexa.services.agents.coding_mentor_agent import CodingMentorAgent
from codexa.services.agents.memory_agent import MemoryAgent
from codexa.services.agents.orchestration import AgentOrchestrator
from codexa.services.agents.planner_agent import PlannerAgent
from codexa.services.agents.repo_analyst_agent import RepoAnalystAgent
from codexa.services.agents.retrieval_agent import RetrievalAgent
from codexa.services.dependency.import_graph_builder import ImportGraphBuilder
from codexa.services.ingestion.git_loader import GitRepositoryLoader
from codexa.services.llm.provider import LlmProvider
from codexa.services.memory.interfaces import MemoryStore
from codexa.services.memory.json_store import JsonMemoryStore
from codexa.services.parsing.tree_sitter_parser import TreeSitterAstParser
from codexa.services.qa.answer_service import AnswerService
from codexa.services.qa.explain_service import CodeExplainService
from codexa.services.retrieval.faiss_retriever import FaissCodeRetriever
from codexa.services.retrieval.hash_embedder import HashEmbeddingService
from codexa.services.retrieval.indexing import CodeIndexService
from codexa.services.retrieval.sentence_transformer_embedder import (
    SentenceTransformerEmbeddingService,
)
from codexa.services.state.repo_state_store import RepoStateStore
from codexa.utils.config import AppConfig, load_config


@lru_cache
def get_repository_loader() -> GitRepositoryLoader:
    return GitRepositoryLoader()


@lru_cache
def get_ast_parser() -> TreeSitterAstParser:
    return TreeSitterAstParser()


@lru_cache
def get_dependency_graph_builder() -> ImportGraphBuilder:
    return ImportGraphBuilder()


@lru_cache
def get_code_retriever() -> FaissCodeRetriever:
    config = get_config()
    return FaissCodeRetriever(base_dir=config.index_dir)


@lru_cache
def get_embedder() -> SentenceTransformerEmbeddingService | HashEmbeddingService:
    config = get_config()
    if config.embedding_provider == "hash":
        return HashEmbeddingService()
    return SentenceTransformerEmbeddingService(model_name=config.embedding_model)


@lru_cache
def get_index_service() -> CodeIndexService:
    return CodeIndexService(embedder=get_embedder(), retriever=get_code_retriever())


@lru_cache
def get_answer_service() -> AnswerService:
    return AnswerService(
        retriever=get_code_retriever(),
        embedder=get_embedder(),
        llm=get_llm_provider().get_chat_model(),
    )


@lru_cache
def get_explain_service() -> CodeExplainService:
    return CodeExplainService(state_store=get_repo_state_store(), llm=get_llm_provider().get_chat_model())


@lru_cache
def get_memory_store() -> MemoryStore:
    config = get_config()
    # Ensure state directory exists
    Path(config.state_dir).mkdir(parents=True, exist_ok=True)
    memory_file = Path(config.state_dir) / "agent_memory.json"
    return JsonMemoryStore(file_path=str(memory_file))


@lru_cache
def get_agent_orchestrator() -> AgentOrchestrator:
    llm = get_llm_provider().get_chat_model()
    answer_service = get_answer_service()
    repo_state_store = get_repo_state_store()
    memory_store = get_memory_store()

    planner = PlannerAgent(llm=llm)
    retrieval_agent = RetrievalAgent(answer_service=answer_service)
    analyst_agent = RepoAnalystAgent(state_store=repo_state_store, llm=llm)
    mentor_agent = CodingMentorAgent(answer_service=answer_service, llm=llm)
    memory_agent = MemoryAgent(memory_store=memory_store)

    return AgentOrchestrator(
        planner=planner,
        retrieval_agent=retrieval_agent,
        analyst_agent=analyst_agent,
        mentor_agent=mentor_agent,
        memory_agent=memory_agent,
        memory_store=memory_store,
    )


@lru_cache
def get_repo_state_store() -> RepoStateStore:
    config = get_config()
    return RepoStateStore(base_dir=config.state_dir)


@lru_cache
def get_config() -> AppConfig:
    return load_config()


@lru_cache
def get_llm_provider() -> LlmProvider:
    return LlmProvider(get_config())
