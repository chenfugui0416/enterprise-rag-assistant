"""FastAPI 应用入口。

M0 阶段只挂载健康检查；业务路由在 M1 之后按模块加入 app/api/routes/。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="企业级 RAG 智能助手 API",
        version=settings.app_version,
        # 生产环境关闭交互式文档，减少信息暴露面
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    return app


app = create_app()
