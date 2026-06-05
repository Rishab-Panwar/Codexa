from functools import lru_cache

try:
    from fastembed import TextEmbedding  # type: ignore
except Exception:  # pragma: no cover
    TextEmbedding = None  # type: ignore

from codexa.services.retrieval.embedding import EmbeddingService

# Quantized ONNX build of all-MiniLM-L6-v2: ~90MB, 384-dim, same quality as
# the sentence-transformers model but 3-5x faster on CPU and far lighter on RAM.
_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class FastEmbedEmbeddingService(EmbeddingService):
    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self._model_name = model_name

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = _get_model(self._model_name)
        return [vector.tolist() for vector in model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        model = _get_model(self._model_name)
        return next(iter(model.query_embed(text))).tolist()


@lru_cache
def _get_model(model_name: str) -> "TextEmbedding":
    if TextEmbedding is None:
        raise RuntimeError(
            "fastembed is not installed. Set CODEXA_EMBEDDING_PROVIDER=sentence or hash, or install fastembed."
        )
    return TextEmbedding(model_name=model_name)
