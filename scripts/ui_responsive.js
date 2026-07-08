// 4 套 viewport 截图 + 测量比例
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const SID = 'wanli1587_20260708_163051';

  const viewports = [
    { name: 'mobile-375', w: 375, h: 812, expect: 'mobile' },
    { name: 'mobile-414', w: 414, h: 896, expect: 'mobile' },
    { name: 'tablet-768', w: 768, h: 1024, expect: 'tablet' },
    { name: 'tablet-1023', w: 1023, h: 768, expect: 'tablet' },
    { name: 'desktop-1280', w: 1280, h: 800, expect: 'desktop' },
    { name: 'desktop-1440', w: 1440, h: 900, expect: 'desktop' },
    { name: 'wide-1920', w: 1920, h: 1080, expect: 'wide' },
  ];

  for (const vp of viewports) {
    const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h } });
    const page = await ctx.newPage();
    page.on('pageerror', e => console.log(`[${vp.name} page-error]`, e.message));

    await page.goto(`http://localhost:5173/game?session=${SID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4500);

    const layout = await page.evaluate(() => {
      const get = (sel) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { w: Math.round(r.width), h: Math.round(r.height) };
      };
      const char = get('.char-card');
      const main = get('.game-main');
      const timeline = get('.timeline-archive');
      const tlVisible = timeline && timeline.w > 0;
      const timelineExpanded = document.querySelector('.timeline-archive-expanded') !== null;
      return { char, main, timeline, tlVisible, timelineExpanded };
    });

    console.log(`\n=== ${vp.name} (${vp.w}×${vp.h}) [${vp.expect}] ===`);
    console.log(`  char-card:  ${JSON.stringify(layout.char)}`);
    console.log(`  game-main:  ${JSON.stringify(layout.main)}`);
    console.log(`  timeline:   ${JSON.stringify(layout.timeline)}  visible=${layout.tlVisible}  expanded=${layout.timelineExpanded}`);

    await page.screenshot({ path: `/tmp/responsive_${vp.name}.png`, fullPage: false });
    console.log(`  screenshot: /tmp/responsive_${vp.name}.png`);

    await ctx.close();
  }
  await browser.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
