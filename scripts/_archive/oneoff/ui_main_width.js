// 验证: main 占据视觉中心（>= 60%）
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const SID = 'wanli1587_20260708_163051';
  const vps = [
    { name: '1280', w: 1280, h: 800 },
    { name: '1440', w: 1440, h: 900 },
    { name: '1920', w: 1920, h: 1080 },
  ];
  for (const vp of vps) {
    const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h } });
    const page = await ctx.newPage();
    await page.goto(`http://localhost:5173/game?session=${SID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4500);

    const m = await page.evaluate(() => {
      const get = (sel) => {
        const el = document.querySelector(sel);
        return el ? el.getBoundingClientRect().width : null;
      };
      return {
        char: get('.char-card'),
        main: get('.game-main'),
        timeline: get('.timeline-archive'),
      };
    });
    const total = m.char + m.main + m.timeline;
    console.log(`\n=== ${vp.name} ===  total=${total}`);
    console.log(`  char:    ${m.char}px (${Math.round(m.char/total*100)}%)`);
    console.log(`  main:    ${m.main}px (${Math.round(m.main/total*100)}%)  ← 故事主体`);
    console.log(`  timeline:${m.timeline}px (${Math.round(m.timeline/total*100)}%)`);
    const verdict = m.main / total >= 0.6 ? '✅ 主体' : '❌ 偏小';
    console.log(`  视觉中心判定: ${verdict}`);

    await page.screenshot({ path: `/tmp/main_width_${vp.name}.png`, fullPage: false });
    await ctx.close();
  }
  await browser.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
