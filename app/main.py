from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.actions import router as actions_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.core.config import get_settings
from peopleops_mcp.server import mcp_server

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_DIST = PROJECT_ROOT / "ui" / "dist"
MCP_HTTP_APP = mcp_server.streamable_http_app(
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with mcp_server.session_manager.run():
        yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        description="Agentic HR policy and operations assistant for synthetic data.",
        version=settings.app_version,
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(chat_router)
    application.include_router(actions_router)

    assets_directory = UI_DIST / "assets"
    if assets_directory.is_dir():
        application.mount("/assets", StaticFiles(directory=assets_directory), name="assets")

    @application.get("/", include_in_schema=False)
    async def root():
        index_file = UI_DIST / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "phase-7-ready",
            "health": "/health",
            "chat": "/chat",
            "mcp": "/mcp",
            "docs": "/docs",
        }

    application.mount("/", MCP_HTTP_APP, name="mcp")
    return application


app = create_app()
