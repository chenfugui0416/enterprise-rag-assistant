from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

# 测试固定使用 mock provider：不联网、不需要任何 API Key，CI 可离线运行。
TEST_ENV = {
    "APP_ENV": "test",
    "CORS_ORIGINS": (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    ),
    "LLM_PROVIDER": "mock",
    "EMBEDDING_PROVIDER": "mock",
    "EMBEDDING_DIM": "64",
    "SEED_ADMIN_EMAIL": "",
    "SEED_ADMIN_PASSWORD": "",
}


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """环境变量优先级高于 .env，因此本地是否存在 .env 都不影响测试结果。"""
    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c
