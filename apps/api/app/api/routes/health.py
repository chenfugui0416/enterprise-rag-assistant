"""健康检查。用于 Docker healthcheck、CI 冒烟测试和前端连通性展示。

只暴露运行状态与已启用的 provider 名称，不暴露 base_url、密钥或内部路径。
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    env: str
    llm_provider: str
    embedding_provider: str
    embedding_dim: int


@router.get("/health", response_model=HealthResponse, summary="服务健康检查")
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
        llm_provider=settings.llm_provider,
        embedding_provider=settings.embedding_provider,
        embedding_dim=settings.embedding_dim,
    )
