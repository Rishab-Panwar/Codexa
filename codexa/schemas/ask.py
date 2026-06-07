from pydantic import BaseModel


class ChatTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class AskRequest(BaseModel):
    repo_id: str | None = None
    question: str
    history: list[ChatTurn] | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[str]
    reasoning_steps: list[str]
