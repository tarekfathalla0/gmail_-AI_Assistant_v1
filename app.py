from contextlib import asynccontextmanager
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config import get_settings
from database import close as close_database, connect as connect_database
from routers.auth_router import router as auth_router
from routers.gmail_router import router as gmail_router
from routers.agent_router import router as agent_router
from data import checkpoint, memory
from mcp_client import initialize_mcp_tools, shutdown_mcp_tools


settings = get_settings()

os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY or ""
os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
os.environ["LANGSMITH_TRACING"] = str(settings.LANGSMITH_TRACING).lower()
os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT

@asynccontextmanager
async def lifespan(app: FastAPI):

    print(f"Starting {settings.APP_NAME}...")

    await connect_database()

    await initialize_mcp_tools()

    checkpoint.checkpointer = (
        await checkpoint.checkpointer_cm.__aenter__()
    )
    await checkpoint.checkpointer.setup()

    await memory.initialize_store()

    print("Postgres initialized")

    yield

    await memory.shutdown_store()

    await checkpoint.checkpointer_cm.__aexit__(None, None, None)

    await shutdown_mcp_tools()

    await close_database()

    print("Application stopped.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)


@app.exception_handler(httpx.HTTPStatusError)
async def google_http_exception(
    request: Request,
    exc: httpx.HTTPStatusError,
):
    """
    Handle HTTP errors returned by Google APIs.
    """

    try:
        detail = exc.response.json()
    except Exception:
        detail = exc.response.text

    return JSONResponse(
        status_code=exc.response.status_code,
        content={
            "detail": detail
        },
    )


@app.exception_handler(RuntimeError)
async def runtime_exception(
    request: Request,
    exc: RuntimeError,
):
    """
    Handle application runtime errors.
    """

    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc)
        },
    )


@app.get("/")
async def home():
    """
    Health endpoint.
    """

    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "documentation": "/docs",
    }


app.include_router(auth_router)
app.include_router(gmail_router)
app.include_router(agent_router)