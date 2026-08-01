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
