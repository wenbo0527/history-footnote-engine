// 端到端：访问 user session，看 voice_options 区域无「自由输入」
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', e => console.log('[page-error]', e.message));

  await page.goto('http://localhost:5173/game?session=wanli1587_20260708_163051', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);
  console.log('URL:', page.url());

  // 抓 voice options 区域
  const voices = await page.evaluate(() => {
    const items = Array.from(document.querySelectorAll('.voice-option, [class*="voice-option-item"]'));
    return items.map(item => ({
      text: item.innerText?.trim().replace(/\s+/g,' ').substring(0, 100)
    }));
  });
  console.log('\n=== voice cards 数量 ===', voices.length);
  voices.forEach((v,i) => console.log(`  [${i}] ${v.text}`));

  // 找空态文案（不该有"自由输入"）
  const freetextCards = voices.filter(v => v.text.includes('自由输入') || v.text.includes('freetext'));
  console.log('包含「自由输入」的卡:', freetextCards.length);

  // 看 round
  const round = await page.$eval('.chapter-title, h2', el => el.innerText).catch(() => '?');
  console.log('round 标题:', round);

  // 截图
  await page.screenshot({ path: '/tmp/voice_no_freetext.png', fullPage: true });
  console.log('screenshot: /tmp/voice_no_freetext.png');

  await browser.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
