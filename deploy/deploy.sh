#!/usr/bin/env bash
# ============================================================
# 🆕 v2.10.9 deploy.sh — 单机一键部署脚本
#
# 适用场景：
#   - 个人 VPS / 内网机器
#   - 不想折腾 Docker / K8s
#   - 想要 systemd 自动管理 + Nginx 反代
#
# 用法：
#   sudo bash deploy/deploy.sh           # 完整部署
#   sudo bash deploy/deploy.sh --update  # 拉新代码重启
#   sudo bash deploy/deploy.sh --rollback  # 回滚到上一版本
#
# 前提：
#   - Debian/Ubuntu 系统
#   - 已克隆代码到 /opt/history-footnote-engine
#   - sudo 权限
# ============================================================

set -euo pipefail

# ---------- 配置 ----------
APP_USER="hfe"
APP_GROUP="hfe"
APP_DIR="/opt/history-footnote-engine"
BACKUP_DIR="/var/backups/hfe"
LOG_DIR="/var/log/hfe"
SERVICE_NAME="hfe-backend"

# 颜色
if [ -t 1 ]; then
  C_GREEN='\033[1;32m'; C_RED='\033[1;31m'; C_YELLOW='\033[1;33m'; C_BLUE='\033[1;34m'; C_RESET='\033[0m'
else
  C_GREEN=''; C_RED=''; C_YELLOW=''; C_BLUE=''; C_RESET=''
fi
info() { echo -e "${C_BLUE}[deploy]${C_RESET} $*"; }
ok()   { echo -e "${C_GREEN}[deploy]${C_RESET} ✅ $*"; }
warn() { echo -e "${C_YELLOW}[deploy]${C_RESET} ⚠️  $*"; }
err()  { echo -e "${C_RED}[deploy]${C_RESET} ❌ $*"; }

# ---------- 子命令 ----------
ACTION="${1:-install}"

# ---------- 通用函数 ----------
check_root() {
  if [[ $EUID -ne 0 ]]; then
    err "需要 sudo 权限：sudo bash $0 $*"
    exit 1
  fi
}

check_os() {
  if ! command -v apt-get &> /dev/null; then
    err "当前仅支持 Debian/Ubuntu（需要 apt-get）"
    exit 1
  fi
}

create_user() {
  if ! id "$APP_USER" &>/dev/null; then
    info "创建系统用户 $APP_USER"
    useradd --system --shell /bin/bash --home-dir "$APP_DIR" --create-home "$APP_USER"
  else
    ok "用户 $APP_USER 已存在"
  fi
}

install_system_deps() {
  info "安装系统依赖 (python3.11, nodejs, nginx, lsof)..."
  apt-get update -qq
  apt-get install -y --no-install-recommends \
      python3.11 python3.11-venv python3-pip \
      curl lsof \
      nginx \
      rsnapshot

  # Node.js 20（如果未装）
  if ! command -v node &> /dev/null; then
    info "安装 Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y --no-install-recommends nodejs
  fi

  ok "系统依赖已装"
}

setup_dirs() {
  info "创建数据目录..."
  mkdir -p "$APP_DIR"/{saves,runtime/accounts,logs,static}
  mkdir -p "$BACKUP_DIR"
  mkdir -p "$LOG_DIR"
  chown -R "$APP_USER:$APP_GROUP" "$APP_DIR" "$BACKUP_DIR" "$LOG_DIR"
  ok "数据目录就绪"
}

setup_venv() {
  if [[ ! -d "$APP_DIR/.venv" ]]; then
    info "创建 Python 虚拟环境..."
    sudo -u "$APP_USER" python3.11 -m venv "$APP_DIR/.venv"
    sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip
    sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -e "$APP_DIR"
  else
    ok "虚拟环境已存在"
  fi
}

setup_env() {
  if [[ ! -f "$APP_DIR/.env" ]]; then
    warn ".env 不存在，从 .env.example 复制"
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"

    # 生成 cookie secret
    local secret
    secret=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    sed -i "s|^WEB_COOKIE_SECRET=.*|WEB_COOKIE_SECRET=$secret|" "$APP_DIR/.env"

    warn "⚠️  请编辑 $APP_DIR/.env 填入真实 API Key："
    warn "    sudo nano $APP_DIR/.env"
    warn "    然后再次运行: sudo bash $0 --update"
    exit 1
  else
    ok ".env 已存在"
  fi
}

build_frontend() {
  info "构建前端..."
  cd "$APP_DIR/src/frontend"

  if [[ ! -d node_modules ]]; then
    sudo -u "$APP_USER" npm ci --no-audit --no-fund
  fi
  sudo -u "$APP_USER" npm run build

  # 🆕 v2.10.10：路径统一
  # SvelteKit build 产物 → /var/www/hfe/build/
  # （nginx.conf 里 location / 指向这里）
  mkdir -p /var/www/hfe
  rsync -a --delete "$APP_DIR/src/frontend/build/" /var/www/hfe/build/

  # SvelteKit 静态资源（命运卡 / 角色 / 场景图）
  # → /var/www/hfe/static/
  if [[ -d "$APP_DIR/src/frontend/static" ]]; then
    rsync -a --delete "$APP_DIR/src/frontend/static/" /var/www/hfe/static/
  fi

  ok "前端已构建并部署到 /var/www/hfe/ (build/ + static/)"
}

install_systemd() {
  info "安装 systemd 服务..."
  cp "$APP_DIR/deploy/hfe-backend.service" "/etc/systemd/system/$SERVICE_NAME.service"
  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME"
  ok "systemd 服务已注册"
}

configure_nginx() {
  info "配置 Nginx..."
  local domain="${WEB_DOMAIN:-your-domain.com}"

  # 替换 domain
  sed "s|your-domain.com|$domain|g" "$APP_DIR/deploy/nginx.conf" \
    > "/etc/nginx/sites-available/$SERVICE_NAME"
  ln -sf "/etc/nginx/sites-available/$SERVICE_NAME" /etc/nginx/sites-enabled/
  rm -f /etc/nginx/sites-enabled/default

  nginx -t
  systemctl reload nginx
  ok "Nginx 已配置（域名：$domain）"
}

start_backend() {
  info "启动后端..."
  systemctl restart "$SERVICE_NAME"
  sleep 2

  if systemctl is-active --quiet "$SERVICE_NAME"; then
    ok "后端运行中"
  else
    err "后端启动失败，查看日志：journalctl -u $SERVICE_NAME -n 50"
    exit 1
  fi
}

health_check() {
  info "健康检查..."
  sleep 3
  local version
  version=$(curl -sf http://localhost:8765/api/version || echo "FAIL")

  if [[ "$version" == "FAIL" ]]; then
    err "后端无响应：curl http://localhost:8765/api/version"
    err "日志：journalctl -u $SERVICE_NAME -n 30"
    exit 1
  fi

  ok "后端响应正常: $version"

  # 检查前端
  if [[ -f /var/www/hfe/build/index.html ]]; then
    ok "前端 build 已部署"
  else
    warn "前端 build 缺失（虽然 nginx 可能仍能服务其它内容）"
  fi
}

backup_data() {
  info "备份数据..."
  local timestamp
  timestamp=$(date +%Y%m%d_%H%M%S)
  local backup_path="$BACKUP_DIR/$timestamp"

  mkdir -p "$backup_path"
  rsync -a "$APP_DIR/saves/" "$backup_path/saves/"
  rsync -a "$APP_DIR/runtime/" "$backup_path/runtime/"

  # 保留最近 7 份
  cd "$BACKUP_DIR"
  ls -1d */ 2>/dev/null | sort -r | tail -n +8 | xargs -r rm -rf

  ok "数据已备份到 $backup_path"
}

update_code() {
  info "拉取最新代码..."
  cd "$APP_DIR"
  sudo -u "$APP_USER" git pull --rebase
  ok "代码已更新"

  info "更新 Python 依赖..."
  sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -e "$APP_DIR"

  build_frontend
  start_backend
  health_check
}

rollback() {
  warn "回滚到上一版本..."
  cd "$APP_DIR"
  sudo -u "$APP_USER" git log --oneline -5
  read -p "回滚到哪个 commit? " commit
  sudo -u "$APP_USER" git checkout "$commit"
  start_backend
  health_check
}

# ---------- 主流程 ----------
case "$ACTION" in
  install)
    check_root
    check_os
    install_system_deps
    create_user
    setup_dirs
    setup_venv
    setup_env
    build_frontend
    install_systemd
    configure_nginx
    start_backend
    health_check
    ok "部署完成！访问 http://your-domain.com 或 http://$(hostname -I | awk '{print $1}')"
    ;;

  --update)
    check_root
    backup_data
    update_code
    ok "更新完成"
    ;;

  --rollback)
    check_root
    rollback
    ok "回滚完成"
    ;;

  *)
    echo "Usage: sudo bash $0 {install|--update|--rollback}"
    exit 1
    ;;
esac