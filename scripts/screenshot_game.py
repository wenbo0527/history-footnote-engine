"""截图 game 页（用 mock data）"""
import time, subprocess
from pathlib import Path

# mock data 注入脚本
mock_js = """
if (window.location.search.includes('demo=1')) {
  setTimeout(() => {
    const m = document.querySelector('script[type=\"module\"]');
    // 直接通过全局 store 注入
    if (window.__svelte && window.__svelte.set) {
      // Svelte 5 没有这个 API
    }
    // 通过 URL 走 store
    const script = document.createElement('script');
    script.type = 'module';
    script.textContent = `
      import { gameActions } from '/src/lib/stores/game.svelte.ts';
      gameActions.set(MOCK_GAME);
    `;
    document.body.appendChild(script);
  }, 1000);
}
"""

# 简化：直接通过 store 注入
mock_data_script = """
const MOCK_GAME = {
  session_id: 'demo-1',
  account_username: 'demo',
  character: { name: '沈织户', age: 30, occupation: '织工', hometown: '盛泽镇' },
  family: [
    { relation: '妻', name: '张氏', age: 27, status: '在世' },
    { relation: '母', name: '沈王氏', age: 58, status: '在世' },
    { relation: '子', name: '大毛', age: 7, status: '在世' }
  ],
  skills: [
    { name: '挽丝', level: 3 },
    { name: '织绸', level: 2 }
  ],
  city: '盛泽镇',
  year_current: 1587,
  year_max: 1601,
  round_current: 1,
  cash: 1.20,
  rice: 0,
  looms: 1,
  debt: 3.60,
  monthly_burn: 0.42,
  reputation: 5,
  identity: 'weaving_male',
  gender: 'male',
  era_id: 'wanli1587',
  timeline: [
    { year: 1587, event: '你出生', highlight: false },
    { year: 1588, event: '入行学徒', highlight: false },
    { year: 1596, event: '矿税监设立', highlight: false },
    { year: 1601, event: '葛贤抗税', highlight: true }
  ],
  sidebar: {
    active_tasks: [
      { title: '送牙行束脩（约 1.2 两）', urgency: 'high' },
      { title: '购置干青桑叶', urgency: 'medium' }
    ],
    upcoming_deadlines: [
      { name: '赵牙人束脩', days_estimate: 10, amount: '1.20 两' }
    ],
    financial_status: { cash: 1.20, rice: 0, debt: 3.60, monthly_burn: 0.42 }
  },
  narrative: {
    round: 1,
    content: `欢迎来到【万历十五年】

你是 沈青山 — 苏州府吴江县盛泽镇东栅巷
家庭：妻张氏 27岁，操持灶房与机后的事；子大毛 7岁尚未开蒙、二丫头 4岁常跟在张氏脚边；母沈王氏 58岁半瘫在床，住在后屋。

【来历】
沈家原在吴江县城外，祖上以耕读传家。祖父辈在镇上开过一间小当铺，后被倭寇烧毁，家道中落。父亲沈青山自幼随邻人学织，到你这辈已是第三代织工。

【开局处境】
万历十五年十月廿三。手里现银只有四钱三分，欠牙行束脩一两二钱。米缸见底，老娘的药快没了。

十月的夜来得早。沈青山从织机前站起身的时候，膝盖咯吧一响，腰像是被人拿绳子勒过一道。张氏在后屋哄二丫头睡着了，灶房里还有一点药味没散——是给老娘熬的最后一副。`,
    type: 'opening',
    created_at: '2026-07-08'
  },
  narrative_history: [],
  last_voice_options: [
    { voice_id: 'v1', voice_name: '先看看家里情况', intent_text: '我先扫一眼家里有什么，银钱还剩多少，灶房是什么光景' },
    { voice_id: 'v2', voice_name: '出门找活路', intent_text: '我去牙行问最近有没有活计可接' },
    { voice_id: 'v3', voice_name: '先顾眼前', intent_text: '我想想今天的米缸还够不够，今天必须先吃饱' },
    { voice_id: 'free', voice_name: '✍️ 自由输入', intent_text: '都不对？自己描述要做什么', is_freetext: true }
  ]
};

// 注入到全局
window.MOCK_GAME = MOCK_GAME;
"""

# 用浏览器直接加载
for name, w, h in [("desktop", 1280, 900), ("mobile", 375, 812)]:
    out = f"/tmp/v2_game_{name}.png"
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-sandbox",
        f"--window-size={w},{h}",
        "--virtual-time-budget=20000",
        f"--screenshot={out}",
        f"http://localhost:5174/game/?demo=1"
    ]
    subprocess.run(cmd, capture_output=True, timeout=30)
    print(f"{name}: {out}")
    time.sleep(2)
print("Done")
