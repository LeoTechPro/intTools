// spawn_agent_id: none
// spawn_agent_utc: n/a
// parent_session_id: n/a
// beads_id: shared-access-audit
const { chromium } = require('playwright');

const TARGET_URL = 'https://punctb.pro';
const ACCOUNT = {
  email: process.env.WORKSPACE_EMAIL || 'user.example@punctb.test',
  password: process.env.WORKSPACE_PASSWORD || '<SECRET>',
};

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto(`${TARGET_URL}/lk`, { waitUntil: 'domcontentloaded' });
  await page.fill('#email', ACCOUNT.email);
  await page.fill('#password', ACCOUNT.password);
  await page.click('button[type="submit"]');
  await delay(2000);

  await page.goto(`${TARGET_URL}/leads`, { waitUntil: 'domcontentloaded' });
  await delay(1000);

  const current = page.url();
  const fs = require('fs');
  fs.writeFileSync('/int/assess/AGENTS/tmp/playwright-leads-redirect.json', JSON.stringify({ url: current }, null, 2));
  console.log(JSON.stringify({ url: current }, null, 2));

  await context.close();
  await browser.close();
})();
