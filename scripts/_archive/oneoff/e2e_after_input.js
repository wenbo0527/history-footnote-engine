// 端到端验证：点算盘声 → narrative 是否更新为「第 1 回合」
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();

  let apiCalls = [];
  page.on('response', resp => {
    const u = resp.url();
    if (u.includes('/api/')) {
      apiCalls.push({ url: u, status: resp.status() });
      console.log(`[API ${resp.status()}] ${u}`);
    }
  });
  page.on('pageerror', e => console.log('[page-error]', e.message));

  console.log('=== 走通 wizard ===');
  await page.goto('http://localhost:5174/wizard', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1200);
  await page.click('.identity-card:nth-child(1)');
  await page.waitForTimeout(200);
  await page.click('button:has-text("下一步")');
  await page.waitForTimeout(200);
  await page.fill('#wizard-name', '沈半山');
  await page.click('button:has-text("下一步")');
  await page.waitForTimeout(200);
  await page.click('button.seal');
  await page.waitForTimeout(6000);
  console.log('URL:', page.url());

  console.log('\n=== 点算盘声，等 90 秒直到 overlay 消失 ===');
  const t0 = Date.now();
  await page.click('.voice-option:has-text("算盘声")');

  // 等 overlay 消失
  let overlayGone = false;
  for (let i = 0; i < 18; i++) {
    await page.waitForTimeout(5000);
    const stillVisible = await page.evaluate(() => !!document.querySelector('.loading-overlay'));
    console.log(`  +${(i+1)*5}s, overlay=${stillVisible ? '仍可见' : '已消失'}, elapsed=${Math.round((Date.now()-t0)/1000)}s`);
    if (!stillVisible) { overlayGone = true; break; }
  }
  if (!overlayGone) {
    console.log('!!! 90 秒后 overlay 仍可见，强制退出');
    await page.screenshot({ path: '/tmp/after_input_timeout.png', fullPage: true });
    await browser.close();
    return;
  }

  await page.waitForTimeout(3000);

  // 检查 narrative 内容
  const narrativeState = await page.evaluate(() => {
    const narr = document.querySelector('.narrative-area, [class*="narrative"]');
    const overlay = document.querySelector('.loading-overlay');
    return {
      overlayVisible: !!overlay,
      narrativesLen: document.querySelectorAll('.narrative-block, [class*="narrative-block"]').length,
      bodyTextSnippet: document.body.innerText.substring(0, 500),
      voiceOptionsCount: document.querySelectorAll('.voice-option').length,
    };
  });

  console.log('\n=== 实测状态 ===');
  console.log('overlay 还显示?', narrativeState.overlayVisible);
  console.log('narrative-block 数量:', narrativeState.narrativesLen);
  console.log('voice-option 数量:', narrativeState.voiceOptionsCount);
  console.log('---');
  console.log(narrativeState.bodyTextSnippet.substring(0, 400));

  await page.screenshot({ path: '/tmp/after_input.png', fullPage: true });
  console.log('\nscreenshot: /tmp/after_input.png');
  console.log('API 总调用次数:', apiCalls.length);
  apiCalls.forEach((c, i) => console.log(`  ${i+1}. ${c.status} ${c.url.substring(0,80)}`));

  await browser.close();
})().catch(e => { console.error('FATAL:', e); process.exit(1); });
