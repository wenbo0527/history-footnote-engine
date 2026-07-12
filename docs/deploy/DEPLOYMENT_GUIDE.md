# 历史注脚 HFE · 部署指南

> **从 GitHub 拉取后如何部署**
> **项目**: history-footnote-engine v0.1.0 (Python 后端) + history-footnote-frontend v2.7.0 (Svelte 5 前端)
> **运行时**: Python ≥3.11 + Node.js ≥20

## 📊 架构总览

```
┌─────────────────┐         ┌──────────────────┐
│  Vite Dev :5173 │  HTTP   │  Web Server      │
│  Svelte 5 SPA   │ ──────> │  :8765 (Python)  │
│  (开发/生产)    │         │  FastAPI/HTTP    │
└─────────────────┘         └──────────────────┘
                                     │
                                     ├─> LLM (minimax-anthropic / deepseek)
                                     ├─> saves/  (本地存档)
                                     ├─> eras/   (时代配置)
                                     └─> runtime/ (账户/会话)
```

| 组件 | 端口 | 技术栈 | 启动命令 |
|---|---|---|---|
| **前端 dev** | 5173 | Vite + Svelte 5 | `npm run dev` |
| **前端 prod** | 4173 | 静态文件 + Vite preview | `npm run build && npm run preview` |
| **后端** | 8765 | Python http.server (自定义) | `python -m history_footnote.web_server_concurrent --port 8765` |
| **API** | /api/* | HTTP + SSE 流式 | - |

## 🚀 部署流程(5 步)

### 步骤 1:克隆 + Python 环境

```bash
# 1.1 克隆
git clone git@github.com:wenbo0527/history-footnote-engine.git
cd history-footnote-engine

# 1.2 确认 Python ≥3.11
python3 --version  # 必须 ≥3.11

# 1.3 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 1.4 安装依赖
pip install -e .
# 或
pip install -r requirements.txt  # 如果存在
```

### 步骤 2:配置 .env ⚠️ 关键

```bash
# 2.1 复制模板
cp .env.example .env

# 2.2 填入真实 API Key
nano .env
```

**关键变量** (来自 `.env.example`):
```bash
# Minimax API (主 provider)
MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic
MINIMAX_MODEL=MiniMax-M3
MINIMAX_API_KEY=sk-xxxxxx   # ⚠️ 必填

# DeepSeek API (备选)
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_API_KEY=sk-xxxxxx

# Web 配置
WEB_PORT=8765
WEB_COOKIE_SECRET=<生成32位随机字符串>   # ⚠️ 生产环境必填
# 生成方法: python -c 'import secrets; print(secrets.token_hex(32))'

# LLM 限流
LLM_MAX_REQUESTS=120
LLM_WINDOW_SECONDS=600
```

### 步骤 3:准备数据目录

```bash
# 3.1 时代配置 (已有 wanli1587)
ls eras/  # 应有 wanli1587/

# 3.2 存档目录 (自动创建,首次启动)
mkdir -p saves/
mkdir -p runtime/accounts/
mkdir -p logs/

# 3.3 (可选) 复制老存档
# cp -r /backup/saves/* saves/
```

### 步骤 4:启动后端

```bash
# 4.1 启动
python -m history_footnote.web_server_concurrent --port 8765 --workers 4

# 或带日志
python -m history_footnote.web_server_concurrent --port 8765 > logs/server.log 2>&1 &

# 4.2 验证
curl http://localhost:8765/api/version
# 应返: {"version": "1.7.27", ...}

curl http://localhost:8765/api/eras
# 应返: {"eras": [{"id": "wanli1587", ...}]}
```

### 步骤 5:启动前端

**开发模式** (推荐本地):
```bash
cd src/frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

**生产模式** (推荐部署):
```bash
cd src/frontend
npm install --production
npm run build
# 输出在 src/frontend/build/ (SvelteKit adapter-static)

# 启动 preview server
npm run preview
# 访问 http://localhost:4173

# 或部署到 Nginx/Cloudflare Pages
# build/ 目录是纯静态文件
```

## ⚠️ 部署常见问题 + 解决方案

### 问题 1: 端口冲突
**症状**: `Address already in use`
**解决**:
```bash
# 找占用进程
lsof -i :8765
lsof -i :5173

# 杀掉
pkill -9 -f "history_footnote.web_server"
pkill -9 -f "vite dev"

# 换端口
python -m history_footnote.web_server_concurrent --port 8766
```

### 问题 2: API Key 错误
**症状**: `HTTP 401 Unauthorized` 调 LLM
**解决**:
```bash
# 1. 检查 .env 存在且填了真 Key
cat .env | grep MINIMAX_API_KEY

# 2. 测连通性
curl -X POST "$MINIMAX_BASE_URL/v1/messages" \
  -H "x-api-key: $MINIMAX_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"MiniMax-M3","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'

# 3. 后端有 fallback,会自动切到备选 provider
```

### 问题 3: chapter_state 反序列化为 dict
**症状**: `/api/chapter/state` 返 500
**状态**: ✅ **已在 v2.10.2 W52 followup commit 73cf2e1 修好**
**验证**:
```bash
curl "http://localhost:8765/api/chapter/state?session_id=YOUR_SID"
# 应返 200, 不再 500
```

### 问题 4: /game 页面 500
**症状**: Vite dev 报 SSR 500
**状态**: ✅ **已在 v2.10.2 W52 followup commit 73cf2e1 修好**
**修法**: `src/frontend/src/routes/game/+page.ts` 加 `ssr = false`
**手动解决**(如仍出现):
```bash
# 清 Vite cache
rm -rf src/frontend/.svelte-kit
rm -rf src/frontend/node_modules/.vite

# 重启 vite
pkill -9 -f "vite dev"
cd src/frontend && npm run dev
```

### 问题 5: 存档兼容
**症状**: 老存档加载后字段丢失(变 dict)
**根因**: `chapter_state` dataclass 经 save/load 序列化为 dict
**状态**: ✅ **后端 router 已加 dict/dataclass 兼容**
**新存档**: 直接创建,无此问题
**老存档迁移**: 不需要,自动兼容

### 问题 6: LLM 限流 429
**症状**: 大量请求被拒
**解决**:
```bash
# 调大限制
echo "LLM_MAX_REQUESTS=200" >> .env
echo "LLM_WINDOW_SECONDS=600" >> .env
# 重启后端生效
```

### 问题 7: 前端类型不匹配
**症状**: `npm run check` 报 svelte-check errors
**状态**: ✅ **已在 v2.10.2 W52 followup commit 4b1a4ad 修好(22→0)**
**新代码**: 保持 0 errors

### 问题 8: Node 版本不兼容
**症状**: Svelte 5 报语法错误
**解决**:
```bash
# 必须 Node ≥20
node --version
# 升级: nvm install 20 && nvm use 20
```

### 问题 9: 路径配置错误
**症状**: 找不到 eras/ saves/ 等目录
**根因**: `Path("saves")` 是相对路径,必须在项目根目录运行
**解决**:
```bash
# 必须在项目根目录运行后端
cd /path/to/history-footnote-engine
python -m history_footnote.web_server_concurrent --port 8765
```

### 问题 10: Cookie/Session 失效
**症状**: 401 错误频繁
**解决**:
```bash
# .env 设 WEB_COOKIE_SECRET
export WEB_COOKIE_SECRET=$(python -c 'import secrets; print(secrets.token_hex(32))')
```

## 🔧 生产环境额外配置

### Nginx 反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/hfe/build;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://localhost:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSE 流式支持 (重要!)
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

### Systemd 服务
```ini
# /etc/systemd/system/hfe-backend.service
[Unit]
Description=HFE Backend
After=network.target

[Service]
Type=simple
User=hfe
WorkingDirectory=/opt/history-footnote-engine
Environment="PATH=/opt/history-footnote-engine/.venv/bin"
EnvironmentFile=/opt/history-footnote-engine/.env
ExecStart=/opt/history-footnote-engine/.venv/bin/python -m history_footnote.web_server_concurrent --port 8765 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable hfe-backend
systemctl start hfe-backend
systemctl status hfe-backend
```

### Docker (可选)
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install -e .

EXPOSE 8765
CMD ["python", "-m", "history_footnote.web_server_concurrent", "--port", "8765", "--workers", "4"]
```

```bash
docker build -t hfe-backend .
docker run -d --name hfe -p 8765:8765 --env-file .env hfe-backend
```

## 📋 部署清单

部署前必检:

- [ ] Python ≥3.11 已装
- [ ] Node ≥20 已装
- [ ] .env 已配置 (API Key 真实)
- [ ] WEB_COOKIE_SECRET 已生成
- [ ] eras/wanli1587 存在
- [ ] saves/ 可写
- [ ] runtime/ 可写
- [ ] logs/ 可写
- [ ] 端口 8765 未占用
- [ ] 端口 5173/4173 未占用
- [ ] 防火墙允许这些端口
- [ ] LLM API 可达 (curl 测试)

## 🆘 故障排查顺序

1. **后端能否启动?** `python -m history_footnote.web_server_concurrent --port 8765`
2. **后端 health?** `curl http://localhost:8765/api/version`
3. **后端 LLM 可达?** `curl -X POST ... <API URL>`
4. **前端能 build?** `cd src/frontend && npm run build`
5. **前端能启动?** `npm run dev`
6. **API 代理工作?** `curl http://localhost:5173/api/version` (vite proxy)
7. **浏览器控制台无错?** F12 → Console

## 📞 关键 commit (本次会话修的)

- `73cf2e1` /game 强制 client-only (ssr=false) ← 修 500
- `1e2fdbf` /api/chapter/* dict 兼容 ← 修 500
- `4b1a4ad` svelte-check 22→0 errors
- `b72809c` 修 BUG 6-13 (8 个 optional/identity 兜底)
- `0bbe9b4` SSE 调试工具脚本

## 📚 相关文档

- [README.md](README.md) - 项目说明
- [RELEASE_NOTES_v2.8.0.md](RELEASE_NOTES_v2.8.0.md) - 版本说明
- [ISSUES.md](ISSUES.md) - 已知问题
- [docs/test/v2.10.2-frontend-audit.md](docs/test/v2.10.2-frontend-audit.md) - 前端审计
- [docs/test/v2.10.2-bug-prevention-analysis.md](docs/test/v2.10.2-bug-prevention-analysis.md) - BUG 预防

依据 v2.10.2 W52 followup
