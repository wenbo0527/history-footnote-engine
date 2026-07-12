#!/bin/bash
# 🆕 v2.10.1 W52 P2-3: deploy-pre-start.sh（升级版：check + auto-fix）
#
# 目的：防止 git reset --hard / 升级时丢失版本号对齐
# 永远在服务启动前自动跑一次
#
# 模式：
#   默认：check-only（只检查，发现错误 exit 1）
#   FIX=1：auto-fix（自动对齐版本号）
#
# 用法：
#   bash scripts/deploy-pre-start.sh            # 仅检查
#   FIX=1 bash scripts/deploy-pre-start.sh      # 自动修复
#   bash scripts/deploy-pre-start.sh --fix      # 自动修复（cli 形式）
#
# 影响的 6 处：
#   1. CHANGELOG.md 顶部段
#   2. src/history_footnote/__init__.py 的 __version__
#   3. src/frontend/package.json 的 "version"
#   4. src/frontend/src/app.html 的版本标识
#   5. README.md 的版本徽章
#   6. docs/design/v2.7.1-后续TODO.md 的 v2.10.0 收官段

set -e

VERSION="${VERSION:-v2.10.1}"
VERSION_NO_V="${VERSION#v}"

# 是否 auto-fix
AUTO_FIX=0
if [ "${FIX:-0}" = "1" ] || [ "$1" = "--fix" ]; then
  AUTO_FIX=1
fi

echo "[deploy-pre-start] 对齐版本号到 $VERSION (fix=$AUTO_FIX) ..."

fix_or_check() {
  # $1 = 文件路径
  # $2 = 描述
  # $3 = 检查命令 (grep -q ...)
  # $4 = 修复命令 (sed -i ...)
  local file="$1"
  local desc="$2"
  local check_cmd="$3"
  local fix_cmd="$4"

  if [ ! -f "$file" ]; then
    echo "[deploy-pre-start] ⚠️  $file 不存在（跳过）"
    return 0
  fi

  if eval "$check_cmd" 2>/dev/null; then
    echo "[deploy-pre-start] ✅ $desc"
    return 0
  fi

  if [ "$AUTO_FIX" = "1" ]; then
    echo "[deploy-pre-start] 🔧 修复 $desc"
    eval "$fix_cmd"
    if eval "$check_cmd" 2>/dev/null; then
      echo "[deploy-pre-start] ✅ 修复成功"
      return 0
    else
      echo "[deploy-pre-start] ❌ 修复失败,请手动检查"
      return 1
    fi
  else
    echo "[deploy-pre-start] ❌ $desc 不匹配 $VERSION（FIX=1 自动修复）"
    return 1
  fi
}

EXIT_CODE=0

# 1. CHANGELOG.md 顶部段
fix_or_check \
  "CHANGELOG.md" \
  "CHANGELOG.md 含 $VERSION 段" \
  "grep -q '## \[$VERSION\]' CHANGELOG.md" \
  "sed -i '' '/^## \[Unreleased\]/a\\
\\
## [$VERSION] - '$(date +%Y-%m-%d)'\\
' CHANGELOG.md" \
  || EXIT_CODE=1

# 2. src/history_footnote/__init__.py
fix_or_check \
  "src/history_footnote/__init__.py" \
  "__init__.py __version__=$VERSION" \
  "grep -q '__version__.*$VERSION' src/history_footnote/__init__.py" \
  "sed -i '' 's/__version__ = .*/__version__ = \"$VERSION\"/' src/history_footnote/__init__.py" \
  || EXIT_CODE=1

# 3. src/frontend/package.json
fix_or_check \
  "src/frontend/package.json" \
  "package.json version=$VERSION_NO_V" \
  "[ \"\$(grep -oE '\"version\":[[:space:]]*\"[^\"]*\"' src/frontend/package.json | head -1 | cut -d'\"' -f4)\" = \"$VERSION_NO_V\" ]" \
  "sed -i '' 's/\"version\":[[:space:]]*\"[^\"]*\"/\"version\": \"$VERSION_NO_V\"/' src/frontend/package.json" \
  || EXIT_CODE=1

# 4. src/frontend/src/app.html
fix_or_check \
  "src/frontend/src/app.html" \
  "app.html 含 $VERSION" \
  "grep -q '$VERSION' src/frontend/src/app.html" \
  "sed -i '' 's|<title>[^<]*</title>|<title>历史注脚 '$VERSION' · AI 驱动的明朝万历年间生存模拟</title>|' src/frontend/src/app.html" \
  || EXIT_CODE=1

# 5. README.md
fix_or_check \
  "README.md" \
  "README.md 含 $VERSION" \
  "grep -q '$VERSION' README.md" \
  "sed -i '' 's|v[0-9]*\.[0-9]*\.[0-9]*|[!]('$VERSION')|' README.md" \
  || EXIT_CODE=1

# 6. docs/design/v2.7.1-后续TODO.md
fix_or_check \
  "docs/design/v2.7.1-后续TODO.md" \
  "TODO 文档含 v2.10.0 收官段" \
  "grep -q 'v2.10.0 收官' docs/design/v2.7.1-后续TODO.md" \
  "echo '' >> docs/design/v2.7.1-后续TODO.md && echo '## v2.10.0 收官' >> docs/design/v2.7.1-后续TODO.md" \
  || EXIT_CODE=1

if [ $EXIT_CODE -eq 0 ]; then
  echo "[deploy-pre-start] ✅ 版本号对齐完成（$VERSION）"
else
  echo "[deploy-pre-start] ⚠️  存在不匹配项（FIX=1 自动修复,或手动修复）"
fi

exit $EXIT_CODE