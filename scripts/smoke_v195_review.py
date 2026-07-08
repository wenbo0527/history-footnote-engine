"""Chrome headless 完整 review: 截全屏 + 多视口宽度 + 看输入区"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

URL_BASE = "http://localhost:8765"
OUT_DIR = Path("/tmp/v195_review")
OUT_DIR.mkdir(exist_ok=True)

HOOK_JS = r"""
(async () => {
  if (window.__testHookInjected) return;
  window.__testHookInjected = true;
  for (let i = 0; i < 50; i++) {
    if (typeof window.startGame === 'function') break;
    await new Promise(r => setTimeout(r, 100));
  }
  const startResp = await fetch('/api/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      era_id: 'wanli1587',
      identity: 'weaving_male',
      gender: 'male',
      character: {
        name: '沈织户',
        age: 30,
        occupation: '织工',
        hometown: '盛泽镇',
        background: '沈家原也不是盛泽本地人...欠着绸缎牙行周二爷三两银子的旧账',
        starting_situation: '手头现银一两二钱，欠牙行周二爷三两（利息每月三分）...马上要交春税折银（合四钱二分）',
        family: { wife: '张氏（26岁）', mother: '沈氏（58岁）', son: '大毛（5岁）' },
      }
    })
  });
  const startData = await startResp.json();
  window.__testData = startData;
  await window.startGame(startData);
  // 滚动到底部让 3 声音 + 输入框显示
  setTimeout(() => window.scrollTo(0, document.body.scrollHeight), 500);
  document.title = '__test_done__';
})();
"""

main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")

try:
    inject = f"\n\n/* __test_hook__ */\nif (window.location.search.includes('__test__')) {{ {HOOK_JS} }}\n"
    main_js.write_text(backup + inject, encoding="utf-8")
    print("已注入测试 hook")

    # 多个视口宽度截图
    viewports = [
        ("1920x1080", 1920, 1080),
        ("1440x900", 1440, 900),
        ("1280x720", 1280, 720),
        ("1024x768", 1024, 768),
        ("375x667", 375, 667),  # 移动端
    ]
    for label, w, h in viewports:
        out = OUT_DIR / f"screen_{label}.png"
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            f"--window-size={w},{h}",
            "--virtual-time-budget=12000",
            f"--screenshot={out}",
            f"{URL_BASE}/?__test__=1",
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        print(f"[{label}] 截图: {out.stat().st_size if out.exists() else 0} bytes")

    # dump DOM
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--virtual-time-budget=15000",
        "--dump-dom",
        f"{URL_BASE}/?__test__=1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
    dom = proc.stdout
    (OUT_DIR / "dom_after.html").write_text(dom, encoding="utf-8")
    print(f"\nDOM: {len(dom)} chars")

finally:
    main_js.write_text(backup, encoding="utf-8")
    print("已恢复 main.js")

# 分析 char-card 的内容
print("\n" + "=" * 60)
print("char-card 内容检查")
print("=" * 60)
m = re.search(r'<aside class="char-card"[^>]*>(.*?)</aside>', dom, re.DOTALL)
if m:
    char_inner = m.group(1)
    # 提取关键文本
    texts = re.findall(r'>([^<]{2,30})<', char_inner)
    print("  文本片段:", [t.strip() for t in texts if t.strip()])

# 分析 char-card 名字
m_name = re.search(r'<h3[^>]*>([^<]+)</h3>', dom)
if m_name:
    print(f"  char-card 名字: {m_name.group(1)!r}")

# sidebar 状态
print("\n" + "=" * 60)
print("layout 状态")
print("=" * 60)
m_layout = re.search(r'<div class="layout"([^>]*)>', dom)
if m_layout:
    print(f"  app-layout class: {m_layout.group(0)[:200]}")

# 看 sidebar 是否隐藏
m_side = re.search(r'<div class="sidebar"[^>]*>', dom)
if m_side:
    print(f"  sidebar 元素: {m_side.group(0)[:200]}")

# 输入区 + 3 声音
print("\n" + "=" * 60)
print("输入区 + 3 声音")
print("=" * 60)
m_act = re.search(r'<div class="action-area"[^>]*>(.*?)</div>\s*</div>\s*</div>', dom, re.DOTALL)
if m_act:
    act_inner = m_act.group(1)
    print(f"  action-area 长度: {len(act_inner)} chars")
    # 提取 voice-option-btn 名称
    names = re.findall(r'<span class="voice-name">([^<]+)</span>', act_inner)
    print(f"  声音按钮: {names}")
    # 提取 textarea
    ta = re.search(r'<textarea[^>]*placeholder="([^"]+)"', act_inner)
    if ta:
        print(f"  textarea placeholder: {ta.group(1)[:80]}")
    # 提取 btn_submit
    btn = re.search(r'<button[^>]*id="btn_submit"[^>]*>([^<]+)</button>', act_inner)
    if btn:
        print(f"  btn_submit text: {btn.group(1)}")

# 视觉/排版 review
print("\n" + "=" * 60)
print("自适应宽度（多视口）")
print("=" * 60)
import os
for f in sorted(OUT_DIR.glob("screen_*.png")):
    size = os.path.getsize(f)
    print(f"  {f.name}: {size} bytes")
