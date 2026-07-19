// 验证：访问页面后，console 不再有 fonts.gstatic.com 报错
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  let fontErrors = 0;
  let otherErrors = 0;

  page.on('console', msg => {
    if (msg.type() === 'error') {
      const t = msg.text();
      if (t.includes('fonts.gstatic.com') || t.includes('fonts.googleapis.com')) {
        fontErrors++;
        console.log('[FONT-ERROR]', t.substring(0, 100));
      } else {
        otherErrors++;
        console.log('[OTHER-ERROR]', t.substring(0, 100));
      }
    }
  });
  page.on('requestfailed', req => {
    const url = req.url();
    if (url.includes('fonts.gstatic.com') || url.includes('fonts.googleapis.com')) {
      fontErrors++;
      console.log('[REQ-FAIL-FONT]', url.substring(0, 100));
    } else {
      console.log('[REQ-FAIL-OTHER]', url.substring(0, 100));
    }
  });

  for (const path of ['/', '/login', '/wizard', '/game']) {
    await page.goto('http://localhost:5174' + path, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    console.log(`Visited ${path} - font errors so far: ${fontErrors}`);
  }

  console.log('\n=== 最终结果 ===');
  console.log('fonts.gstatic.com errors:', fontErrors);
  console.log('other errors:', otherErrors);

  await browser.close();
  if (fontErrors === 0) console.log('\n✅ 修复成功：0 条 Google Fonts 报错');
  else console.log('\n❌ 还有', fontErrors, '条 Google Fonts 报错');
})().catch(e => { console.error('FATAL:', e); process.exit(1); });
