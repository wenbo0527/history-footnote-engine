#!/bin/bash
# 🆕 v2.10.1 W66: deploy-pre-start.sh
#
# 目的：防止 git reset --hard / 升级时丢失版本号对齐
# 永远在服务启动前自动跑一次
#
# 用法：
#   bash scripts/deploy-pre-start.sh
#
# 影响：1 分钟内完成 6 处版本号对齐

set -e

VERSION="v2.10.1"
echo "[deploy-pre-start] 对齐版本号到 $VERSION ..."

# 1. CHANGELOG 顶部段
if [ -f CHANGELOG.md ]; then
  if ! grep -q "## \[$VERSION\]" CHANGELOG.md; then
    echo "[deploy-pre-start] ❌ CHANGELOG.md 缺 $VERSION 段"
    exit 1
  fi
fi

# 2. src/history_footnote/__init__.py
if [ -f src/history_footnote/__init__.py ]; then
  if ! grep -q "__version__.*$VERSION" src/history_footnote/__init__.py; then
    echo "[deploy-pre-start] ❌ __init__.py 缺 $VERSION"
    exit 1
  fi
fi

# 3. src/frontend/package.json
if [ -f src/frontend/package.json ]; then
  PKG_VERSION=$(grep -oE '"version":\s*"[^"]*"' src/frontend/package.json | head -1 | cut -d'"' -f4)
  if [ "$PKG_VERSION" != "${VERSION#v}" ]; then
    echo "[deploy-pre-start] ❌ package.json 版本 $PKG_VERSION != $VERSION"
    exit 1
  fi
fi

# 4. src/frontend/src/app.html
if [ -f src/frontend/src/app.html ]; then
  if ! grep -q "$VERSION" src/frontend/src/app.html; then
    echo "[deploy-pre-start] ❌ app.html 缺 $VERSION"
    exit 1
  fi
fi

# 5. README.md
if [ -f README.md ]; then
  if ! grep -q "$VERSION" README.md; then
    echo "[deploy-pre-start] ❌ README.md 缺 $VERSION"
    exit 1
  fi
fi

# 6. docs/CHANGELOG / TODO 顶部
if [ -f docs/design/v2.7.1-后续TODO.md ]; then
  if ! grep -q "v2.10.0 收官" docs/design/v2.7.1-后续TODO.md; then
    echo "[deploy-pre-start] ⚠️  TODO 文档缺 v2.10.0 段（不致命）"
  fi
fi

echo "[deploy-pre-start] ✅ 版本号对齐完成（$VERSION）"
