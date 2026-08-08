from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.core.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_DIST = PROJECT_ROOT / "ui" / "dist"


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        description="Agentic HR policy and operations assistant for synthetic data.",
        version=settings.app_version,
    )
    application.include_router(health_router)

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
            "status": "foundation-ready",
            "health": "/health",
            "docs": "/docs",
        }

    return application


app = create_app()
