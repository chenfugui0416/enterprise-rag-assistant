# ---- 依赖层：仅在依赖清单变化时重建 ----
FROM python:3.13-slim AS deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml ./
RUN uv venv /opt/venv && \
    VIRTUAL_ENV=/opt/venv uv pip install --no-cache -r pyproject.toml

# ---- 运行层 ----
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# 以非 root 用户运行
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app
COPY --from=deps /opt/venv /opt/venv
COPY --chown=appuser:appuser app ./app

USER appuser
EXPOSE 8000

# 健康检查复用 /health，容器编排据此判断就绪
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
