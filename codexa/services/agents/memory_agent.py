from codexa.services.agents.interfaces import Agent
from codexa.services.memory.interfaces import MemoryStore

# How many recent turns (user+assistant pairs) to thread into the next answer.
_MAX_TURNS = 4


class MemoryAgent(Agent):
    """Conversational memory: formats recent chat turns into context so the
    mentor can answer follow-ups ("refactor it", "what about that function?").
    """

    def __init__(self, memory_store: MemoryStore) -> None:
        self._memory_store = memory_store

    def format_history(self, history: list) -> str:
        if not history:
            return ""
        recent = history[-_MAX_TURNS * 2 :]
        lines: list[str] = []
        for turn in recent:
            role = getattr(turn, "role", "") or ""
            content = (getattr(turn, "content", "") or "").strip()
            if content:
                speaker = "User" if role == "user" else "Assistant"
                lines.append(f"{speaker}: {content}")
        return "\n".join(lines)

    def run(self, prompt: str, repo_id: str | None = None) -> str:
        # Kept for the Agent interface; conversational memory uses format_history.
        return ""
