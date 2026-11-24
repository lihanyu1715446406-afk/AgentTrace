# 后端镜像：基于 uv 安装依赖，先跑 Alembic 迁移再启动 FastAPI。
# 构建上下文为项目根目录（见 docker-compose.yml 的 context: .）。
FROM python:3.12-slim

# 拷贝 uv 二进制（官方推荐做法，避免单独安装）。
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先拷贝依赖清单，利用 Docker 层缓存。
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 拷贝源码与迁移脚本。
COPY backend ./backend
COPY sdk ./sdk
COPY mcp_server ./mcp_server
COPY scripts ./scripts
COPY README.md ./

EXPOSE 8000

# 一键部署：先迁移数据库，再启动 uvicorn（FastAPI）。
CMD ["sh", "-c", "uv run --no-sync python -m alembic -c backend/alembic.ini upgrade head && uv run --no-sync python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
