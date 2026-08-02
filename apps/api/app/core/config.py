"""应用配置：所有外部依赖只通过环境变量注入，不在代码中硬编码任何凭据。"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderKind = Literal["mock", "openai_compatible"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- 应用 ----
    app_env: str = "development"
    app_name: str = "enterprise-rag-assistant"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    )

    # ---- 安全 ----
    jwt_secret: str = "dev-only-insecure-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    seed_admin_email: str = ""
    seed_admin_password: str = ""

    # ---- 基础设施 ----
    database_url: str = "postgresql+psycopg://rag:rag@localhost:5432/ragdb"
    redis_url: str = "redis://localhost:6379/0"

    # ---- 生成模型 ----
    llm_provider: ProviderKind = "mock"
    llm_base_url: str = "https://api.siliconflow.cn/v1"
    llm_api_key: str = ""
    llm_model: str = "Qwen/Qwen2.5-7B-Instruct"
    llm_timeout_seconds: float = 60.0
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.2

    # ---- Embedding 模型 ----
    embedding_provider: ProviderKind = "mock"
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_api_key: str = ""
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    embedding_batch_size: int = 32

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
