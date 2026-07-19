# 🆕 v2.10.9 部署文件说明

本目录是**生产环境部署**所需的所有文件：

| 文件 | 作用 | 使用时机 |
|---|---|---|
| `Dockerfile` | 单镜像构建（前端 + 后端） | 容器化部署 / Docker Compose |
| `.dockerignore` | Docker 构建排除规则 | 与 Dockerfile 配套 |
| `deploy.sh` | 一键部署脚本（systemd + nginx） | 传统 VPS / 裸金属部署 |
| `hfe-backend.service` | systemd 单元文件 | `deploy.sh` 自动复制到 /etc/systemd/system/ |
| `nginx.conf` | Nginx 反代 + 静态前端托管 | `deploy.sh` 自动配置 |

## 🚀 快速开始（推荐 3 选 1）

### 方案 A：Docker（最快）
```bash
# 1. 准备 .env
cp .env.example .env && nano .env

# 2. 构建 + 启动
docker build -t hfe-app .
docker run -d --name hfe \
    -p 8765:8765 \
    -v $(pwd)/saves:/app/saves \
    -v $(pwd)/runtime:/app/runtime \
    -v $(pwd)/eras:/app/eras \
    --env-file .env \
    hfe-app

# 3. 验证
curl http://localhost:8765/api/version
# 浏览器访问 http://localhost:8765
```

### 方案 B：一键脚本（systemd + nginx）
```bash
# 1. 克隆代码到目标机器
git clone <repo> /opt/history-footnote-engine
cd /opt/history-footnote-engine

# 2. 配置环境变量
cp .env.example .env
nano .env  # 填入真实 API Key
export WEB_DOMAIN=your-domain.com  # nginx 配置用

# 3. 一键部署
sudo bash deploy/deploy.sh

# 浏览器访问 http://your-domain.com
```

### 方案 C：手动部署（开发调试）
```bash
# 后端
PYTHONPATH=src python -m history_footnote.web_server --port 8765

# 前端（另一终端）
cd src/frontend && npm run dev
```

## 📊 部署流程时间对比

| 步骤 | 手动 | Docker | 一键脚本 |
|---|---|---|---|
| 安装系统依赖 | 10 min | 2 min (apt) | 2 min |
| 安装 Python 依赖 | 5 min | 1 min (pip cache) | 1 min |
| 安装前端依赖 + build | 5 min | 1 min (npm cache) | 1 min |
| 配置 nginx | 5 min | - | 30 s |
| 配置 systemd | 5 min | - | 30 s |
| **总计** | **30 min** | **5 min** | **5 min** |

## 🛠 运维命令速查

### Docker
```bash
docker logs hfe                   # 实时日志
docker restart hfe                # 重启
docker stop hfe && docker rm hfe  # 停止 + 删除
```

### systemd
```bash
sudo systemctl status hfe-backend
sudo systemctl restart hfe-backend
sudo journalctl -u hfe-backend -f  # 实时日志
```

### 更新部署
```bash
# Docker
git pull && docker build -t hfe-app . && docker restart hfe

# systemd
sudo bash deploy/deploy.sh --update
```

### 数据备份
```bash
# Docker
docker run --rm -v $(pwd)/saves:/backup ubuntu tar czf /backup.tgz /backup

# systemd（deploy.sh 自动备份，也可手动）
sudo tar czf saves-$(date +%Y%m%d).tgz /opt/history-footnote-engine/saves
```

## 🔍 部署验证清单

- [ ] 后端响应：`curl http://localhost:8765/api/version`
- [ ] 后端 health：`curl http://localhost:8765/api/health`
- [ ] era 列表：`curl http://localhost:8765/api/eras`
- [ ] 前端 build：`ls /var/www/hfe/build/index.html`（nginx 方案）
- [ ] LLM 连通：访问前端 → 开始新游戏 → 看第一回合叙事是否生成

## ⚠️ 生产环境必检

- [ ] `.env` 已填真实 `MINIMAX_API_KEY` / `WEB_COOKIE_SECRET`
- [ ] `WEB_COOKIE_SECRET` 是 32+ 位随机字符串（用 `python -c 'import secrets; print(secrets.token_hex(32))'`）
- [ ] HTTPS 已配置（certbot）
- [ ] 防火墙：仅开放 80/443，8765 仅本机访问
- [ ] `saves/` `runtime/` `logs/` 已挂载到持久化卷（Docker）或独立分区（裸机）
- [ ] 日志轮转已配置（logrotate）
- [ ] 备份策略：每天 cron `tar czf` saves/ 到 S3/OSS