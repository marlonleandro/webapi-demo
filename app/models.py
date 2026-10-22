"""Modelos (esquemas) de entrada y salida de la API."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ItemName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ItemBase(BaseModel):
    """Datos comunes de un item."""

    name: ItemName = Field(description="Nombre del item", examples=["Teclado mecánico"])
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Descripción opcional del item",
        examples=["Teclado con switches rojos y retroiluminación RGB"],
    )
    price: float = Field(gt=0, le=1_000_000, description="Precio en unidades monetarias", examples=[49.99])
    tags: list[str] = Field(default_factory=list, description="Etiquetas libres", examples=[["teclado", "gaming"]])
    in_stock: bool = Field(default=True, description="Indica si hay stock disponible")


class ItemCreate(ItemBase):
    """Cuerpo de la petición para crear un item."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Mouse inalámbrico",
                "description": "Mouse ergonómico con receptor USB",
                "price": 19.99,
                "tags": ["mouse", "oficina"],
                "in_stock": True,
            }
        }
    )


class ItemUpdate(BaseModel):
    """Cuerpo de la petición para actualizar parcialmente un item."""

    name: ItemName | None = None
    description: str | None = Field(default=None, max_length=500)
    price: float | None = Field(default=None, gt=0, le=1_000_000)
    tags: list[str] | None = None
    in_stock: bool | None = None

    @model_validator(mode="after")
    def reject_null_non_nullable_fields(self) -> "ItemUpdate":
        for field_name in ("name", "price", "tags", "in_stock"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} no puede ser null")
        return self


class Item(ItemBase):
    """Item tal como lo devuelve la API."""

    id: int = Field(description="Identificador único autogenerado")
    created_at: datetime = Field(description="Fecha de creación en formato ISO 8601 (UTC)")
    updated_at: datetime = Field(description="Fecha de la última modificación en formato ISO 8601 (UTC)")


class ItemPage(BaseModel):
    """Respuesta paginada del listado de items."""

    total: int = Field(description="Cantidad total de items que cumplen el filtro")
    limit: int = Field(description="Tamaño de página solicitado")
    offset: int = Field(description="Desplazamiento aplicado")
    items: list[Item] = Field(description="Items de la página actual")


class HealthResponse(BaseModel):
    """Estado de salud del servicio."""

    status: str
    environment: str
    version: str


class ApiInfo(BaseModel):
    """Información general de la API."""

    name: str
    version: str
    environment: str
    docs_url: str
    openapi_url: str
