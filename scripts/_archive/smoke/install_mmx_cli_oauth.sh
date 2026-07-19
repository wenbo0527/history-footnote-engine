#!/bin/bash
# 🆕 v2.7+ mmx-cli 安装 + OAuth 配置脚本
# 目的：让 history_footnote 项目能用 mmx-cli 集成图像/视频/语音/音乐能力
#
# 安全说明：
# - 使用 OAuth（mmx auth login --recommend），避免 API key 出现在命令行
# - 浏览器授权（RFC 8628 + PKCE）
# - 凭证存 ~/.mmx/config.json（access_token + refresh_token，token 自动刷新）
#
# 使用方法：
#   1. review 这个脚本
#   2. 在终端执行：bash scripts/install_mmx_cli_oauth.sh
#   3. OAuth 步骤会在浏览器打开，授权即可
#
# 参考：https://github.com/MiniMax-AI/cli
set -e

echo "=========================================="
echo "  mmx-cli 安装 + OAuth 配置"
echo "=========================================="
echo ""

# ============================================================
# 步骤 1: 全局安装 mmx-cli
# ============================================================
echo "▶ 步骤 1/4: 全局安装 mmx-cli..."
if command -v mmx &> /dev/null; then
    MMX_VERSION=$(mmx --version 2>&1)
    echo "  ✅ mmx 已安装：$MMX_VERSION"
    echo "  （如需升级：mmx update）"
else
    npm install -g mmx-cli
    echo "  ✅ mmx-cli 安装完成"
fi

# 验证
echo ""
echo "▶ 验证安装："
mmx --version
echo ""

# ============================================================
# 步骤 2: 安装官方 SKILL（给 AI agent 用）
# ============================================================
echo "▶ 步骤 2/4: 安装官方 SKILL（npx skills add MiniMax-AI/cli -y -g）"
echo "  这会让 Claude Code / Cursor / Trae 等 AI agent 知道 mmx-cli 的能力"
npx skills add MiniMax-AI/cli -y -g
echo "  ✅ SKILL 安装完成"
echo ""

# ============================================================
# 步骤 3: OAuth 登录（推荐方式）
# ============================================================
echo "▶ 步骤 3/4: OAuth 登录（浏览器授权）"
echo "  - 接下来 mmx auth login 会打印 device code + 打开浏览器"
echo "  - 在浏览器输入 code 完成授权"
echo "  - 凭证存 ~/.mmx/config.json（access_token + refresh_token）"
echo "  - token 自动刷新（5 分钟 buffer）"
echo ""
mmx auth login --recommend
echo ""
echo "  验证登录状态："
mmx auth status
echo ""

# ============================================================
# 步骤 4: 查看 quota（确认整体配置生效）
# ============================================================
echo "▶ 步骤 4/4: 查看 Token Plan 余额"
mmx quota
echo ""

echo "=========================================="
echo "  ✅ mmx-cli 安装 + 配置完成"
echo "=========================================="
echo ""
echo "现在你可以用 mmx 命令："
echo "  mmx text chat --message 'hello'"
echo "  mmx image 'a cat in spacesuit'"
echo "  mmx speech synthesize --text '你好' --out hi.mp3"
echo "  mmx video generate --prompt 'ocean waves' --download out.mp4"
echo "  mmx music generate --prompt 'upbeat pop' --out song.mp3"
echo "  mmx vision photo.jpg"
echo "  mmx search 'history footnote engine'"
echo ""
echo "下一步：把 mmx 集成到 history_footnote 的图像/语音/视频功能"
