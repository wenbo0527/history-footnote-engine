// 端到端：选 male → 入局 → 点击「算盘声」→ 看 narrative 更新
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();

  let apiErrors = 0;
  page.on('pageerror', e => console.log('[page-error]', e.message));
  // 监听请求
  page.on('response', resp => {
    if (resp.url().includes('/api/input') || resp.url().includes('/api/start')) {
      console.log(`[API ${resp.status()}] ${resp.url()}`);
      if (resp.status() >= 400) apiErrors++;
    }
  });

  await page.goto('http://localhost:5174/wizard', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  await page.click('.identity-card:nth-child(1)');
  await page.waitForTimeout(300);
  await page.click('button:has-text("下一步")');
  await page.waitForTimeout(300);
  await page.fill('#wizard-name', '沈半山');
  await page.click('button:has-text("下一步")');
  await page.waitForTimeout(300);
  await page.click('button.seal');
  await page.waitForTimeout(6000);

  console.log('URL:', page.url());

  // 点 "算盘声"
  console.log('\n>>> 点击「算盘声」');
  await page.click('.voice-option:has-text("算盘声")');
  // 等 LLM + narrative 真实更新（"第 1 回合"）
  await page.waitForSelector('.narrative-area :text("第 1 回合")', { timeout: 30000 }).catch(() => console.log('timeout waiting for new narrative'));
  await page.waitForTimeout(2000);

  // 看新 narrative
  const txt = await page.evaluate(() => {
    const el = document.querySelector('.narrative-area, [class*="narrative"]');
    return el?.innerText?.slice(0, 800) || '(no narrative)';
  });
  console.log('\n=== 最新 narrative 区 ===');
  console.log(txt);

  // 当前 voice options 数量
  const voiceCount = await page.$$eval('.voice-option', els => els.length);
  console.log('\nVoice options 数量:', voiceCount);

  // 是否出现 toast error
  const toasts = await page.$$('.toast, [class*="toast"]');
  console.log('Toast 数:', toasts.length);
  for (const t of toasts) {
    const text = await t.evaluate(el => el.innerText);
    console.log(' Toast:', text.slice(0, 100));
  }

  await page.screenshot({ path: '/tmp/after_voice_click.png', fullPage: true });
  console.log('\nAPI errors:', apiErrors);

  await browser.close();
})().catch(e => { console.error('FATAL:', e); process.exit(1); });
