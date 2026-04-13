#!/usr/bin/env node
/* eslint-disable no-console */

const { chromium } = require('@playwright/test');

const baseUrl = process.env.BASE_URL || 'https://dev.punkt-b.pro';
const email = process.env.WORKSPACE_EMAIL;
const password = process.env.WORKSPACE_PASSWORD;

if (!email || !password) {
  console.error('SMOKE_FAIL');
  console.error('Missing WORKSPACE_EMAIL or WORKSPACE_PASSWORD env vars.');
  process.exit(1);
}

const normalizeBaseUrl = (url) => url.replace(/\/$/, '');
const rootUrl = normalizeBaseUrl(baseUrl);

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ ignoreHTTPSErrors: true });

  await page.goto(`${rootUrl}/lk`, { waitUntil: 'domcontentloaded' });
  await page.fill('#email', email);
  await page.fill('#password', password);
  await page.click('button[type="submit"]');

  await page.waitForURL(`${rootUrl}/`, { timeout: 15000 });
  await page.waitForSelector('[aria-label="Панель рабочей области"]', { timeout: 15000 });

  await page.goto(`${rootUrl}/manager`, { waitUntil: 'domcontentloaded' });
  await page.waitForURL(`${rootUrl}/`, { timeout: 15000 });

  await page.goto(`${rootUrl}/specialist`, { waitUntil: 'domcontentloaded' });
  await page.waitForURL(`${rootUrl}/`, { timeout: 15000 });

  await page.goto(`${rootUrl}/client`, { waitUntil: 'domcontentloaded' });
  await page.waitForURL(/\/diag/, { timeout: 15000 });

  console.log('SMOKE_OK');
  await browser.close();
})().catch((err) => {
  console.error('SMOKE_FAIL');
  console.error(err?.message || err);
  process.exit(1);
});
