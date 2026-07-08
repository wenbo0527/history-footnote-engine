// 重新端到端验证 RecapModal: items 16 + 搜索过滤
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', e => console.log('[page-error]', e.message));

  await page.goto('http://localhost:5173/game?session=wanli1587_20260708_163051', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);

  // 点"回顾"按钮
  await page.click('button[aria-label="回顾"]');
  await page.waitForTimeout(3000);

  // 抓 recap items
  const items = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll('.recap-item'));
    return els.length;
  });
  console.log('=== Recap items count ===', items);

  // 搜索"周大娘"
  const searchInput = await page.$('.recap-search-input');
  if (searchInput) {
    await searchInput.fill('周大娘');
    await page.waitForTimeout(500);
    const filtered = await page.evaluate(() => {
      const els = Array.from(document.querySelectorAll('.recap-item'));
      return {
        count: els.length,
        rounds: els.map(el => el.querySelector('.recap-round')?.innerText)
      };
    });
    console.log('=== 搜索 "周大娘" ===');
    console.log('过滤后数量:', filtered.count);
    console.log('回合:', filtered.rounds);
  } else {
    console.log('NO SEARCH INPUT');
  }

  // 截图（搜索后状态）
  await page.screenshot({ path: '/tmp/recap_final.png', fullPage: true });
  await browser.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
