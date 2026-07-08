// 端到端验证：CharCard 折叠后 toggle 仍可见
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', e => console.log('[page-error]', e.message));

  await page.goto('http://localhost:5173/game?session=wanli1587_20260708_163051', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);

  // 初始状态：toggle 可见，body 可见
  const initial = await page.evaluate(() => {
    const toggle = document.querySelector('.char-card-toggle');
    const body = document.querySelector('.char-card-body');
    const toggleStyle = toggle ? getComputedStyle(toggle) : null;
    const bodyStyle = body ? getComputedStyle(body) : null;
    return {
      toggleExists: !!toggle,
      toggleDisplay: toggleStyle?.display,
      bodyDisplay: bodyStyle?.display,
      expanded: toggle?.getAttribute('aria-expanded'),
    };
  });
  console.log('=== 初始（展开态） ===');
  console.log(JSON.stringify(initial, null, 2));

  // 点 toggle 折叠
  await page.click('.char-card-toggle');
  await page.waitForTimeout(500);

  const collapsed = await page.evaluate(() => {
    const toggle = document.querySelector('.char-card-toggle');
    const body = document.querySelector('.char-card-body');
    const card = document.querySelector('.char-card');
    const toggleStyle = toggle ? getComputedStyle(toggle) : null;
    const bodyStyle = body ? getComputedStyle(body) : null;
    return {
      toggleExists: !!toggle,
      toggleDisplay: toggleStyle?.display,
      toggleVisible: toggle?.getBoundingClientRect().height > 0,
      bodyDisplay: bodyStyle?.display,
      cardClass: card?.className,
      expanded: toggle?.getAttribute('aria-expanded'),
      toggleText: toggle?.innerText?.trim(),
    };
  });
  console.log('\n=== 点击折叠后 ===');
  console.log(JSON.stringify(collapsed, null, 2));

  // 截图折叠态
  await page.screenshot({ path: '/tmp/charcard_collapsed.png', fullPage: true });
  console.log('screenshot: /tmp/charcard_collapsed.png');

  // 再点 toggle 展开
  console.log('\n>>> 再点 toggle 展开');
  await page.click('.char-card-toggle');
  await page.waitForTimeout(500);

  const expandedAgain = await page.evaluate(() => {
    const toggle = document.querySelector('.char-card-toggle');
    const body = document.querySelector('.char-card-body');
    return {
      toggleDisplay: getComputedStyle(toggle).display,
      bodyDisplay: getComputedStyle(body).display,
      expanded: toggle?.getAttribute('aria-expanded'),
    };
  });
  console.log(JSON.stringify(expandedAgain, null, 2));

  await browser.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
