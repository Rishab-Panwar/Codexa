import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except Exception:  # pragma: no cover
    genai = None  # type: ignore
    types = None  # type: ignore

from codexa.services.retrieval.embedding import EmbeddingService

# Vertex AI text embeddings. Routes through Vertex AI generative-AI SKUs (uses
# GCP IAM/ADC auth, not an API key) — higher quotas than the AI Studio free
# tier, and billed under Vertex AI (potentially covered by GenAI credits).
_DEFAULT_MODEL = "text-embedding-004"  # 768-dim
_BATCH = 100  # max texts per request
_MAX_RETRIES = 5
# Vertex caps each embed request at 20k tokens total; batch by estimated tokens
# (chars/3 is a conservative code estimate) and truncate oversized snippets.
_CHARS_PER_TOKEN = 3
_MAX_REQUEST_TOKENS = 18000
_MAX_TEXT_TOKENS = 2000
_CONCURRENCY = 8  # parallel embed requests (retry/backoff handles any throttling)


class VertexEmbeddingService(EmbeddingService):
    def __init__(
        self,
        project: str | None = None,
        location: str | None = None,
        model_name: str = _DEFAULT_MODEL,
    ) -> None:
        self._project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self._location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self._model_name = model_name
        self._client = None
        self._logger = logging.getLogger(__name__)

    def _get_client(self):
        if genai is None:
            raise RuntimeError(
                "google-genai is not installed. Set CODEXA_EMBEDDING_PROVIDER=fastembed/hash or install google-genai."
            )
        if not self._project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set (required for Vertex AI).")
        if self._client is None:
            self._client = genai.Client(vertexai=True, project=self._project, location=self._location)
        return self._client

    def _embed_with_retry(self, contents: list[str], task_type: str):
        client = self._get_client()
        config = types.EmbedContentConfig(task_type=task_type)
        delay = 2.0
        for attempt in range(_MAX_RETRIES):
            try:
                return client.models.embed_content(model=self._model_name, contents=contents, config=config)
            except Exception as e:
                is_rate_limit = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                if is_rate_limit and attempt < _MAX_RETRIES - 1:
                    self._logger.warning("Vertex rate limited; retrying in %.0fs", delay)
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        resp = self._embed_with_retry(batch, "RETRIEVAL_DOCUMENT")
        return [embedding.values for embedding in resp.embeddings]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Split into token-bounded batches, then embed them concurrently
        # (preserving order) so ~50 requests don't run one-after-another.
        batches: list[list[str]] = []
        batch: list[str] = []
        batch_tokens = 0
        for text in texts:
            snippet = _truncate(text if text.strip() else " ")
            est = max(len(snippet) // _CHARS_PER_TOKEN, 1)
            if batch and (batch_tokens + est > _MAX_REQUEST_TOKENS or len(batch) >= _BATCH):
                batches.append(batch)
                batch, batch_tokens = [], 0
            batch.append(snippet)
            batch_tokens += est
        if batch:
            batches.append(batch)

        self._get_client()  # init once before threads to avoid a lazy-init race
        results: list[list[list[float]]] = [[] for _ in batches]
        with ThreadPoolExecutor(max_workers=_CONCURRENCY) as executor:
            future_to_idx = {executor.submit(self._embed_batch, b): i for i, b in enumerate(batches)}
            for future in as_completed(future_to_idx):
                results[future_to_idx[future]] = future.result()
        return [vector for batch_result in results for vector in batch_result]

    def embed_query(self, text: str) -> list[float]:
        resp = self._embed_with_retry([_truncate(text if text.strip() else " ")], "RETRIEVAL_QUERY")
        return resp.embeddings[0].values


def _truncate(text: str) -> str:
    max_chars = _MAX_TEXT_TOKENS * _CHARS_PER_TOKEN
    return text[:max_chars] if len(text) > max_chars else text
