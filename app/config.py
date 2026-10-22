"""Configuración de la aplicación leída desde variables de entorno."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración tipada de la API.

    Los valores se leen de las variables de entorno y, en desarrollo local,
    del archivo `.env` ubicado en la raíz del proyecto.
    """

    app_name: str = "FastAPI Demo API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: str = "*"
    seed_demo_data: bool = True
    log_level: str = "info"
    database_url: str = "postgresql://app:app@localhost:5432/itemsdb"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Convierte la lista de orígenes separada por comas en una lista."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única instancia de la configuración."""
    return Settings()
