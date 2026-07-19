"""v1.9.5 验证 3 声音 + 财务/待办/还债日"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

URL = "http://localhost:8765"
OUT_DIR = Path("/tmp/v195_voice")
OUT_DIR.mkdir(exist_ok=True)

HOOK_JS = r"""
(async () => {
  if (window.__testHookInjected) return;
  window.__testHookInjected = true;
  for (let i = 0; i < 50; i++) {
    if (typeof window.startGame === 'function') break;
    await new Promise(r => setTimeout(r, 100));
  }
  // 清掉 localStorage 的旧 voice 偏好
  try { localStorage.removeItem("hfe_voice_options_collapsed"); } catch(_){}
  // 清掉 EXPLICIT 标志
  window.__VOICE_PREFS_EXPLICIT = false;
  const startResp = await fetch('/api/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      era_id: 'wanli1587', identity: 'weaving_male', gender: 'male',
      character: { name: '沈织户', age: 30, occupation: '织工', hometown: '盛泽镇' }
    })
  });
  const startData = await startResp.json();
  await window.startGame(startData);
  await new Promise(r => setTimeout(r, 500));
  // dump
  const $toggle = document.querySelector('.voice-options-toggle');
  const $grid = document.getElementById('voice-options-grid');
  const $options = document.querySelectorAll('.voice-option-btn');
  const $actionArea = document.getElementById('action-area');
  const dump = {
    hasToggle: !!$toggle,
    toggleAriaExpanded: $toggle ? $toggle.getAttribute('aria-expanded') : null,
    toggleIcon: $toggle ? $toggle.querySelector('.voice-options-toggle-icon')?.textContent : null,
    gridClass: $grid ? $grid.className : null,
    gridCollapsed: $grid ? $grid.classList.contains('collapsed') : null,
    gridDisplay: $grid ? getComputedStyle($grid).display : null,
    gridHeight: $grid ? $grid.offsetHeight : null,
    optionsCount: $options.length,
    optionsText: Array.from($options).map(b => b.textContent.trim().slice(0, 30)),
    actionAreaExists: !!$actionArea,
    actionAreaVisible: $actionArea ? $actionArea.offsetParent !== null : null,
  };
  // 写入 DOM
  const pre = document.createElement('pre');
  pre.id = '__voice_dump__';
  pre.style.display = 'none';
  pre.textContent = JSON.stringify(dump, null, 2);
  document.body.appendChild(pre);
  document.title = '__test_done__';
})();
"""

main_js = Path("src/history_footnote/web/static/js/main.js")
backup = main_js.read_text(encoding="utf-8")
try:
    inject = f"\nif (window.location.search.includes('__test__')) {{ (async () => {{ {HOOK_JS} }})() }}\n"
    main_js.write_text(backup + inject, encoding="utf-8")
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-sandbox",
        "--window-size=1440,900",
        "--virtual-time-budget=15000",
        "--dump-dom",
        f"{URL}/?__test__=1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
    dom = proc.stdout
    (OUT_DIR / "dom.html").write_text(dom, encoding="utf-8")
    # 提取 dump
    m = re.search(r'<pre id="__voice_dump__"[^>]*>(.+?)</pre>', dom, re.DOTALL)
    if m:
        import html
        data = json.loads(html.unescape(m.group(1)))
        print("=" * 60)
        print("3 声音 + 财务/待办/还债日 验证")
        print("=" * 60)
        for k, v in data.items():
            print(f"  {k}: {v}")
        print("=" * 60)
        # 断言
        checks = [
            ("toggle 存在", data["hasToggle"]),
            ("aria-expanded=true (展开)", data["toggleAriaExpanded"] == "true"),
            ("icon ▾ (展开)", data["toggleIcon"] == "▾"),
            ("grid 不含 collapsed", not data["gridCollapsed"]),
            ("grid display 不为 none", data["gridDisplay"] != "none"),
            ("3 个 voice-option-btn (排除自由)", data["optionsCount"] == 4),  # 3 真实 + 1 自由
            ("4 个按钮包含'先看看家里情况'", any("先看看家里情况" in t for t in data["optionsText"])),
            ("包含'出门找活路'", any("出门找活路" in t for t in data["optionsText"])),
            ("包含'先顾眼前'", any("先顾眼前" in t for t in data["optionsText"])),
            ("包含'自由输入'", any("自由输入" in t for t in data["optionsText"])),
            ("action-area 存在", data["actionAreaExists"]),
        ]
        passed = 0
        for name, ok in checks:
            mark = "✅" if ok else "❌"
            print(f"  {mark} {name}")
            if ok:
                passed += 1
        print(f"\n通过: {passed}/{len(checks)}")
    else:
        print("没找到 voice dump")
finally:
    main_js.write_text(backup, encoding="utf-8")
    print("已恢复 main.js")
