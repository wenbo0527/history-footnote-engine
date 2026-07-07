#!/bin/bash
# 🆕 v1.7.46: 自动加载 .env（含 ADMIN_TOKEN）
set -a
. /root/history-footnote-engine/.env
set +a
cd /root/history-footnote-engine
exec .venv/bin/python -u -c "from history_footnote.web_server import run; run(\"0.0.0.0\", 8765)"
