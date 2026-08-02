import pytest
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "enterprise-rag-assistant"


def test_health_does_not_leak_secrets(client: TestClient) -> None:
    """健康检查是公开端点，不允许出现密钥、上游地址或数据库连接串。"""
    body = client.get("/health").json()
    forbidden = {"api_key", "llm_base_url", "embedding_base_url", "database_url", "jwt_secret"}
    assert forbidden.isdisjoint(body.keys())
    assert "://" not in " ".join(str(v) for v in body.values())


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
)
def test_health_allows_local_development_origins(client: TestClient, origin: str) -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_demo_routes_are_not_mounted_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """无认证的演示路由绝不能出现在生产环境。

    这些路由可被任意调用来上传文件、触发解析与模型调用。M2 完成认证与限流前，
    靠"部署时记得关掉"是不可靠的，这里把它钉成断言。
    """
    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as production_client:
            assert production_client.get("/health").status_code == 200
            assert production_client.post("/demo/query", json={"question": "x"}).status_code == 404
            assert production_client.post("/documents/preview").status_code == 404
            # 生产环境同时应关闭交互式文档
            assert production_client.get("/docs").status_code == 404
    finally:
        get_settings.cache_clear()
