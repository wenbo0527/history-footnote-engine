// UI 比例分析：访问 game 页，截全屏 + 量各区域尺寸
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  await page.goto('http://localhost:5173/game?session=wanli1587_20260708_163051', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);

  // 测各区域比例
  const layout = await page.evaluate(() => {
    const get = (sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) };
    };
    return {
      viewport: { w: window.innerWidth, h: window.innerHeight },
      charCard: get('.char-card'),
      narrative: get('.narrative-area'),
      timeline: get('.game-timeline'),
      input: get('.game-input'),
      voiceOptions: get('.voice-options'),
      loadingOverlay: get('.loading-overlay'),
      timelineRight: get('.game-timeline aside, .game-timeline'),
    };
  });
  console.log('=== viewport ===', JSON.stringify(layout.viewport));
  console.log('=== 各区域 ===');
  for (const [k, v] of Object.entries(layout)) {
    if (k === 'viewport') continue;
    console.log(`  ${k}:`, JSON.stringify(v));
  }
  // 比例计算
  if (layout.charCard && layout.narrative && layout.timeline) {
    const total = layout.charCard.w + layout.narrative.w + layout.timeline.w;
    console.log('\n=== 三栏比例 ===');
    console.log(`  CharCard: ${layout.charCard.w}px (${Math.round(layout.charCard.w / total * 100)}%)`);
    console.log(`  Narrative: ${layout.narrative.w}px (${Math.round(layout.narrative.w / total * 100)}%)`);
    console.log(`  Timeline: ${layout.timeline.w}px (${Math.round(layout.timeline.w / total * 100)}%)`);
  }
  // 黄金分割 1.618 对比
  if (layout.narrative) {
    const golden = layout.viewport.w / 1.618;
    console.log(`\n  黄金比例 width (1.618): ${Math.round(golden)}px (当前 narrative ${layout.narrative.w}px, 偏 ${layout.narrative.w > golden ? '宽' : '窄'} ${Math.abs(Math.round(layout.narrative.w - golden))}px)`);
  }

  // 截图
  await page.screenshot({ path: '/tmp/ui_review.png', fullPage: true });
  await browser.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
