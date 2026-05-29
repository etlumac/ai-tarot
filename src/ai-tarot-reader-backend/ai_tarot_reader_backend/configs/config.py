from typing import Optional

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class PostgresConfig(BaseModel):
    host: str = Field(..., description="PostgreSQL host")
    port: int = Field(5432, description="PostgreSQL port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Database user")
    password: SecretStr = Field(..., description="Database password")
    pool_size: int = Field(10, description="Min connections in pool")

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class MlLayerConfig(BaseModel):
    base_url: str = Field("http://localhost:8001", description="ML layer base URL")


class OpenRouterConfig(BaseModel):
    api_key: SecretStr = Field(..., description="OpenRouter API key")
    model: str = Field("openrouter/free", description="Model to use")
    base_url: str = Field("https://openrouter.ai/api/v1")


class PathSettings(BaseModel):
    yaml_path: Optional[str] = None
    env_path: Optional[str] = None


class Config(BaseSettings):
    postgres: PostgresConfig
    ml_layer: MlLayerConfig = MlLayerConfig()
    open_router: OpenRouterConfig
    path_settings: PathSettings = PathSettings()

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore",  # игнорировать лишние переменные окружения
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        file_secret_settings: PydanticBaseSettingsSource,  # noqa: ARG003
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            DotEnvSettingsSource(settings_cls, env_file=cls.path_settings.env_path),
            YamlConfigSettingsSource(
                settings_cls, yaml_file=cls.path_settings.yaml_path
            ),
        )

    @classmethod
    def load(cls, path_settings: PathSettings) -> "Config":
        cls.path_settings = path_settings
        return cls()


config: Config | None = None


def set_config(path_settings: PathSettings) -> Config:
    global config
    config = Config.load(path_settings=path_settings)
    return config


def get_config() -> Config:
    global config
    if config is None:
        raise RuntimeError("Config not loaded")
    return config