#!/bin/bash
# 联调截图：游戏页（用真后端 session）
set -e

echo "1. 创建真实 session"
SESSION_ID=$(curl -s -m 15 -X POST http://localhost:5174/api/start \
  -H "Content-Type: application/json" \
  -d '{"era_id":"wanli1587","identity":"weaving_male","gender":"male","character":{"name":"联调截图","age":30,"occupation":"织工","hometown":"盛泽镇"}}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
echo "  session_id: $SESSION_ID"

echo ""
echo "2. 截图游戏页（桌面 1280x900）"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-sandbox \
  --window-size=1280,900 \
  --virtual-time-budget=45000 \
  --screenshot=/tmp/v2_liantiao_game_1280.png \
  "http://localhost:5174/game/?session=$SESSION_ID" 2>/dev/null
ls -la /tmp/v2_liantiao_game_1280.png

echo ""
echo "3. 截图游戏页（移动 375x812）"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-sandbox \
  --window-size=375,812 \
  --virtual-time-budget=45000 \
  --screenshot=/tmp/v2_liantiao_game_375.png \
  "http://localhost:5174/game/?session=$SESSION_ID" 2>/dev/null
ls -la /tmp/v2_liantiao_game_375.png

echo ""
echo "4. 截图首页（确认 UI 没坏）"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-sandbox \
  --window-size=1280,900 \
  --virtual-time-budget=15000 \
  --screenshot=/tmp/v2_liantiao_home.png \
  "http://localhost:5174/" 2>/dev/null
ls -la /tmp/v2_liantiao_home.png
