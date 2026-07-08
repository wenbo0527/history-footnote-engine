#!/bin/bash
# 看 game 页的 DOM 状态
SESSION_ID="wanli1587_20260708_111459"
URL="http://localhost:5174/game/?session=$SESSION_ID"

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-sandbox \
  --window-size=1280,900 \
  --virtual-time-budget=15000 \
  --dump-dom \
  "$URL" 2>/dev/null > /tmp/game_dom.html

# 检查关键元素
echo "=== DOM 关键元素检查 ==="
grep -c "game-view" /tmp/game_dom.html | head -1 | awk '{print "game-view:", $1, "次"}'
grep -c "game-main" /tmp/game_dom.html | head -1 | awk '{print "game-main:", $1, "次"}'
grep -c "game-char" /tmp/game_dom.html | head -1 | awk '{print "game-char:", $1, "次"}'
grep -c "game-timeline" /tmp/game_dom.html | head -1 | awk '{print "game-timeline:", $1, "次"}'
grep -c "narrative" /tmp/game_dom.html | head -1 | awk '{print "narrative:", $1, "次"}'
grep -c "加载中" /tmp/game_dom.html | head -1 | awk '{print "加载中:", $1, "次"}'
grep -c "万历" /tmp/game_dom.html | head -1 | awk '{print "万历:", $1, "次"}'

echo ""
echo "=== error 提示 ==="
grep -oE "error[^<]*" /tmp/game_dom.html | head -5
