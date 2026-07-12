# deploy/ · 部署与运维文档

> **目的**:部署流程、配置、故障排查

## 📋 文件列表

| 文件 | 主题 |
|---|---|
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | 完整部署指南(5 步 + 10 问题 + Nginx/Systemd/Docker) |

## 🚀 快速部署(5 步)

1. **克隆 + Python venv** (Python ≥3.11)
2. **配置 .env** (API Key + WEB_COOKIE_SECRET)
3. **准备数据目录** (saves/ runtime/ logs/ eras/)
4. **启动后端** (端口 8765)
5. **启动前端** (dev 或 build 后 preview)

## ⚠️ 常见 10 问题

| # | 问题 | 状态 |
|---|---|---|
| 1 | 端口冲突 | lsof + pkill |
| 2 | API Key 错误 | 后端自动 fallback |
| 3 | chapter_state 500 | ✅ commit 1e2fdbf |
| 4 | /game 500 | ✅ commit 73cf2e1 |
| 5 | 存档兼容 | ✅ 加 dict/dataclass 兼容 |
| 6 | LLM 限流 429 | 调大 LLM_MAX_REQUESTS |
| 7 | svelte-check errors | ✅ 22→0 (commit 4b1a4ad) |
| 8 | Node 版本不兼容 | 必须 ≥20 |
| 9 | 路径配置错误 | 必须在项目根目录运行 |
| 10 | Cookie/Session 失效 | 设 WEB_COOKIE_SECRET |

## 🔧 生产配置

- **Nginx 反向代理** (含 SSE 流式)
- **Systemd 服务**
- **Docker** (可选)

详见 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

依据 v2.10.2 W52 followup
