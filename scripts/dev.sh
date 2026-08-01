#!/usr/bin/env bash
# 同时启动后端与前端热重载进程，Ctrl-C 时一并回收，避免留下孤儿进程占用端口。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -x "apps/api/.venv/bin/uvicorn" ]; then
  echo "后端依赖未安装，请先执行：make setup" >&2
  exit 1
fi
if [ ! -d "apps/web/node_modules" ]; then
  echo "前端依赖未安装，请先执行：make setup" >&2
  exit 1
fi

pids=()
cleanup() {
  echo ""
  echo "正在停止开发进程…"
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(cd apps/api && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) &
pids+=($!)

(cd apps/web && npm run dev) &
pids+=($!)

echo "后端 http://localhost:8000/docs"
echo "前端 http://localhost:3000"
wait -n
