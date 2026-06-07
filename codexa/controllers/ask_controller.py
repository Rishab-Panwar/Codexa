import asyncio
import json
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from codexa.app.di import get_agent_orchestrator, get_llm_provider, get_repo_state_store
from codexa.observability.tracker import tracker
from codexa.schemas.ask import AskRequest, AskResponse
from codexa.services.agents.orchestration import AgentOrchestrator
from codexa.services.llm.provider import LlmProvider
from codexa.services.state.repo_state_store import RepoStateStore

router = APIRouter(prefix="/ask", tags=["qa"])


def _repo_header(state_store: RepoStateStore, repo_id: str) -> str:
    """A short metadata header so the model can answer name/overview questions."""
    state = state_store.get(repo_id)
    if not state:
        return ""
    name = state.name or "(unknown)"
    parts = [f"Repository name: {name}"]
    if state.url:
        parts.append(f"URL: {state.url}")
    parts.append(f"Indexed files: {len(state.parsed_repo.files)}, functions: {len(state.parsed_repo.functions)}")
    return "\n".join(parts) + "\n\n"


# ---------- normal (non-streaming) endpoint ----------
@router.post("", response_model=AskResponse)
def ask(
    request: AskRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
    llm_provider: LlmProvider = Depends(get_llm_provider),
) -> AskResponse:
    start = time.perf_counter()

    # General mode — no repo, just answer the coding question directly
    if not request.repo_id:
        llm = llm_provider.get_chat_model()
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a senior software engineer and coding mentor. "
                    "Answer the user's coding question clearly with examples where helpful.",
                ),
                ("human", "{question}"),
            ]
        )
        chain = prompt | llm
        response = chain.invoke({"question": request.question})
        resp = AskResponse(
            answer=response.content,
            citations=[],
            reasoning_steps=["General mode: answered without repo context."],
        )
        _track(request, resp, start)
        return resp

    result = orchestrator.handle_question(request.question, request.repo_id)
    resp = AskResponse(
        answer=result.answer,
        citations=result.citations,
        reasoning_steps=result.reasoning_steps,
    )
    _track(request, resp, start)
    return resp


# ---------- streaming SSE endpoint ----------
@router.post("/stream")
async def ask_stream(
    request: AskRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
    llm_provider: LlmProvider = Depends(get_llm_provider),
    state_store: RepoStateStore = Depends(get_repo_state_store),
):
    async def generate():
        start = time.perf_counter()
        try:
            if not request.repo_id:
                # ---- General mode: true LLM token streaming ----
                yield _sse({"type": "status", "content": "Thinking..."})
                llm = llm_provider.get_chat_model()
                from langchain_core.prompts import ChatPromptTemplate

                prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            "You are a senior software engineer and coding mentor. "
                            "Answer the user's coding question clearly with examples where helpful.",
                        ),
                        ("human", "{question}"),
                    ]
                )
                chain = prompt | llm
                full_answer = ""
                for chunk in chain.stream({"question": request.question}):
                    token = chunk.content if hasattr(chunk, "content") else str(chunk)
                    if token:
                        full_answer += token
                        yield _sse({"type": "token", "content": token})

                latency = (time.perf_counter() - start) * 1000
                tracker.record_query(
                    question=request.question,
                    repo_id=None,
                    latency_ms=latency,
                    citation_count=0,
                    agents_used=["mentor"],
                )
                yield _sse(
                    {
                        "type": "done",
                        "citations": [],
                        "reasoning_steps": ["General mode: streamed response."],
                    }
                )
            else:
                # ---- Repo mode: retrieve context (no LLM), then stream mentor tokens ----
                yield _sse({"type": "status", "content": "Retrieving context..."})

                loop = asyncio.get_event_loop()
                context, citations = await loop.run_in_executor(
                    None,
                    lambda: orchestrator.prepare_fast_context(request.question, request.repo_id),
                )

                yield _sse({"type": "status", "content": "Streaming answer..."})

                # Prepend repo metadata so name/overview questions are grounded.
                context = _repo_header(state_store, request.repo_id) + context

                # Conversational memory: thread recent turns into the answer.
                history_text = orchestrator.format_memory(request.history)

                # Real token streaming from the LLM as it generates.
                for token in orchestrator.stream_answer_fast(request.question, context, history_text):
                    yield _sse({"type": "token", "content": token})

                latency = (time.perf_counter() - start) * 1000
                tracker.record_query(
                    question=request.question,
                    repo_id=request.repo_id,
                    latency_ms=latency,
                    citation_count=len(citations),
                    agents_used=["retrieval", "mentor"],
                )
                yield _sse(
                    {
                        "type": "done",
                        "citations": citations,
                        "reasoning_steps": [
                            "Fast mode: 1 retrieval + streamed mentor answer.",
                            f"Retrieved {len(citations)} citations.",
                        ],
                    }
                )
        except Exception as e:
            yield _sse({"type": "error", "content": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------- helpers ----------
def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _track(request: AskRequest, resp: AskResponse, start: float) -> None:
    latency = (time.perf_counter() - start) * 1000
    agents = ["mentor"] if not request.repo_id else ["planner", "retrieval", "mentor", "validator"]
    tracker.record_query(
        question=request.question,
        repo_id=request.repo_id,
        latency_ms=latency,
        citation_count=len(resp.citations),
        agents_used=agents,
    )
