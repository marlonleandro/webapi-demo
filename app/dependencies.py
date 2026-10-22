"""Dependencias reutilizables de FastAPI."""

from typing import Annotated

from fastapi import Depends, Request

from app.repository import ItemRepository


def get_repository(request: Request) -> ItemRepository:
    """Devuelve el repositorio PostgreSQL asociado a la aplicación."""
    return request.app.state.repository


RepositoryDep = Annotated[ItemRepository, Depends(get_repository)]
