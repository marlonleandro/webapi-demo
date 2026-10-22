"""Endpoints del CRUD de items."""

from typing import Annotated, NoReturn

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.dependencies import RepositoryDep
from app.models import Item, ItemCreate, ItemPage, ItemUpdate
from app.repository import DuplicateItemName, ItemRepository

router = APIRouter(prefix="/items", tags=["items"])


async def _get_item_or_404(repository: ItemRepository, item_id: int) -> Item:
    item = await repository.get(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No existe el item con id {item_id}")
    return item


async def _ensure_unique_name(repository: ItemRepository, name: str, *, ignore_id: int | None = None) -> None:
    existing = await repository.find_by_name(name)
    if existing is not None and existing.id != ignore_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un item con el nombre '{name}' (id {existing.id})",
        )


def _raise_duplicate_name(name: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Ya existe un item con el nombre '{name}'",
    )


@router.get(
    "",
    response_model=ItemPage,
    summary="Listar items",
    description="Devuelve una página de items con filtros opcionales por texto y disponibilidad.",
)
async def list_items(
    repository: RepositoryDep,
    q: Annotated[str | None, Query(max_length=100, description="Busca en nombre y descripción")] = None,
    in_stock: Annotated[bool | None, Query(description="Filtra por disponibilidad")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Tamaño de página")] = 10,
    offset: Annotated[int, Query(ge=0, description="Elementos a omitir")] = 0,
) -> ItemPage:
    items, total = await repository.list(q=q, in_stock=in_stock, limit=limit, offset=offset)
    return ItemPage(total=total, limit=limit, offset=offset, items=items)


@router.get("/{item_id}", response_model=Item, summary="Obtener un item")
async def get_item(item_id: int, repository: RepositoryDep) -> Item:
    return await _get_item_or_404(repository, item_id)


@router.post(
    "",
    response_model=Item,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un item",
    responses={409: {"description": "Ya existe un item con ese nombre"}},
)
async def create_item(
    payload: ItemCreate,
    repository: RepositoryDep,
    request: Request,
    response: Response,
) -> Item:
    await _ensure_unique_name(repository, payload.name)
    try:
        item = await repository.create(payload)
    except DuplicateItemName:
        _raise_duplicate_name(payload.name)
    response.headers["Location"] = str(request.url_for("get_item", item_id=item.id))
    return item


@router.put(
    "/{item_id}",
    response_model=Item,
    summary="Reemplazar un item",
    responses={404: {"description": "Item no encontrado"}, 409: {"description": "Nombre duplicado"}},
)
async def replace_item(item_id: int, payload: ItemCreate, repository: RepositoryDep) -> Item:
    await _get_item_or_404(repository, item_id)
    await _ensure_unique_name(repository, payload.name, ignore_id=item_id)
    try:
        item = await repository.replace(item_id, payload)
    except DuplicateItemName:
        _raise_duplicate_name(payload.name)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No existe el item con id {item_id}")
    return item


@router.patch(
    "/{item_id}",
    response_model=Item,
    summary="Actualizar parcialmente un item",
    responses={404: {"description": "Item no encontrado"}, 409: {"description": "Nombre duplicado"}},
)
async def update_item(item_id: int, payload: ItemUpdate, repository: RepositoryDep) -> Item:
    await _get_item_or_404(repository, item_id)
    if payload.name is not None:
        await _ensure_unique_name(repository, payload.name, ignore_id=item_id)
    try:
        item = await repository.update(item_id, payload)
    except DuplicateItemName:
        _raise_duplicate_name(payload.name or "")
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No existe el item con id {item_id}")
    return item


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un item",
    responses={404: {"description": "Item no encontrado"}},
)
async def delete_item(item_id: int, repository: RepositoryDep) -> Response:
    if not await repository.delete(item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No existe el item con id {item_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
