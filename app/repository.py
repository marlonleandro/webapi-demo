"""Repositorio asíncrono de items respaldado por PostgreSQL."""

from decimal import Decimal

import asyncpg

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


class DuplicateItemName(Exception):
    """Señala que el nombre de item ya existe."""


class ItemRepository:
    """CRUD de items almacenados en PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @staticmethod
    def _as_item(record: asyncpg.Record) -> Item:
        return Item(**dict(record))

    @staticmethod
    def _payload_values(payload: ItemCreate) -> dict[str, object]:
        values = payload.model_dump()
        values["price"] = Decimal(str(values["price"]))
        return values

    async def seed_demo_data(self) -> None:
        """Carga los items de ejemplo solo si la tabla está vacía."""
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                has_items = await connection.fetchval("SELECT EXISTS (SELECT 1 FROM items)")
                if has_items:
                    return
                await connection.executemany(
                    """
                    INSERT INTO items (name, description, price, tags, in_stock)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT DO NOTHING
                    """,
                    [
                        (
                            item["name"],
                            item["description"],
                            Decimal(str(item["price"])),
                            item["tags"],
                            item["in_stock"],
                        )
                        for item in _SEED_ITEMS
                    ],
                )

    async def count(self) -> int:
        return await self._pool.fetchval("SELECT count(*) FROM items")

    async def list(
        self,
        *,
        q: str | None = None,
        in_stock: bool | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[Item], int]:
        """Devuelve una página de items y el total que cumple los filtros."""
        conditions: list[str] = []
        parameters: list[object] = []
        if q:
            parameters.append(q)
            placeholder = f"${len(parameters)}"
            conditions.append(
                f"(position(lower({placeholder}) in lower(name)) > 0 "
                f"OR position(lower({placeholder}) in lower(coalesce(description, ''))) > 0)"
            )
        if in_stock is not None:
            parameters.append(in_stock)
            conditions.append(f"in_stock = ${len(parameters)}")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        total = await self._pool.fetchval(
            f"SELECT count(*) FROM items {where_clause}",
            *parameters,
        )
        page_parameters = [*parameters, limit, offset]
        rows = await self._pool.fetch(
            f"""
            SELECT * FROM items
            {where_clause}
            ORDER BY id
            LIMIT ${len(parameters) + 1} OFFSET ${len(parameters) + 2}
            """,
            *page_parameters,
        )
        return [self._as_item(row) for row in rows], total

    async def get(self, item_id: int) -> Item | None:
        record = await self._pool.fetchrow("SELECT * FROM items WHERE id = $1", item_id)
        return self._as_item(record) if record is not None else None

    async def find_by_name(self, name: str) -> Item | None:
        record = await self._pool.fetchrow(
            "SELECT * FROM items WHERE lower(name) = lower($1)",
            name,
        )
        return self._as_item(record) if record is not None else None

    async def create(self, payload: ItemCreate) -> Item:
        values = self._payload_values(payload)
        try:
            record = await self._pool.fetchrow(
                """
                INSERT INTO items (name, description, price, tags, in_stock)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                values["name"],
                values["description"],
                values["price"],
                values["tags"],
                values["in_stock"],
            )
        except asyncpg.UniqueViolationError as error:
            raise DuplicateItemName from error
        return self._as_item(record)

    async def replace(self, item_id: int, payload: ItemCreate) -> Item | None:
        values = self._payload_values(payload)
        try:
            record = await self._pool.fetchrow(
                """
                UPDATE items
                SET name = $2, description = $3, price = $4, tags = $5,
                    in_stock = $6, updated_at = now()
                WHERE id = $1
                RETURNING *
                """,
                item_id,
                values["name"],
                values["description"],
                values["price"],
                values["tags"],
                values["in_stock"],
            )
        except asyncpg.UniqueViolationError as error:
            raise DuplicateItemName from error
        return self._as_item(record) if record is not None else None

    async def update(self, item_id: int, payload: ItemUpdate) -> Item | None:
        changes = payload.model_dump(exclude_unset=True)
        if changes.get("price") is not None:
            changes["price"] = Decimal(str(changes["price"]))
        columns = {
            "name": "name",
            "description": "description",
            "price": "price",
            "tags": "tags",
            "in_stock": "in_stock",
        }
        assignments = [f"{columns[field]} = ${index}" for index, field in enumerate(changes, start=2)]
        assignments.append("updated_at = now()")
        try:
            record = await self._pool.fetchrow(
                f"""
                UPDATE items
                SET {", ".join(assignments)}
                WHERE id = $1
                RETURNING *
                """,
                item_id,
                *changes.values(),
            )
        except asyncpg.UniqueViolationError as error:
            raise DuplicateItemName from error
        return self._as_item(record) if record is not None else None

    async def delete(self, item_id: int) -> bool:
        record = await self._pool.fetchrow("DELETE FROM items WHERE id = $1 RETURNING id", item_id)
        return record is not None
