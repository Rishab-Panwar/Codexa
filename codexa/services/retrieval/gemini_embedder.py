import os

try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover
    genai = None  # type: ignore

from codexa.services.retrieval.embedding import EmbeddingService

# text-embedding-004: 768-dim, strong retrieval quality, generous free tier.
_DEFAULT_MODEL = "models/text-embedding-004"
_BATCH = 100  # Gemini batchEmbedContents max per request


class GeminiEmbeddingService(EmbeddingService):
    def __init__(self, api_key: str | None = None, model_name: str = _DEFAULT_MODEL) -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._model_name = model_name
        self._configured = False

    def _ensure_configured(self) -> None:
        if genai is None:
            raise RuntimeError(
                "google-generativeai is not installed. "
                "Set CODEXA_EMBEDDING_PROVIDER=fastembed/hash or install google-generativeai."
            )
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        if not self._configured:
            genai.configure(api_key=self._api_key)
            self._configured = True

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._ensure_configured()
        vectors: list[list[float]] = []
        for i in range(0, len(texts), _BATCH):
            # Gemini rejects empty content — substitute a space to keep alignment.
            batch = [t if t.strip() else " " for t in texts[i : i + _BATCH]]
            resp = genai.embed_content(
                model=self._model_name,
                content=batch,
                task_type="retrieval_document",
            )
            vectors.extend(resp["embedding"])
        return vectors

    def embed_query(self, text: str) -> list[float]:
        self._ensure_configured()
        resp = genai.embed_content(
            model=self._model_name,
            content=text if text.strip() else " ",
            task_type="retrieval_query",
        )
        return resp["embedding"]
