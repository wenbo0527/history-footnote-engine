// 端到端：选 male → 入局 → 截图看 voice options
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();

  page.on('pageerror', e => console.log('[page-error]', e.message));

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

  // 抓取 voice options 渲染
  const voices = await page.evaluate(() => {
    const items = Array.from(document.querySelectorAll('.voice-option, [class*="voice-option-item"]'));
    return items.map(item => ({
      cls: item.className,
      text: item.innerText.replace(/\s+/g, ' ').substring(0, 100)
    }));
  });
  console.log('Voice options rendered:', JSON.stringify(voices, null, 2));

  // 截整个 VoiceOptions section
  const voSection = await page.$('.voice-options');
  if (voSection) {
    await voSection.scrollIntoViewIfNeeded();
    await voSection.screenshot({ path: '/tmp/voices_section.png' });
    console.log('Voice section screenshot: /tmp/voices_section.png');
  }

  await page.screenshot({ path: '/tmp/voices_full.png', fullPage: true });
  await browser.close();
})().catch(e => { console.error('FATAL:', e); process.exit(1); });
