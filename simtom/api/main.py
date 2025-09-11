from fastapi import FastAPI
from contextlib import asynccontextmanager

from .routes import router
from ..core.registry import PluginRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Discover and register all available generators
    PluginRegistry.discover_generators()
    yield
    # Shutdown: Cleanup if needed


def create_app() -> FastAPI:
    app = FastAPI(
        title="SIMTOM",
        description="Realistic data simulator for ML system testing",
        version="0.1.0",
        lifespan=lifespan
    )
    
    app.include_router(router)
    
    return app


app = create_app()