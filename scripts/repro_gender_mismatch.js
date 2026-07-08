// 检查：选 male 后，到游戏第一回合的 narrative 提到"织女"的次数
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.goto('http://localhost:5174/wizard', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  await page.click('.identity-card:nth-child(1)'); // weaving_male
  await page.waitForTimeout(200);
  await page.click('button:has-text("下一步")');
  await page.waitForTimeout(200);
  await page.fill('#wizard-name', '沈织户');
  await page.click('button:has-text("下一步")');
  await page.waitForTimeout(200);
  await page.click('button.seal');
  await page.waitForTimeout(5000);

  console.log('URL:', page.url());

  // 输入自由文本，看看 narrative 是否提到"织女"
  const voiceOptExists = await page.$$('[class*="voice"]');
  console.log('voice opts:', voiceOptExists.length);

  // Free text 输入框
  const textarea = await page.$('textarea, [contenteditable]');
  if (textarea) {
    await textarea.fill('我坐在织机前理经线');
    await page.waitForTimeout(500);
    await page.click('button:has-text("送出"), button:has-text("发送"), button[type=submit]').catch(()=>{});
    await page.waitForTimeout(8000);
  }

  // Full body dump
  const full = await page.evaluate(() => document.body.innerText);
  const matches = full.match(/(织女|织工|牙商|佃户)/g);
  console.log('全文关键字:', matches);
  if (matches) {
    const counts = {};
    matches.forEach(m => counts[m] = (counts[m] || 0) + 1);
    console.log('频次:', counts);
  }

  await page.screenshot({ path: '/tmp/after_action.png', fullPage: true });
  await browser.close();
})().catch(e => { console.error('FATAL:', e); process.exit(1); });
