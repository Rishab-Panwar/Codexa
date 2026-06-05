import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    embedding_provider: str
    embedding_model: str
    index_dir: str
    state_dir: str
    llm_provider: str
    llm_model: str
    llm_temperature: float
    api_key: str | None
    auth_enabled: bool


def load_config() -> AppConfig:
    return AppConfig(
        embedding_provider=os.getenv("CODEXA_EMBEDDING_PROVIDER", "sentence"),
        embedding_model=os.getenv("CODEXA_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        index_dir=os.getenv("CODEXA_INDEX_DIR", ".codexa/indexes"),
        state_dir=os.getenv("CODEXA_STATE_DIR", ".codexa/state"),
        llm_provider=os.getenv("CODEXA_LLM_PROVIDER", "groq"),
        llm_model=os.getenv("CODEXA_LLM_MODEL", "llama-3.1-8b-instant"),
        llm_temperature=float(os.getenv("CODEXA_LLM_TEMPERATURE", "0.2")),
        api_key=os.getenv("CODEXA_API_KEY"),
        auth_enabled=os.getenv("CODEXA_AUTH_ENABLED", "false").lower() == "true",
    )
