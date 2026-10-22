"""Doble en memoria para probar los endpoints sin una instancia de PostgreSQL."""

from datetime import datetime, timezone

from app.models import Item, ItemCreate, ItemUpdate

_SEED_ITEMS = [
    {
        "name": "Teclado mecánico",
        "description": "Teclado con switches rojos y retroiluminación RGB",
        "price": 49.99,
        "tags": ["teclado", "gaming"],
        "in_stock": True,
    },
    {
        "name": "Mouse inalámbrico",
        "description": "Mouse ergonómico con receptor USB",
        "price": 19.99,
        "tags": ["mouse", "oficina"],
        "in_stock": True,
    },
    {
        "name": "Monitor 27 pulgadas",
        "description": "Monitor IPS 1440p a 165 Hz",
        "price": 299.0,
        "tags": ["monitor", "gaming"],
        "in_stock": False,
    },
]


class InMemoryItemRepository:
    """Implementa el contrato del repositorio para las pruebas HTTP."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._items: dict[int, Item] = {}
        self._next_id = 1
        for payload in _SEED_ITEMS:
            self._insert(ItemCreate(**payload))

    def _insert(self, payload: ItemCreate) -> Item:
        timestamp = datetime.now(timezone.utc)
        item = Item(
            id=self._next_id,
            created_at=timestamp,
            updated_at=timestamp,
            **payload.model_dump(),
        )
        self._items[item.id] = item
        self._next_id += 1
        return item

    async def count(self) -> int:
        return len(self._items)

    async def list(
        self,
        *,
        q: str | None = None,
        in_stock: bool | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[Item], int]:
        found = sorted(self._items.values(), key=lambda item: item.id)
        if q:
            needle = q.casefold()
            found = [
                item
                for item in found
                if needle in item.name.casefold() or needle in (item.description or "").casefold()
            ]
        if in_stock is not None:
            found = [item for item in found if item.in_stock is in_stock]
        return found[offset : offset + limit], len(found)

    async def get(self, item_id: int) -> Item | None:
        return self._items.get(item_id)

    async def find_by_name(self, name: str) -> Item | None:
        return next((item for item in self._items.values() if item.name.casefold() == name.casefold()), None)

    async def create(self, payload: ItemCreate) -> Item:
        return self._insert(payload)

    async def replace(self, item_id: int, payload: ItemCreate) -> Item | None:
        current = self._items.get(item_id)
        if current is None:
            return None
        updated = Item(
            id=item_id,
            created_at=current.created_at,
            updated_at=datetime.now(timezone.utc),
            **payload.model_dump(),
        )
        self._items[item_id] = updated
        return updated

    async def update(self, item_id: int, payload: ItemUpdate) -> Item | None:
        current = self._items.get(item_id)
        if current is None:
            return None
        updated = current.model_copy(
            update={**payload.model_dump(exclude_unset=True), "updated_at": datetime.now(timezone.utc)}
        )
        self._items[item_id] = updated
        return updated

    async def delete(self, item_id: int) -> bool:
        return self._items.pop(item_id, None) is not None
