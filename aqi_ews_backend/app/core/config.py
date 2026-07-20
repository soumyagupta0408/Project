from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "aqi_sentinel"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    SECRET_KEY: str = "change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DATA_GOV_API_KEY: str = ""
    DATA_GOV_RESOURCE_ID: str = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
    WAQI_API_KEY: str = ""
    WAQI_STATION: str = "india/indore/chhoti-gwaltoli"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:8501,http://127.0.0.1:8501"
  

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def cors_origins_list(self) -> list:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()

