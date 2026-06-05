from abc import ABC, abstractmethod

from codexa.models.repository import Repository


class RepositoryLoader(ABC):
    @abstractmethod
    def load(self, repo_url: str) -> Repository:
        raise NotImplementedError
