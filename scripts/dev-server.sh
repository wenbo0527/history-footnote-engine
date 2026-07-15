#!/usr/bin/env bash
# ============================================================
# 🆕 v2.10.8 dev-server.sh - 一键启停前后端
#
# 目的：替代手动启停（kill + nohup + disown + lsof 这一串命令）
#
# 用法：
#   bash scripts/dev-server.sh start      # 启动后端 + 前端
#   bash scripts/dev-server.sh stop       # 停止两个服务
#   bash scripts/dev-server.sh restart    # 重启（先停后启）
#   bash scripts/dev-server.sh status     # 查看状态
#   bash scripts/dev-server.sh logs       # tail 两个日志
#   bash scripts/dev-server.sh open       # 浏览器打开前端
#   bash scripts/dev-server.sh build      # 重新构建前端（生产模式跑 build/）
#   bash scripts/dev-server.sh dev        # 切换到 vite dev（默认）
#
# 端口：
#   - 后端 8765（Python HTTPServer）
#   - 前端 5173（Vite dev / SPA fallback server）
#
# 日志：
#   - /tmp/hfe_backend.log
#   - /tmp/hfe_frontend.log
#
# PID 文件：
#   - /tmp/hfe_backend.pid
#   - /tmp/hfe_frontend.pid
# ============================================================

set -e

# 项目根目录（脚本所在目录的上一级）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

BACKEND_PORT=8765
FRONTEND_PORT=5173
BACKEND_PID_FILE="/tmp/hfe_backend.pid"
FRONTEND_PID_FILE="/tmp/hfe_frontend.pid"
BACKEND_LOG="/tmp/hfe_backend.log"
FRONTEND_LOG="/tmp/hfe_frontend.log"
FRONTEND_MODE_FILE="/tmp/hfe_frontend.mode"   # 'dev' or 'spa'
PYTHONPATH="${PYTHONPATH:-$PROJECT_ROOT/src}"

# 颜色（终端支持时）
if [ -t 1 ]; then
  C_GREEN="\033[1;32m"
  C_RED="\033[1;31m"
  C_YELLOW="\033[1;33m"
  C_BLUE="\033[1;34m"
  C_RESET="\033[0m"
else
  C_GREEN=""; C_RED=""; C_YELLOW=""; C_BLUE=""; C_RESET=""
fi
info() { echo -e "${C_BLUE}[dev-server]${C_RESET} $*"; }
ok()   { echo -e "${C_GREEN}[dev-server]${C_RESET} ✅ $*"; }
warn() { echo -e "${C_YELLOW}[dev-server]${C_RESET} ⚠️  $*"; }
err()  { echo -e "${C_RED}[dev-server]${C_RESET} ❌ $*"; }

# ============================================================
# 工具函数
# ============================================================

# 端口占用检测（返回占用进程的 PID，没有则空）
port_pid() {
  local port="$1"
  lsof -ti :"$port" -P -n 2>/dev/null | head -1
}

# 杀掉指定端口的所有进程
kill_port() {
  local port="$1"
  local pids
  pids=$(lsof -ti :"$port" -P -n 2>/dev/null || true)
  if [ -n "$pids" ]; then
    warn "端口 $port 被占用 (PID: $pids)，kill -9"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
}

# 等待端口 LISTEN（最多 wait_seconds 秒）
wait_listen() {
  local port="$1"
  local wait_seconds="${2:-15}"
  for i in $(seq 1 "$wait_seconds"); do
    if port_pid "$port" >/dev/null; then
      return 0
    fi
    sleep 1
  done
  return 1
}

# 健康检查（GET / 返回 200 表示后端 OK；vite dev 不会 200 但能 LISTEN 即可）
backend_health() {
  local pid
  pid=$(port_pid "$BACKEND_PORT")
  if [ -z "$pid" ]; then return 1; fi
  # 用 timeout 避免 curl 卡住
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://127.0.0.1:$BACKEND_PORT/" 2>/dev/null || echo "000")
  [ "$code" = "200" ] || [ "$code" = "404" ]  # 后端根路径可能 404，但 200 表示 serve 静态主页
}

frontend_health() {
  local pid
  pid=$(port_pid "$FRONTEND_PORT")
  if [ -z "$pid" ]; then return 1; fi
  # vite dev 的 / 通常要等几秒；只要 LISTEN 就算 OK
  return 0
}

# ============================================================
# start 后端
# ============================================================
start_backend() {
  local existing
  existing=$(port_pid "$BACKEND_PORT")
  if [ -n "$existing" ]; then
    warn "后端已在 $BACKEND_PORT 运行（PID: $existing）"
    return 0
  fi

  info "启动后端 (port $BACKEND_PORT, log: $BACKEND_LOG)..."
  PYTHONPATH="$PYTHONPATH" nohup python -c "from history_footnote.web_server import run; run()" \
    > "$BACKEND_LOG" 2>&1 &
  local pid=$!
  disown
  echo "$pid" > "$BACKEND_PID_FILE"

  if wait_listen "$BACKEND_PORT" 15; then
    ok "后端启动成功（PID: $pid，URL: http://127.0.0.1:$BACKEND_PORT/）"
    return 0
  else
    err "后端启动失败（15 秒内未监听）。日志最后 10 行："
    tail -10 "$BACKEND_LOG" | sed 's/^/  /'
    return 1
  fi
}

# ============================================================
# start 前端（dev 模式，优先；如已有 build/ 也可走 SPA fallback）
# ============================================================
start_frontend() {
  local existing
  existing=$(port_pid "$FRONTEND_PORT")
  if [ -n "$existing" ]; then
    warn "前端已在 $FRONTEND_PORT 运行（PID: $existing）"
    return 0
  fi

  local mode="${1:-dev}"
  echo "$mode" > "$FRONTEND_MODE_FILE"

  if [ "$mode" = "spa" ]; then
    if [ ! -d "src/frontend/build" ]; then
      err "src/frontend/build 不存在，请先 bash scripts/dev-server.sh build"
      return 1
    fi
    info "启动前端（SPA 静态模式，port $FRONTEND_PORT，log: $FRONTEND_LOG）..."
    nohup python /tmp/spa_server.py "$FRONTEND_PORT" src/frontend/build \
      > "$FRONTEND_LOG" 2>&1 &
  else
    info "启动前端（Vite dev 模式，port $FRONTEND_PORT，log: $FRONTEND_LOG）..."
    cd src/frontend
    nohup npx vite --host 0.0.0.0 --port "$FRONTEND_PORT" --strictPort \
      > "$FRONTEND_LOG" 2>&1 &
    cd "$PROJECT_ROOT"
  fi

  local pid=$!
  disown
  echo "$pid" > "$FRONTEND_PID_FILE"

  if wait_listen "$FRONTEND_PORT" 20; then
    ok "前端启动成功（PID: $pid，模式: $mode，URL: http://127.0.0.1:$FRONTEND_PORT/）"
    return 0
  else
    err "前端启动失败（20 秒内未监听）。日志最后 10 行："
    tail -10 "$FRONTEND_LOG" | sed 's/^/  /'
    return 1
  fi
}

# ============================================================
# stop 后端
# ============================================================
stop_backend() {
  local pid
  pid=$(port_pid "$BACKEND_PORT")
  if [ -z "$pid" ]; then
    info "后端未运行"
    rm -f "$BACKEND_PID_FILE"
    return 0
  fi
  info "停止后端（PID: $pid）..."
  kill "$pid" 2>/dev/null || true
  for i in 1 2 3 4 5; do
    if ! port_pid "$BACKEND_PORT" >/dev/null; then
      rm -f "$BACKEND_PID_FILE"
      ok "后端已停止"
      return 0
    fi
    sleep 1
  done
  warn "PID $pid 还在，强制 kill -9"
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$BACKEND_PID_FILE"
  ok "后端已强制停止"
}

# ============================================================
# stop 前端
# ============================================================
stop_frontend() {
  local pid
  pid=$(port_pid "$FRONTEND_PORT")
  if [ -z "$pid" ]; then
    info "前端未运行"
    rm -f "$FRONTEND_PID_FILE"
    return 0
  fi
  info "停止前端（PID: $pid）..."
  kill "$pid" 2>/dev/null || true
  for i in 1 2 3 4 5; do
    if ! port_pid "$FRONTEND_PORT" >/dev/null; then
      rm -f "$FRONTEND_PID_FILE"
      ok "前端已停止"
      return 0
    fi
    sleep 1
  done
  warn "PID $pid 还在，强制 kill -9"
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$FRONTEND_PID_FILE"
  ok "前端已强制停止"
}

# ============================================================
# status
# ============================================================
cmd_status() {
  echo "============================================="
  echo "  后端 (port $BACKEND_PORT)"
  echo "============================================="
  local bp
  bp=$(port_pid "$BACKEND_PORT")
  if [ -n "$bp" ]; then
    ok "运行中 (PID: $bp)"
    if backend_health; then
      ok "健康检查: 通过（curl / 返回 200/404）"
    else
      warn "健康检查: 失败（端口在但 HTTP 不通）"
    fi
    if [ -f "$BACKEND_LOG" ]; then
      echo "  日志: $BACKEND_LOG ($(wc -l < "$BACKEND_LOG") 行)"
    fi
  else
    err "未运行"
  fi

  echo ""
  echo "============================================="
  echo "  前端 (port $FRONTEND_PORT)"
  echo "============================================="
  local fp
  fp=$(port_pid "$FRONTEND_PORT")
  if [ -n "$fp" ]; then
    local mode="dev"
    [ -f "$FRONTEND_MODE_FILE" ] && mode=$(cat "$FRONTEND_MODE_FILE")
    ok "运行中 (PID: $fp, 模式: $mode)"
    if [ -f "$FRONTEND_LOG" ]; then
      echo "  日志: $FRONTEND_LOG ($(wc -l < "$FRONTEND_LOG") 行)"
    fi
  else
    err "未运行"
  fi

  echo ""
  echo "快捷命令："
  echo "  bash scripts/dev-server.sh open     # 浏览器打开前端"
  echo "  bash scripts/dev-server.sh logs     # tail 日志（Ctrl+C 退出）"
  echo "  bash scripts/dev-server.sh restart  # 重启"
}

# ============================================================
# 主命令
# ============================================================
cmd="${1:-}"

case "$cmd" in
  start)
    start_backend
    start_frontend "${2:-dev}"
    echo ""
    sleep 2  # 等端口稳定，避免 status 看到 timing issue
    cmd_status
    ;;
  restart)
    stop_frontend || true
    stop_backend || true
    sleep 1
    start_backend
    start_frontend "${2:-dev}"
    echo ""
    sleep 2  # 等端口稳定
    cmd_status
    ;;
  stop)
    stop_frontend
    stop_backend
    ;;
  status)
    cmd_status
    ;;
  logs)
    info "Tail 两个日志（Ctrl+C 退出）"
    if command -v tail >/dev/null; then
      tail -f "$BACKEND_LOG" "$FRONTEND_LOG"
    else
      err "tail 命令不可用"
      exit 1
    fi
    ;;
  open)
    local url="http://localhost:$FRONTEND_PORT/"
    info "打开 $url"
    if command -v open >/dev/null; then
      open "$url"
    elif command -v xdg-open >/dev/null; then
      xdg-open "$url"
    else
      warn "未找到 open/xdg-open，请手动打开: $url"
    fi
    ;;
  build)
    info "构建前端生产产物..."
    if [ ! -d "src/frontend/node_modules" ]; then
      warn "node_modules 不存在，先装依赖..."
      (cd src/frontend && npm install)
    fi
    (cd src/frontend && npx vite build) || {
      err "构建失败"
      exit 1
    }
    ok "构建完成（产物: src/frontend/build/）"
    info "提示: bash scripts/dev-server.sh start spa 可切到静态模式运行"
    ;;
  dev)
    info "前端模式: vite dev（默认）"
    info "提示: bash scripts/dev-server.sh start 启动；想用 SPA 模式请 start spa"
    ;;
  *)
    echo "用法: $0 {start [dev|spa] | stop | restart [dev|spa] | status | logs | open | build | dev}"
    echo ""
    echo "示例:"
    echo "  $0 start          # 启动后端 + Vite dev 前端"
    echo "  $0 start spa      # 启动后端 + SPA 静态模式前端"
    echo "  $0 stop           # 停两个服务"
    echo "  $0 restart        # 重启（保留当前模式）"
    echo "  $0 status         # 看状态"
    echo "  $0 logs           # tail 日志"
    echo "  $0 open           # 浏览器打开前端"
    echo "  $0 build          # 构建前端生产产物"
    exit 1
    ;;
esac