// 端到端：访问用户 session，输入"出门寻找出路赚点银钱"，观察 toast + narrative 变化
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  page.on('console', msg => {
    if (msg.type() === 'error' || msg.type() === 'warning') {
      console.log(`[browser ${msg.type()}]`, msg.text().substring(0, 200));
    }
  });

  await page.goto('http://localhost:5173/game?session=wanli1587_20260708_163051', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);
  console.log('URL:', page.url());

  // 找 textarea + 提交
  const textarea = await page.$('textarea, [contenteditable]');
  if (!textarea) { console.log('NO TEXTAREA'); process.exit(1); }
  await textarea.fill('出门寻找出路赚点银钱');
  await page.waitForTimeout(300);
  // 提交按钮
  await page.click('button:has-text("提交"), button[type="submit"], button:has-text("送出")').catch(() => {});
  console.log('>>> 点击提交后');

  // 等 1 秒看 toast
  await page.waitForTimeout(2000);
  const toastsAt2000 = await page.evaluate(() => {
    const toasts = Array.from(document.querySelectorAll('.toast, [class*="toast"]'));
    return toasts.map(t => ({
      cls: t.className,
      text: t.innerText?.trim().substring(0, 200)
    }));
  });
  console.log('2s 后 toast:', JSON.stringify(toastsAt2000, null, 2));

  // 等更多时间看 narrative 更新
  await page.waitForTimeout(20000);
  const finalState = await page.evaluate(() => {
    const narr = document.querySelector('.narrative-area, [class*="narrative"]');
    const roundTitle = document.querySelector('.chapter-title, .title-text, h2');
    const toasts = Array.from(document.querySelectorAll('.toast, [class*="toast"]'));
    return {
      roundTitle: roundTitle?.innerText?.trim(),
      narrative: narr?.innerText?.substring(0, 500),
      toasts: toasts.map(t => t.innerText?.trim().substring(0, 200))
    };
  });
  console.log('\n=== 25s 后状态 ===');
  console.log('round 标题:', finalState.roundTitle);
  console.log('narrative:', finalState.narrative);
  console.log('toasts:', JSON.stringify(finalState.toasts, null, 2));

  await page.screenshot({ path: '/tmp/after_input_diag.png', fullPage: true });
  await browser.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
