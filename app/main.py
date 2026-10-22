"""Punto de entrada de la API demo: crea y configura la aplicación FastAPI."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import ApiInfo, HealthResponse
from app.repository import ItemRepository
from app.routers import items

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    application.state.repository = ItemRepository(pool)
    try:
        if settings.seed_demo_data:
            await application.state.repository.seed_demo_data()
        logger.info(
            "Iniciando %s v%s (entorno: %s) conectado a PostgreSQL",
            settings.app_name,
            settings.app_version,
            settings.environment,
        )
        yield
    finally:
        await pool.close()
        logger.info("Deteniendo %s", settings.app_name)


def create_app() -> FastAPI:
    """Construye la aplicación con routers, middleware y documentación."""
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API REST demo con FastAPI y Uvicorn. Implementa un CRUD de items "
            "con almacenamiento PostgreSQL, validación con Pydantic y documentación "
            "interactiva autogenerada."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        debug=settings.debug,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(items.router, prefix=settings.api_prefix)

    @application.get("/", response_model=ApiInfo, tags=["root"], summary="Información de la API")
    async def root() -> ApiInfo:
        return ApiInfo(
            name=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
            docs_url="/docs",
            openapi_url="/openapi.json",
        )

    @application.get("/health", response_model=HealthResponse, tags=["health"], summary="Estado de salud")
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            environment=settings.environment,
            version=settings.app_version,
        )

    return application


app = create_app()
