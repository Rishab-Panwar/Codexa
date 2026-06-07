from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from codexa.services.agents.interfaces import Agent
from codexa.services.qa.answer_service import AnswerService


class CodingMentorAgent(Agent):
    def __init__(self, answer_service: AnswerService, llm: BaseChatModel) -> None:
        self._answer_service = answer_service
        self._llm = llm
        self._prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a Senior Software Engineer and Mentor. "
                    "Use the provided code context to answer the user's request. "
                    "Use the prior conversation to resolve follow-up references "
                    "(e.g. 'it', 'that function', 'refactor it'). "
                    "Provide specific code examples and refactoring suggestions where appropriate. "
                    "Cite the file paths you are referencing.",
                ),
                (
                    "human",
                    "Prior conversation:\n{history}\n\nGoal: {goal}\n\nExisting Code Context:\n{context}",
                ),
            ]
        )

    def _inputs(self, goal: str, context: str, history: str) -> dict:
        return {
            "goal": goal,
            "context": context if context.strip() else "No relevant code found in the repository index.",
            "history": history if history.strip() else "No prior conversation.",
        }

    def generate(self, goal: str, context: str, history: str = "") -> str:
        """Single LLM call using pre-retrieved context (no internal retrieval)."""
        chain = self._prompt | self._llm
        response = chain.invoke(self._inputs(goal, context, history))
        return response.content

    def stream(self, goal: str, context: str, history: str = ""):
        """Stream the answer token-by-token using pre-retrieved context."""
        chain = self._prompt | self._llm
        for chunk in chain.stream(self._inputs(goal, context, history)):
            token = chunk.content if hasattr(chunk, "content") else str(chunk)
            if token:
                yield token

    def run(self, prompt: str, repo_id: str | None = None) -> str:
        if not repo_id:
            return "Error: repo_id is required for coding assistance."

        # 1. Retrieve relevant context
        # We assume the prompt is the question/goal
        retrieval = self._answer_service.answer(repo_id=repo_id, question=prompt, top_k=3)

        context_str = ""
        if retrieval.citations:
            context_str = f"Found relevant code:\n{retrieval.answer}\n\nCitations:\n" + "\n".join(retrieval.citations)
        else:
            context_str = "No relevant code found in the repository index."

        # 2. Generate advice
        chain = self._prompt | self._llm
        response = chain.invoke({"goal": prompt, "context": context_str})

        return response.content
