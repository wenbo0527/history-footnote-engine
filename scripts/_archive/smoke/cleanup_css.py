"""清理 v1.7.30 4 档断点，替换为 v1.9.5 简化 2 档"""
from pathlib import Path

css = Path("main.css")
content = css.read_text(encoding="utf-8")

# 找 line 1805 起到下一个 "/* ===" 块（v1.7.30 4 档断点）
import re
# 匹配 v1.7.30 4 档断点区块
pattern = re.compile(
    r"/\* ={30,}\s*\n/\* 🆕 v1\.7\.30 完整响应式.*?\n/\* ={30,}\s*\n"
    r"[\s\S]*?"
    r"\*/\s*\n",
    re.MULTILINE
)
matches = pattern.findall(content)
print(f"找到 {len(matches)} 个 v1.7.30 断点块")
for m in matches:
    print(f"  - {m[:100].strip()}")

if matches:
    # 第一个就是 v1.7.30 4 档断点
    new_section = """/* ============================================================ */
/* 🆕 v1.9.5 简化响应式（2 档：桌面 / 移动）                          */
/* v1.7.30 4 档断点已删除（sidebar 永远隐藏，不需要断点）              */
/* ============================================================ */

/* 桌面端（≥768px）：body 字体略大 */
@media (min-width: 768px) {
  body {
    font-size: 15px;
  }
}

/* 移动端（≤767px）：紧凑布局 + 单列 */
@media (max-width: 767px) {
  body {
    font-size: 14px;
  }
  /* 触摸优化 */
  button, .voice-option, .archive-item {
    min-height: 44px;
  }
  .input-area textarea {
    font-size: 16px;
  }
  /* 🆕 v1.9.5：移动端单列堆叠由 .game-layout flex-wrap 负责 */
  .game-layout > * { flex: 0 0 100% !important; }
  /* 🆕 v1.9.5：游戏页顶部 banner 在移动端压缩 */
  .game-header { padding: 12px 16px !important; }
  .game-header > div:last-child { font-size: 12px !important; gap: 8px !important; }
  .modal-content { width: 95vw !important; max-height: 90vh !important; }
}
"""
    content = content.replace(matches[0], new_section, 1)
    css.write_text(content, encoding="utf-8")
    print("✅ 已替换")
else:
    print("❌ 没找到")
