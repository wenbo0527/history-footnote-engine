"""清理 v1.7.30 4 档断点 - 简单字符串版本"""
from pathlib import Path

css = Path("/Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/web/static/css/main.css")
content = css.read_text(encoding="utf-8")

# 找 v1.7.30 块起始 + 块结束
start_marker = "/* 🆕 v1.7.30 完整响应式（断点系统：4 档） */"
end_marker = "/* 触摸设备优化 */"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx < 0 or end_idx < 0:
    print(f"❌ start_idx={start_idx}, end_idx={end_idx}")
else:
    # 找 start 块的前导 "/* ====" 
    block_start = content.rfind("/* ==", 0, start_idx)
    # 找 end 块的前导 "/* ====" 
    block_end = content.rfind("/* ====", end_idx, end_idx)
    # 整个替换 = 从 block_start 到 end_idx
    old = content[block_start:end_idx]
    new = """/* ============================================================ */
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
    content = content[:block_start] + new + content[end_idx:]
    css.write_text(content, encoding="utf-8")
    print(f"✅ 替换成功（block_start={block_start}, end_idx={end_idx}）")
    print(f"  删了 {end_idx - block_start} 字符，新增 {len(new)} 字符")
