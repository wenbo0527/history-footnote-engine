// 端到端：验证 LoadingOverlay 出现在 isLoading=true 期间
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();

  const errs = [];
  page.on('pageerror', e => errs.push(`[page-error] ${e.message}`));
  page.on('console', msg => {
    if (msg.type() === 'error') errs.push(`[console] ${msg.text().slice(0,200)}`);
  });

  await page.goto('http://localhost:5174/wizard', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

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

  // 截 LLM 加载期间的截图（点 voice 后瞬间 loading=true）
  // 用 mock API 路径模拟慢响应：先把 web 端 proxy 关掉,手动放慢
  // —— 简单做法：直接看 isLoading 时 hover overlay，截图
  console.log('\n>>> 点击「算盘声」 + 立即截图');
  await Promise.all([
    page.click('.voice-option:has-text("算盘声")'),
    page.waitForTimeout(800), // 不等响应，先截图
  ]);

  // 立即截图看 overlay
  await page.screenshot({ path: '/tmp/overlay_active.png', fullPage: true });
  const overlay = await page.evaluate(() => {
    const ov = document.querySelector('.loading-overlay');
    if (!ov) return null;
    const titleEl = ov.querySelector('.title-text');
    const progressBar = ov.querySelector('.progress-bar');
    const tipText = ov.querySelector('.tip-text');
    const tipSource = ov.querySelector('.tip-source');
    return {
      visible: true,
      title: titleEl?.textContent,
      progressWidth: progressBar?.style.width,
      tipText: tipText?.textContent,
      tipSource: tipSource?.textContent,
      ariaBusy: ov.getAttribute('aria-busy'),
    };
  });
  console.log('\n=== LoadingOverlay 内容 ===');
  console.log(JSON.stringify(overlay, null, 2));

  // 等约 5 秒看 tip 切换
  await page.waitForTimeout(5000);
  await page.screenshot({ path: '/tmp/overlay_5s.png', fullPage: true });
  const tip5s = await page.evaluate(() => {
    return document.querySelector('.tip-text')?.textContent;
  });
  console.log('5s 后 tip:', tip5s);

  // 等更多时间，tip 应该不同
  await page.waitForTimeout(5000);
  await page.screenshot({ path: '/tmp/overlay_10s.png', fullPage: true });
  const tip10s = await page.evaluate(() => {
    return document.querySelector('.tip-text')?.textContent;
  });
  console.log('10s 后 tip:', tip10s);
  console.log('相同?', tip5s === tip10s);

  // 等响应回来
  console.log('\n>>> 等待响应完成');
  await page.waitForSelector('.loading-overlay', { state: 'detached', timeout: 60000 }).catch(() => console.log('timeout - 60s'));
  await page.waitForTimeout(2000);

  console.log('\n=== Errors ===');
  errs.forEach(e => console.log(e));

  await browser.close();
})().catch(e => { console.error('FATAL:', e); process.exit(1); });
