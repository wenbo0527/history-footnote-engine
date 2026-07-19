#!/bin/bash
# 截图 v1.7.30 新版首页
# 1. 登录页（未登录）
# 2. 首页（访客模式，?skip_login=1）
# 3. 首页（已登录模式 ?login=demo）
set -e

echo "=== 1. /login 页面（桌面 1280） ==="
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-sandbox \
  --window-size=1280,900 \
  --virtual-time-budget=30000 \
  --screenshot=/tmp/v1730_login_1280.png \
  "http://localhost:5174/login" 2>/dev/null
ls -la /tmp/v1730_login_1280.png

echo ""
echo "=== 2. /login 页面（移动 375） ==="
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-sandbox \
  --window-size=375,812 \
  --virtual-time-budget=30000 \
  --screenshot=/tmp/v1730_login_375.png \
  "http://localhost:5174/login" 2>/dev/null
ls -la /tmp/v1730_login_375.png

echo ""
echo "=== 3. 首页（访客模式 ?skip_login=1，桌面 1280） ==="
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-sandbox \
  --window-size=1280,900 \
  --virtual-time-budget=45000 \
  --screenshot=/tmp/v1730_home_desktop.png \
  "http://localhost:5174/?skip_login=1" 2>/dev/null
ls -la /tmp/v1730_home_desktop.png

echo ""
echo "=== 4. 首页（访客模式 ?skip_login=1，移动 375） ==="
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-sandbox \
  --window-size=375,812 \
  --virtual-time-budget=45000 \
  --screenshot=/tmp/v1730_home_mobile.png \
  "http://localhost:5174/?skip_login=1" 2>/dev/null
ls -la /tmp/v1730_home_mobile.png
