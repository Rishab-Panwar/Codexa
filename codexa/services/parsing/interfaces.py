from abc import ABC, abstractmethod

from codexa.models.parsed_repository import ParsedRepository
from codexa.models.repository import Repository


class AstParser(ABC):
    @abstractmethod
    def parse_repository(self, repository: Repository) -> ParsedRepository:
        raise NotImplementedError
