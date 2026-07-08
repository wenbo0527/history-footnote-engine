// 模拟用户操作：选织工（weaving_male）后截每个步骤的图，确认是否有 bug
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  // 收集 console log 与请求错误
  page.on('console', msg => console.log(`[browser ${msg.type()}]`, msg.text()));
  page.on('pageerror', e => console.log('[page-error]', e.message));
  page.on('requestfailed', req => console.log(`[req-failed] ${req.url()} -> ${req.failure()?.errorText}`));

  await page.goto('http://localhost:5174/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  // 截图 0：进入游戏首页
  await page.screenshot({ path: '/tmp/hefu_00_home.png', fullPage: true });

  // 进入登录/创建页
  const enterBtn = await page.$('a:has-text("开始"), button:has-text("开始"), [class*="start"]');
  if (enterBtn) {
    await enterBtn.click();
    await page.waitForTimeout(1500);
  }
  await page.screenshot({ path: '/tmp/hefu_01_after_start.png', fullPage: true });

  // 如果是 /login 则直接 guest
  const guestBtn = await page.$('button:has-text("访客"), a:has-text("访客")');
  if (guestBtn) {
    await guestBtn.click();
    await page.waitForTimeout(1500);
  }

  // 进入 /wizard
  await page.goto('http://localhost:5174/wizard', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: '/tmp/hefu_02_wizard_init.png', fullPage: true });

  // 选 [0] 卡（织工）
  console.log('\n--- click weaving_male ---');
  await page.click('.identity-card:nth-child(1)');
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/hefu_03_after_click_male.png', fullPage: true });

  // 看 identity state
  const stateAfterClick = await page.evaluate(() => {
    const w = window;
    return {
      cards: Array.from(document.querySelectorAll('.identity-card')).map(c => ({
        sel: c.classList.contains('identity-card-selected'),
        text: c.innerText.replace(/\s+/g, ' ')
      })),
    };
  });
  console.log('点击后卡片：', JSON.stringify(stateAfterClick, null, 2));

  await browser.close();
})().catch(e => { console.error('FATAL:', e); process.exit(1); });
