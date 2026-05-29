from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.connections import router as connections_router
from app.api.onboarding import router as onboarding_router
from app.api.tenants import router as tenants_router
from app.config import settings
from app.database import enable_pgvector, run_migrations
from app.logging import (
    RequestLoggingMiddleware,
    get_logger,
    setup_logging,
    shutdown_logging,
)

setup_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log.info("app.startup.begin")
    run_migrations()
    enable_pgvector()
    log.info(
        "app.startup.complete",
        llm_model=settings.nvidia_model,
        embedding_model=settings.nvidia_embedding_model,
        axiom_enabled=bool(settings.axiom_token),
        app_env=settings.app_env,
    )
    yield
    log.info("app.shutdown.begin")
    shutdown_logging()
    log.info("app.shutdown.complete")


app = FastAPI(title="Velora", lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenants_router, prefix="/tenants")
app.include_router(auth_router, prefix="/auth")
app.include_router(connections_router, prefix="/connections")
app.include_router(onboarding_router, prefix="/onboard")
app.include_router(chat_router, prefix="/chat")
