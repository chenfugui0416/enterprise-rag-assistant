"""FastAPI 应用入口。

M0 阶段只挂载健康检查；业务路由在 M1 之后按模块加入 app/api/routes/。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import demo_rag, document_preview, health
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

    # 演示路由目前没有任何认证与配额控制：任何人都能上传文件、触发解析与
    # 模型调用。在 M2 完成登录、权限与限流之前，绝不能暴露到公网，
    # 因此在生产环境直接不挂载，而不是依赖部署时记得关掉。
    if not settings.is_production:
        app.include_router(document_preview.router)
        app.include_router(demo_rag.router)
    return app


app = create_app()
