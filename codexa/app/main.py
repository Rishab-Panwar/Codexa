import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware

from codexa.controllers.analyze_controller import router as analyze_router
from codexa.controllers.ask_controller import router as ask_router
from codexa.controllers.dependency_controller import router as dependency_router
from codexa.controllers.eval_controller import router as eval_router
from codexa.controllers.explain_controller import router as explain_router
from codexa.controllers.files_controller import router as files_router
from codexa.controllers.generate_controller import router as generate_router
from codexa.controllers.metrics_controller import router as metrics_router
from codexa.controllers.overview_controller import router as overview_router
from codexa.controllers.repos_controller import router as repos_router
from codexa.controllers.search_controller import router as search_router
from codexa.utils.logging import configure_logging

load_dotenv()


def _allowed_origins() -> list[str]:
    """CORS origins, comma-separated via CODEXA_ALLOWED_ORIGINS."""
    raw = os.getenv("CODEXA_ALLOWED_ORIGINS") or "http://localhost:3000,http://localhost:3001"
    return [o.strip() for o in raw.split(",") if o.strip()]


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Codexa", version="0.1.0")

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Simplified dependency to bypass API key check for local frontend
    def auth_dep(x_api_key: str | None = Header(default=None)) -> None:
        # verify_api_key(get_config(), x_api_key)
        pass

    auth_dependency = Depends(auth_dep)

    app.include_router(analyze_router, dependencies=[auth_dependency])
    app.include_router(ask_router, dependencies=[auth_dependency])
    app.include_router(explain_router, dependencies=[auth_dependency])
    app.include_router(dependency_router, dependencies=[auth_dependency])
    app.include_router(files_router, dependencies=[auth_dependency])
    app.include_router(repos_router, dependencies=[auth_dependency])
    app.include_router(overview_router, dependencies=[auth_dependency])
    app.include_router(search_router, dependencies=[auth_dependency])
    app.include_router(generate_router, dependencies=[auth_dependency])
    app.include_router(eval_router, dependencies=[auth_dependency])
    app.include_router(metrics_router)

    @app.on_event("startup")
    def _warm_embedder() -> None:
        # Load the embedding model in the background so the first index doesn't
        # pay the one-time model-load cost. No-op for the hash provider.
        import logging
        import threading

        def warm() -> None:
            try:
                from codexa.app.di import get_embedder

                get_embedder().embed_query("warmup")
                logging.getLogger(__name__).info("Embedder warmed up.")
            except Exception as e:
                logging.getLogger(__name__).warning("Embedder warmup skipped: %s", e)

        threading.Thread(target=warm, daemon=True).start()

    @app.middleware("http")
    async def record_metrics(request, call_next):
        from time import perf_counter

        from codexa.observability.metrics import REQUEST_COUNT, REQUEST_LATENCY

        start = perf_counter()
        response = await call_next(request)
        elapsed = perf_counter() - start
        REQUEST_COUNT.labels(
            method=request.method,
            path=request.url.path,
            status=str(response.status_code),
        ).inc()
        REQUEST_LATENCY.labels(path=request.url.path).observe(elapsed)
        return response

    return app


app = create_app()
