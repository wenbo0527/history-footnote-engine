# 🆕 v2.10.10 Dockerfile — 单镜像部署后端 + SvelteKit 前端
#
# 用法：
#   docker build -t hfe-app .
#   docker run -d --name hfe \
#     -p 8765:8765 \
#     -v $(pwd)/saves:/app/saves \
#     -v $(pwd)/eras:/app/eras \
#     --env-file .env \
#     hfe-app
#
# v2.10.10 改动：
# - 单一 CMD `python -m history_footnote.web_server` 启动后端 8765
# - 后端直接服务 src/frontend/build/ 作为 SvelteKit 静态文件
# - 不再 COPY 前端到 /app/static/（旧路径，新版 web_server 通过 src/frontend/build 路径访问）

# ==================== 前端构建阶段 ====================
FROM node:20-slim AS frontend-build
WORKDIR /build

# 单独拷贝 package.json 利用 Docker 缓存
COPY src/frontend/package*.json ./
RUN npm ci --no-audit --no-fund

COPY src/frontend/ ./
RUN npm run build
# 输出在 /build/build/ （SvelteKit adapter-static 产物）

# ==================== 后端运行时 ====================
FROM python:3.12-slim AS runtime

# 系统依赖（curl 用于 healthcheck）
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 依赖
COPY pyproject.toml ./
COPY src/history_footnote/__init__.py src/history_footnote/__init__.py
# 复制整个 src/ 让 setuptools 能找到包
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e . \
    # 额外安装 web server 需要的几个 SDK
    && pip install --no-cache-dir \
        'langchain>=0.2.0' \
        'langchain-core>=0.3.0' \
        'langchain-anthropic>=0.2.0' \
        'langchain-openai>=0.2.0' \
        'pydantic>=2.0' \
        'python-dotenv>=1.0'

# 🆕 v2.10.10：复制前端 SvelteKit 产物到 /app/src/frontend/build/
# 后端通过 static_assets.py 的 Path(__file__) 计算这个路径。
COPY --from=frontend-build /build/build/ /app/src/frontend/build/

# SvelteKit static 资源（命运卡 / 角色 / 场景图）— optional
COPY --from=frontend-build /build/static/ /app/src/frontend/static/

# 时代配置（时期知识 JSON）
COPY eras/ ./eras/

# 数据卷（生产环境用 -v 挂载）
VOLUME ["/app/saves", "/app/runtime", "/app/logs"]

# 环境变量默认值
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV WEB_HOST=0.0.0.0
ENV WEB_PORT=8765

EXPOSE 8765

# 健康检查（用 /api/version）
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8765/api/version || exit 1

# 启动
CMD ["python", "-m", "history_footnote.web_server"]
