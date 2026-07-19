#!/usr/bin/env bash
# 🆕 v2.10.11+ Save 模块健康检查脚本
# 用途：部署端"save 模块消失"反馈的快速定位
# 用法：bash scripts/check_save_health.sh [host:port]

set -uo pipefail

HOST_PORT="${1:-127.0.0.1:8765}"
HOST="${HOST_PORT%:*}"

ok()   { echo -e "[OK]   $*"; }
warn() { echo -e "[WARN] $*"; }
err()  { echo -e "[ERR]  $*"; }
info() { echo -e "[INFO] $*"; }

echo "==============================================="
echo "  HFE Save 模块健康检查 @ $HOST_PORT"
echo "==============================================="
echo ""

# 1. Python import（conda 环境 / 有 langchain_core 的解释器）
info "1. Python import 测试（PYTHONPATH=src 必备）"
PYTHON_RES=$({
    PYTHONPATH=src /opt/anaconda3/bin/python -c "
try:
    from history_footnote.storage import SaveManager, DEFAULT_SAVE_ROOT
    print('  SaveManager 来源:', SaveManager.__module__)
    print('  DEFAULT_SAVE_ROOT:', DEFAULT_SAVE_ROOT)
    print('PASS')
except Exception as e:
    print(f'FAIL: {type(e).__name__}: {e}', file=__import__('sys').stderr)
" 2>&1
} || true)
echo "$PYTHON_RES" | head -5
if echo "$PYTHON_RES" | grep -q "PASS"; then
    ok "save module import PASS"
elif echo "$PYTHON_RES" | grep -q "FAIL"; then
    err "save module import FAIL"
else
    warn "未能确认 conda python，跳过自动 import 测试"
fi
echo ""

# 2. Save 相关文件是否齐全
info "2. Save 文件结构"
MISSING=0
for f in \
    "src/history_footnote/saves/__init__.py" \
    "src/history_footnote/saves/storage/save_manager.py" \
    "src/history_footnote/storage.py" \
    "src/history_footnote/game/loop_save.py" \
    "src/history_footnote/cli/commands/save_ops.py" \
    "src/history_footnote/web_server/routers/admin_saves.py" ; do
    if [ -f "$f" ]; then
        ok "$f 存在"
    else
        err "$f 缺失!"
        MISSING=$((MISSING+1))
    fi
done
echo ""

# 3. 路由注册
info "3. Save HTTP 路由 (router_registry)"
ROUTE_COUNT=$(grep -c "/api/saves/list\|/api/admin/saves\|/api/admin/saves/delete" src/history_footnote/web_server/router_registry.py 2>/dev/null || echo 0)
if [ "$ROUTE_COUNT" -gt 0 ]; then
    ok "找到 $ROUTE_COUNT 个 save 路由"
else
    err "router_registry.py 里没 save 路由!"
fi
echo ""

# 4. 端点 HTTP 测试
info "4. HTTP 端点 @ $HOST_PORT (curl)"
if ! command -v curl >/dev/null 2>&1; then
    warn "curl 不可用，跳过 HTTP 测试"
else
    for path in "/api/saves/list" "/api/version" "/api/eras"; do
        status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$HOST_PORT$path" 2>/dev/null || echo "TIMEOUT")
        case "$path" in
            /api/saves/list)
                if [ "$status" = "200" ]; then
                    ok "$path -> 200 (save 模块 OK)"
                else
                    err "$path -> $status (save 模块 NOT loaded 或 server 关闭)"
                fi
                ;;
            *)
                if [ "$status" = "200" ]; then
                    ok "$path -> 200"
                else
                    warn "$path -> $status"
                fi
                ;;
        esac
    done
fi
echo ""

# 5. saves 数据目录
info "5. saves 数据目录"
for path in "saves" "/app/saves" "/var/lib/hfe/saves"; do
    if [ -d "$path" ]; then
        count=$(ls "$path" 2>/dev/null | wc -l | tr -d ' ')
        ok "$path 存在 (含 $count 项)"
    else
        warn "$path 不存在"
    fi
done
echo ""

# 6. Docker VOLUME
if [ -f "/.dockerenv" ] || [ -f "/run/.containerenv" ]; then
    info "6. Docker VOLUME 状态"
    if command -v mount >/dev/null; then
        mount | grep -E "saves|runtime|logs" || warn "未发现 saves/runtime/logs 挂载! 数据可能在容器重启时丢失"
    else
        warn "mount 命令不可用"
    fi
else
    info "6. Docker VOLUME (skip, 非 docker 环境)"
fi
echo ""

echo "==============================================="
echo "  检查完成"
echo "==============================================="
echo ""
echo "可能根因排查顺序:"
echo "  1. [ERR] save module import FAIL -> 用 conda python / 检 Python path"
echo "  2. [ERR] HTTP /api/saves/list NOT 200 -> 后端没起 / 路径错"
echo "  3. [WARN] saves 目录 NOT 存在 -> mkdir + docker -v 挂载"
echo "  4. [WARN] Docker VOLUME 未挂载 -> 加 -v \$PWD/saves:/app/saves"