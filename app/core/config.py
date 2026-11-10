from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str = ""
    DB_PORT: int = 3306
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = "vehiculo_iot"
    DB_POOL_SIZE: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_configured(self) -> bool:
        return bool(self.DB_HOST and self.DB_USER and self.DB_PASSWORD)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

