from dataclasses import dataclass

from codexa.models.function_node import FunctionNode
from codexa.models.source_file import SourceFile


@dataclass(frozen=True)
class ParsedRepository:
    repository_id: str
    files: list[SourceFile]
    functions: list[FunctionNode]
