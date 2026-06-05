import logging
from pathlib import Path

from codexa.models.embedding_record import EmbeddingRecord
from codexa.models.parsed_repository import ParsedRepository
from codexa.models.repository import Repository
from codexa.services.retrieval.embedding import EmbeddingService
from codexa.services.retrieval.interfaces import CodeRetriever


class CodeIndexService:
    def __init__(self, embedder: EmbeddingService, retriever: CodeRetriever) -> None:
        self._embedder = embedder
        self._retriever = retriever
        self._logger = logging.getLogger(__name__)

    def index_repository(self, repository: Repository, parsed_repo: ParsedRepository) -> None:
        self._logger.info("Indexing repository %s", repository.repo_id)
        documents: list[str] = []
        records: list[EmbeddingRecord] = []

        # Index a whole-file record only for files that have no parsed functions
        # (configs, scripts, etc). Files with functions are covered by the
        # per-function snippets below — embedding both is redundant and slow.
        files_with_functions = {function.file_path for function in parsed_repo.functions}
        for source_file in parsed_repo.files:
            if source_file.path in files_with_functions:
                continue
            if _is_skippable(source_file.path):
                continue
            content = _safe_read(Path(source_file.path))
            if not content.strip():
                continue
            documents.append(content)
            records.append(
                EmbeddingRecord(
                    record_id=source_file.path,
                    scope="file",
                    vector=[],
                    metadata={"path": source_file.path, "language": source_file.language},
                )
            )

        for function in parsed_repo.functions:
            snippet = _read_snippet(Path(function.file_path), function.start_line, function.end_line)
            documents.append(snippet)
            records.append(
                EmbeddingRecord(
                    record_id=f"{function.file_path}:{function.start_line}-{function.end_line}",
                    scope="function",
                    vector=[],
                    metadata={
                        "path": function.file_path,
                        "name": function.name,
                        "signature": function.signature,
                        "start_line": str(function.start_line),
                        "end_line": str(function.end_line),
                    },
                )
            )

        embeddings = self._embedder.embed_texts(documents)
        indexed_records: list[EmbeddingRecord] = []
        for record, vector in zip(records, embeddings):
            indexed_records.append(
                EmbeddingRecord(
                    record_id=record.record_id,
                    scope=record.scope,
                    vector=vector,
                    metadata=record.metadata,
                )
            )

        self._retriever.index(repository.repo_id, indexed_records)
        self._logger.info("Indexed %s records for repo %s", len(indexed_records), repository.repo_id)


# Files that add noise/bloat to the index without improving code understanding.
_SKIP_NAME_SUFFIXES = (
    ".lock",
    ".min.js",
    ".min.css",
    ".map",
    "-lock.json",
    "package-lock.json",
)
_MAX_FILE_BYTES = 200_000  # skip very large/generated blobs


def _is_skippable(path_str: str) -> bool:
    lower = path_str.lower()
    if any(lower.endswith(suffix) for suffix in _SKIP_NAME_SUFFIXES):
        return True
    try:
        if Path(path_str).stat().st_size > _MAX_FILE_BYTES:
            return True
    except OSError:
        return True
    return False


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_snippet(path: Path, start_line: int, end_line: int) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    start = max(start_line - 1, 0)
    end = max(end_line, start)
    return "\n".join(lines[start:end])
