import logging
from pathlib import Path

from tree_sitter import Node
from tree_sitter_languages import get_parser

from codexa.models.function_node import FunctionNode
from codexa.models.parsed_repository import ParsedRepository
from codexa.models.repository import Repository
from codexa.models.source_file import SourceFile
from codexa.services.parsing.interfaces import AstParser

# Directories never worth indexing (vendored deps, VCS internals, build output).
_IGNORE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    ".idea",
    ".vscode",
    ".mypy_cache",
    ".ruff_cache",
}

# Non-code text files worth indexing (docs, config, infra) — embedded whole-file.
_TEXT_SUFFIX_MAP = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".env": "dotenv",
    ".sh": "bash",
    ".bash": "bash",
    ".sql": "sql",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "css",
    ".gradle": "gradle",
    ".properties": "properties",
}
_TEXT_NAME_MAP = {
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    "caddyfile": "caddy",
    "license": "text",
    ".gitignore": "text",
    ".dockerignore": "text",
    ".env": "dotenv",
    ".env.example": "dotenv",
}


def _text_language(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in _TEXT_SUFFIX_MAP:
        return _TEXT_SUFFIX_MAP[suffix]
    return _TEXT_NAME_MAP.get(path.name.lower())


class TreeSitterAstParser(AstParser):
    def parse_repository(self, repository: Repository) -> ParsedRepository:
        root = Path(repository.root_path)
        files: list[SourceFile] = []
        functions: list[FunctionNode] = []

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in _IGNORE_DIRS for part in path.parts):
                continue

            code_language = self._SUFFIX_MAP.get(path.suffix)
            if code_language is not None:
                # Code file: extract functions for fine-grained retrieval.
                file_functions = self._parse_file(path, code_language)
                files.append(SourceFile(path=str(path), language=code_language, size_bytes=path.stat().st_size))
                functions.extend(file_functions)
                continue

            text_language = _text_language(path)
            if text_language is not None:
                # Docs/config (README, yaml, Dockerfile, ...): indexed as a
                # whole-file record (no functions) so they're searchable + visible.
                files.append(SourceFile(path=str(path), language=text_language, size_bytes=path.stat().st_size))

        return ParsedRepository(
            repository_id=repository.repo_id,
            files=files,
            functions=functions,
        )

    # Mapping of file extensions to tree-sitter language identifiers
    _SUFFIX_MAP: dict[str, str] = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".rb": "ruby",
        ".cs": "c_sharp",
        ".php": "php",
        ".kt": "kotlin",
        ".swift": "swift",
        ".scala": "scala",
    }

    def _language_from_suffix(self, suffix: str) -> str | None:
        return self._SUFFIX_MAP.get(suffix)

    def _parse_file(self, path: Path, language: str) -> list[FunctionNode]:
        try:
            parser = get_parser(language)
        except Exception as exc:
            logging.warning("Tree-sitter parser unavailable for %s: %s", language, exc)
            return []

        try:
            source_bytes = path.read_bytes()
        except OSError as exc:
            logging.warning("Failed to read %s: %s", path, exc)
            return []

        tree = parser.parse(source_bytes)
        return self._collect_functions(path, source_bytes, tree.root_node, language)

    def _collect_functions(self, path: Path, source_bytes: bytes, root: Node, language: str) -> list[FunctionNode]:
        function_nodes = self._function_node_types(language)
        results: list[FunctionNode] = []
        stack = [root]

        while stack:
            node = stack.pop()
            if node.type in function_nodes:
                name = self._extract_name(node, source_bytes)
                signature = self._extract_signature(node, source_bytes)
                results.append(
                    FunctionNode(
                        name=name,
                        file_path=str(path),
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        signature=signature,
                    )
                )
            stack.extend(reversed(node.children))

        return results

    def _function_node_types(self, language: str) -> set[str]:
        if language == "python":
            return {"function_definition", "class_definition"}
        if language in ("java", "c_sharp", "kotlin"):
            return {
                "method_declaration",
                "constructor_declaration",
                "class_declaration",
                "interface_declaration",
            }
        if language == "go":
            return {"function_declaration", "method_declaration", "type_declaration"}
        if language == "rust":
            return {
                "function_item",
                "impl_item",
                "struct_item",
                "enum_item",
                "trait_item",
            }
        if language in ("c", "cpp"):
            return {
                "function_definition",
                "struct_specifier",
                "class_specifier",
            }
        if language == "ruby":
            return {"method", "singleton_method", "class", "module"}
        if language == "php":
            return {
                "function_definition",
                "method_declaration",
                "class_declaration",
            }
        if language in ("swift", "scala"):
            return {"function_declaration", "class_declaration"}
        # JavaScript / TypeScript / TSX
        return {
            "function_declaration",
            "method_definition",
            "function",
            "arrow_function",
            "generator_function",
            "class_declaration",
        }

    def _extract_name(self, node: Node, source_bytes: bytes) -> str:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return "<anonymous>"
        return self._node_text(name_node, source_bytes).strip() or "<anonymous>"

    def _extract_signature(self, node: Node, source_bytes: bytes) -> str:
        text = self._node_text(node, source_bytes)
        first_line = text.splitlines()[0].strip() if text else ""
        return first_line[:200]

    def _node_text(self, node: Node, source_bytes: bytes) -> str:
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
