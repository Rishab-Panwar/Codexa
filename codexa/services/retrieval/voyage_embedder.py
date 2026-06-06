import logging
import os
import time

try:
    import voyageai  # type: ignore
except Exception:  # pragma: no cover
    voyageai = None  # type: ignore

from codexa.services.retrieval.embedding import EmbeddingService

# voyage-code-3: purpose-built for code retrieval, 1024-dim by default.
_DEFAULT_MODEL = "voyage-code-3"
_BATCH = 64  # stay well under Voyage's per-request text/token caps
_MAX_RETRIES = 6
_INTER_BATCH_SLEEP = 0.3


class VoyageEmbeddingService(EmbeddingService):
    def __init__(self, api_key: str | None = None, model_name: str = _DEFAULT_MODEL) -> None:
        self._api_key = api_key or os.getenv("VOYAGE_API_KEY")
        self._model_name = model_name
        self._client = None
        self._logger = logging.getLogger(__name__)

    def _get_client(self):
        if voyageai is None:
            raise RuntimeError(
                "voyageai is not installed. Set CODEXA_EMBEDDING_PROVIDER=fastembed/hash or install voyageai."
            )
        if not self._api_key:
            raise RuntimeError("VOYAGE_API_KEY is not set.")
        if self._client is None:
            self._client = voyageai.Client(api_key=self._api_key)
        return self._client

    def _embed_with_retry(self, contents: list[str], input_type: str):
        client = self._get_client()
        delay = 2.0
        for attempt in range(_MAX_RETRIES):
            try:
                return client.embed(contents, model=self._model_name, input_type=input_type)
            except Exception as e:
                is_rate_limit = "429" in str(e) or "rate" in str(e).lower()
                if is_rate_limit and attempt < _MAX_RETRIES - 1:
                    self._logger.warning("Voyage rate limited; retrying in %.0fs", delay)
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for i in range(0, len(texts), _BATCH):
            # Voyage rejects empty strings — substitute a space to keep alignment.
            batch = [t if t.strip() else " " for t in texts[i : i + _BATCH]]
            result = self._embed_with_retry(batch, "document")
            vectors.extend(result.embeddings)
            if i + _BATCH < len(texts):
                time.sleep(_INTER_BATCH_SLEEP)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        result = self._embed_with_retry([text if text.strip() else " "], "query")
        return result.embeddings[0]
