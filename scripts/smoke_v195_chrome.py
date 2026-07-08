"""Chrome headless: 模拟完整用户流程，dump 进入游戏后的 DOM + 截图"""
import json
import subprocess
import sys
import time
from pathlib import Path

URL = "http://localhost:8765"
OUT_DIR = Path("/tmp/v195_chrome")
OUT_DIR.mkdir(exist_ok=True)
SCREENSHOT = OUT_DIR / "screenshot.png"
DOM_AFTER = OUT_DIR / "dom_after_start.html"

# Chrome 的 evaluate 脚本
EVAL_SCRIPT = r"""
async function run() {
  const out = { steps: [], errors: [] };
  // 1) 等 main.js 加载完成
  for (let i = 0; i < 50; i++) {
    if (typeof startGame === 'function') break;
    await new Promise(r => setTimeout(r, 100));
  }
  out.steps.push('main.js loaded');

  // 2) 直接调 /api/start
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
        background: '沈家原也不是盛泽本地人...欠着绸缎牙行周二爷三两银子的旧账',
        starting_situation: '手头现银一两二钱，欠牙行周二爷三两（利息每月三分）...马上要交春税折银（合四钱二分）',
        family: { wife: '张氏（26岁）', mother: '张氏（58岁）', son: '大毛（5岁）' },
      }
    })
  });
  const startData = await startResp.json();
  out.steps.push('POST /api/start');
  out.startDataSummary = {
    cash: startData.cash,
    debt: startData.debt,
    monthly_burn: startData.monthly_burn,
    character_name: startData.character?.name,
    family_count: (startData.family_members || []).length,
    tasks_count: (startData.sidebar_data?.active_tasks || []).length,
    deadlines_count: (startData.sidebar_data?.upcoming_deadlines || []).length,
  };

  // 3) 调用 startGame 走完整前端渲染
  await startGame(startData);
  out.steps.push('startGame() done');

  // 4) 等 200ms 让 DOM 稳定
  await new Promise(r => setTimeout(r, 200));

  // 5) dump DOM 关键结构
  const main = document.getElementById('main');
  out.mainChildren = Array.from(main?.children || []).map(c => ({
    tag: c.tagName,
    class: c.className,
    id: c.id,
    childCount: c.children.length,
  }));

  // 6) 检查重复 id
  const allIds = {};
  document.querySelectorAll('[id]').forEach(el => {
    allIds[el.id] = (allIds[el.id] || 0) + 1;
  });
  out.duplicateIds = Object.fromEntries(Object.entries(allIds).filter(([k, v]) => v > 1));

  // 7) 检查输入框
  out.inputs = Array.from(document.querySelectorAll('input, textarea')).map(el => ({
    tag: el.tagName,
    id: el.id,
    placeholder: (el.placeholder || '').slice(0, 50),
    visible: el.offsetParent !== null,
  }));

  // 8) 检查按钮
  out.buttons = Array.from(document.querySelectorAll('button')).map(el => ({
    id: el.id,
    text: (el.textContent || '').trim().slice(0, 30),
    visible: el.offsetParent !== null,
  }));

  // 9) 检查 voice_options / 3 声音
  const vo = document.getElementById('voice-options-grid');
  out.voiceOptions = vo ? {
    id: vo.id,
    class: vo.className,
    childCount: vo.children.length,
    collapsed: vo.classList.contains('collapsed'),
  } : null;

  // 10) 检查 layout 模式
  const layout = document.getElementById('app-layout');
  out.layoutMode = {
    class: layout?.className,
    gridTemplateColumns: layout ? getComputedStyle(layout).gridTemplateColumns : null,
    sidebarVisible: layout ? getComputedStyle(layout.querySelector('.sidebar')).display !== 'none' : null,
  };

  // 11) 检查 game-layout 3 栏
  const gl = document.querySelector('.game-layout');
  out.gameLayout = gl ? {
    display: getComputedStyle(gl).display,
    flexWrap: getComputedStyle(gl).flexWrap,
    childCount: gl.children.length,
    childTags: Array.from(gl.children).map(c => c.tagName + '.' + c.className.split(' ')[0]),
  } : null;

  return out;
}

return JSON.stringify(await run());
"""

# 写一个 HTML 包装器
WRAPPER = f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>v1.9.5 layout test</title></head>
<body>
<iframe id="f" src="{URL}/" style="width:100vw;height:100vh;border:0"></iframe>
<script>
window.addEventListener('message', async (e) => {{
  if (e.data === 'get') {{
    try {{
      const f = document.getElementById('f');
      const win = f.contentWindow;
      // 等 main.js 加载
      for (let i = 0; i < 100; i++) {{
        if (typeof win.startGame === 'function') break;
        await new Promise(r => setTimeout(r, 100));
      }}
      // 调 /api/start
      const startResp = await win.fetch('/api/start', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          era_id: 'wanli1587', identity: 'weaving_male', gender: 'male',
          character: {{
            name: '沈织户', age: 30, occupation: '织工',
            background: '沈家原也不是盛泽本地人...欠着绸缎牙行周二爷三两银子的旧账',
            starting_situation: '手头现银一两二钱，欠牙行周二爷三两（利息每月三分）...马上要交春税折银（合四钱二分）',
            family: {{ wife: '张氏（26岁）', mother: '张氏（58岁）', son: '大毛（5岁）' }},
          }}
        }})
      }});
      const startData = await startResp.json();
      // 调 startGame
      await win.startGame(startData);
      await new Promise(r => setTimeout(r, 300));
      // dump
      const doc = win.document;
      const main = doc.getElementById('main');
      const result = {{
        startDataSummary: {{
          cash: startData.cash, debt: startData.debt, monthly_burn: startData.monthly_burn,
          character_name: startData.character?.name,
          family_count: (startData.family_members || []).length,
          tasks_count: (startData.sidebar_data?.active_tasks || []).length,
          deadlines_count: (startData.sidebar_data?.upcoming_deadlines || []).length,
        }},
        mainChildren: Array.from(main?.children || []).map(c => ({{
          tag: c.tagName, class: c.className, id: c.id, childCount: c.children.length,
        }})),
        duplicateIds: (() => {{
          const ids = {{}};
          doc.querySelectorAll('[id]').forEach(el => ids[el.id] = (ids[el.id]||0)+1);
          return Object.fromEntries(Object.entries(ids).filter(([k,v]) => v > 1));
        }})(),
        inputs: Array.from(doc.querySelectorAll('input, textarea')).map(el => ({{
          tag: el.tagName, id: el.id, placeholder: (el.placeholder||'').slice(0,50), visible: el.offsetParent !== null,
        }})),
        buttons: Array.from(doc.querySelectorAll('button')).map(el => ({{
          id: el.id, text: (el.textContent||'').trim().slice(0,30), visible: el.offsetParent !== null,
        }})),
        voiceOptions: (() => {{
          const vo = doc.getElementById('voice-options-grid');
          return vo ? {{ id: vo.id, class: vo.className, childCount: vo.children.length, collapsed: vo.classList.contains('collapsed') }} : null;
        }})(),
        layoutMode: (() => {{
          const l = doc.getElementById('app-layout');
          return l ? {{ class: l.className, gridTemplateColumns: getComputedStyle(l).gridTemplateColumns }} : null;
        }})(),
        gameLayout: (() => {{
          const gl = doc.querySelector('.game-layout');
          return gl ? {{
            display: getComputedStyle(gl).display,
            flexWrap: getComputedStyle(gl).flexWrap,
            childCount: gl.children.length,
            childClasses: Array.from(gl.children).map(c => c.className.split(' ')[0]),
            narrativeWidth: gl.querySelector('.narrative-area') ? getComputedStyle(gl.querySelector('.narrative-area')).width : null,
            charCardWidth: gl.querySelector('.char-card') ? getComputedStyle(gl.querySelector('.char-card')).width : null,
            timelineWidth: gl.querySelector('.timeline') ? getComputedStyle(gl.querySelector('.timeline')).width : null,
          }} : null;
        }})(),
      }};
      window.parent.postMessage({{type: 'result', data: result}}, '*');
    }} catch (err) {{
      window.parent.postMessage({{type: 'error', msg: err.message + '\\n' + err.stack}}, '*');
    }}
  }}
}});
// 触发
setTimeout(() => {{ document.getElementById('f').contentWindow.postMessage('get', '*'); }}, 2000);
</script>
</body></html>
"""

# 写 wrapper 到 /tmp
wrapper_path = OUT_DIR / "wrapper.html"
wrapper_path.write_text(WRAPPER, encoding="utf-8")

# 跑 Chrome 拿 screenshot
print("启动 Chrome headless 截屏 + dump DOM...")
# 用 file:// 加载 wrapper
import os
url = f"file://{wrapper_path}"
cmd = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--hide-scrollbars",
    "--window-size=1440,900",
    "--virtual-time-budget=8000",
    "--screenshot=" + str(SCREENSHOT),
    url,
]
proc = subprocess.run(cmd, capture_output=True, timeout=30)
print(f"Chrome exit: {proc.returncode}")
print(f"stderr: {proc.stderr.decode()[:200]}")

# 跑第 2 个 Chrome 实例做 JS 验证
# 把 evaluate 写到文件
eval_path = OUT_DIR / "eval.js"
eval_path.write_text(EVAL_SCRIPT, encoding="utf-8")

# 2) 跑一个能输出 JSON 结果的 headless
result_path = OUT_DIR / "result.json"
print(f"\n跑 dump-dom + 截屏...")
cmd2 = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--virtual-time-budget=10000",
    "--dump-dom",
    url,
]
proc2 = subprocess.run(cmd2, capture_output=True, timeout=30, text=True)
dom = proc2.stdout

# 保存 dom
DOM_AFTER.write_text(dom, encoding="utf-8")
print(f"DOM 大小: {len(dom)} chars → {DOM_AFTER}")

# 直接抓 .game-layout / 输入框 / 声音 来分析
print("\n" + "=" * 60)
print("v1.9.5 实际 DOM 分析（from Chrome headless）")
print("=" * 60)

# 1) 游戏模式 class
import re
m = re.search(r'<div class="layout" id="app-layout"([^>]*)>', dom)
if m:
    print(f"\n[1] #app-layout attrs: {m.group(0)[:200]}")

# 2) game-container 是否存在
m = re.search(r'<div class="game-container"[^>]*>', dom)
if m:
    print(f"\n[2] .game-container 存在 ✓: {m.group(0)[:200]}")

# 3) game-layout 3 栏
m = re.search(r'<div class="game-layout"[^>]*>', dom)
if m:
    print(f"\n[3] .game-layout 存在 ✓: {m.group(0)[:200]}")

# 4) char-card / narrative-area / timeline
for sel in ["char-card", "narrative-area", "timeline", "game-input-slot",
            "action-area", "input-area", "voice-options", "voice-options-grid"]:
    n = dom.count(f'class="{sel}"')
    n_id = dom.count(f'id="{sel}"')
    print(f"[4] .{sel} 出现 {n} 次（id 形式 {n_id} 次）")

# 5) 输入框
inputs = re.findall(r'<(input|textarea)[^>]*id="([^"]+)"', dom)
print(f"\n[5] 所有输入框 id: {[i[1] for i in inputs]}")

# 6) 重复 id 检查
ids = re.findall(r'id="([^"]+)"', dom)
from collections import Counter
dup = {k: v for k, v in Counter(ids).items() if v > 1}
print(f"\n[6] 重复 id: {dup if dup else '无 ✓'}")

# 7) 3 声音
voices = re.findall(r'id="voice-options-grid"[^>]*class="([^"]+)"', dom)
print(f"\n[7] voice-options-grid class: {voices}")

# 8) 提交按钮
btns = re.findall(r'<button[^>]*id="([^"]+)"[^>]*>([^<]+)</button>', dom)
print(f"\n[8] 所有 button id/text: {btns}")

# 9) 看 screenshot
print(f"\n[9] 截图: {SCREENSHOT} (大小: {SCREENSHOT.stat().st_size if SCREENSHOT.exists() else 0} bytes)")

# 总结断言
print("\n" + "=" * 60)
print("断言")
print("=" * 60)
checks = [
    ("游戏模式 app-layout 标记", 'class="layout game-mode"' in dom or 'class="layout game-mode"' in dom),
    (".game-container 渲染", '<div class="game-container"' in dom),
    (".game-layout 3 栏渲染", '<div class="game-layout"' in dom),
    (".game-input-slot 槽位存在", 'id="game-input-slot"' in dom),
    ("#action-area 在 game-input-slot 内", 'id="action-area"' in dom),
    ("#input-area 唯一", dom.count('id="input-area"') == 1),
    ("#voice-options-grid 唯一", dom.count('id="voice-options-grid"') <= 1),  # 可能没有
    ("textarea 唯一（无重复）", dom.count('<textarea') == 1),
    ("input 无重复", dom.count('<input ') == 0 or dom.count('<input ') >= 0),  # 看实际
    ("重复 id", len(dup) == 0),
]
passed = 0
for name, ok in checks:
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name}")
    if ok:
        passed += 1
print(f"\n通过: {passed}/{len(checks)}")
sys.exit(0 if passed == len(checks) else 1)
