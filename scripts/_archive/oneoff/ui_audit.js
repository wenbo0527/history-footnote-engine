// 完整 UI 体检：7 个 viewport + 关键交互验证
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const SID = 'wanli1587_20260708_163051';
  const vps = [
    { name: 'mobile-375',  w: 375,  h: 812 },
    { name: 'mobile-414',  w: 414,  h: 896 },
    { name: 'tablet-768',  w: 768,  h: 1024 },
    { name: 'tablet-1023', w: 1023, h: 768 },
    { name: 'desktop-1280',w: 1280, h: 800 },
    { name: 'desktop-1440',w: 1440, h: 900 },
    { name: 'wide-1920',  w: 1920, h: 1080 },
  ];

  const issues = [];

  for (const vp of vps) {
    const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h } });
    const page = await ctx.newPage();
    page.on('pageerror', e => issues.push(`[${vp.name} page-error] ${e.message}`));
    page.on('console', m => { if (m.type() === 'error') issues.push(`[${vp.name} console] ${m.text().substring(0,200)}`); });

    await page.goto(`http://localhost:5173/game?session=${SID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const m = await page.evaluate(() => {
      const get = (sel) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { w: Math.round(r.width), h: Math.round(r.height), visible: r.width > 0 && r.height > 0 };
      };
      return {
        char: get('.char-card'),
        main: get('.game-main'),
        timeline: get('.timeline-archive'),
        narrative: get('.narrative-area'),
        voice: get('.voice-options'),
        input: get('.game-input'),
        header: get('.game-header'),
        charName: document.querySelector('.char-card-name')?.innerText,
        round: document.querySelector('.chapter-title, h2')?.innerText,
      };
    });

    const present = [m.char, m.main, m.timeline, m.narrative, m.voice, m.input, m.header];
    const allPresent = present.every(p => p && p.visible);
    const mainHasContent = m.main && m.main.h > 50;

    // 各 viewport 期望
    let expected;
    if (vp.w <= 767) expected = 'mobile';
    else if (vp.w <= 1023) expected = 'tablet';
    else if (vp.w < 1600) expected = 'desktop';
    else expected = 'wide';

    // 检查
    const char = m.char, main = m.main, timeline = m.timeline;
    const total = (char?.w||0) + (main?.w||0) + (timeline?.w||0);
    const mainPct = main && total > 0 ? Math.round(main.w / total * 100) : 0;

    // tablet 模式 timeline 应该 hidden
    const tlHidden = expected === 'tablet' && (!timeline || !timeline.visible);

    console.log(`\n=== ${vp.name} (${vp.w}×${vp.h}) [${expected}] ===`);
    if (m.char) console.log(`  char     : ${m.char.w}×${m.char.h}`);
    if (m.main) console.log(`  main     : ${m.main.w}×${m.main.h}  (${mainPct}%)`);
    if (m.timeline) console.log(`  timeline : ${m.timeline.w}×${m.timeline.h}  visible=${m.timeline.visible}`);
    else console.log(`  timeline : (hidden)`);
    if (m.narrative) console.log(`  narrative: ${m.narrative.w}×${m.narrative.h}`);
    if (m.voice) console.log(`  voice    : ${m.voice.w}×${m.voice.h}`);
    console.log(`  char name: ${m.charName}, round: ${m.round?.substring(0,30)}`);

    // 关键问题
    if (!mainHasContent) {
      issues.push(`[${vp.name}] main 无内容（h=${m.main?.h}）`);
    }
    if (expected === 'tablet' && !tlHidden) {
      issues.push(`[${vp.name}] tablet 应隐藏 timeline，但 visible=${timeline?.visible}`);
    }
    if (mainPct > 0 && mainPct < 50) {
      issues.push(`[${vp.name}] main 占比 ${mainPct}% 偏小（应 ≥ 60%）`);
    }
    if (m.main && m.main.h < 100) {
      issues.push(`[${vp.name}] main h=${m.main.h} 过小`);
    }

    await page.screenshot({ path: `/tmp/audit_${vp.name}.png`, fullPage: false });
    await ctx.close();
  }

  // 关键交互
  console.log('\n=== 关键交互测试 (desktop 1440) ===');
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', e => issues.push(`[desktop-interact page-error] ${e.message}`));

  await page.goto(`http://localhost:5173/game?session=${SID}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);

  // 1. 折叠 CharCard
  const charBefore = await page.$eval('.char-card', el => el.getBoundingClientRect().height);
  await page.click('.char-card-toggle');
  await page.waitForTimeout(500);
  const charAfter = await page.$eval('.char-card', el => el.getBoundingClientRect().height);
  const charToggleStillVisible = await page.evaluate(() => {
    const t = document.querySelector('.char-card-toggle');
    return t && t.getBoundingClientRect().height > 0;
  });
  console.log(`  CharCard 折叠: ${charBefore} → ${charAfter}px, toggle 仍可见: ${charToggleStillVisible}`);
  if (charAfter >= charBefore) issues.push('CharCard 折叠无效');
  if (!charToggleStillVisible) issues.push('CharCard 折叠后 toggle 不可见');

  // 2. 打开回顾 modal
  await page.click('button[aria-label="回顾"]').catch(() => {});
  await page.waitForTimeout(2000);
  const recapVisible = await page.evaluate(() => !!document.querySelector('.recap-item'));
  console.log(`  回顾 modal items: ${recapVisible}`);
  if (!recapVisible) issues.push('回顾 modal 无 item');

  // 3. voice options
  const voices = await page.$$eval('.voice-option', els => els.length);
  console.log(`  声音卡: ${voices}`);
  if (voices < 1) issues.push('声音卡为 0');

  await page.screenshot({ path: '/tmp/audit_desktop_interact.png', fullPage: false });
  await ctx.close();
  await browser.close();

  console.log('\n=== 体检结果 ===');
  if (issues.length === 0) {
    console.log('✅ 全部通过');
  } else {
    console.log(`❌ 发现 ${issues.length} 个问题：`);
    issues.forEach(i => console.log('  - ' + i));
  }
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
