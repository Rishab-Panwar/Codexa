import logging
import os
import time

try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except Exception:  # pragma: no cover
    genai = None  # type: ignore
    types = None  # type: ignore

from codexa.services.retrieval.embedding import EmbeddingService

# gemini-embedding-001: current GA model. Defaults to 3072-dim; we truncate to
# 768 (Matryoshka) for a lean index — FAISS re-normalizes, which truncated
# Gemini vectors require.
_DEFAULT_MODEL = "gemini-embedding-001"
_OUTPUT_DIM = 768
_BATCH = 100  # Gemini batch embed max per request
_MAX_RETRIES = 6
_INTER_BATCH_SLEEP = 0.5  # gentle throttle to stay under the free-tier RPM


class GeminiEmbeddingService(EmbeddingService):
    def __init__(self, api_key: str | None = None, model_name: str = _DEFAULT_MODEL) -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._model_name = model_name
        self._client = None
        self._logger = logging.getLogger(__name__)

    def _get_client(self):
        if genai is None:
            raise RuntimeError(
                "google-genai is not installed. Set CODEXA_EMBEDDING_PROVIDER=fastembed/hash or install google-genai."
            )
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _embed_with_retry(self, contents: list[str], task_type: str):
        client = self._get_client()
        config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=_OUTPUT_DIM)
        delay = 2.0
        for attempt in range(_MAX_RETRIES):
            try:
                return client.models.embed_content(model=self._model_name, contents=contents, config=config)
            except Exception as e:
                is_rate_limit = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                if is_rate_limit and attempt < _MAX_RETRIES - 1:
                    self._logger.warning("Gemini rate limited; retrying in %.0fs", delay)
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for i in range(0, len(texts), _BATCH):
            # Gemini rejects empty content — substitute a space to keep alignment.
            batch = [t if t.strip() else " " for t in texts[i : i + _BATCH]]
            resp = self._embed_with_retry(batch, "RETRIEVAL_DOCUMENT")
            vectors.extend([embedding.values for embedding in resp.embeddings])
            if i + _BATCH < len(texts):
                time.sleep(_INTER_BATCH_SLEEP)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        resp = self._embed_with_retry([text if text.strip() else " "], "RETRIEVAL_QUERY")
        return resp.embeddings[0].values
