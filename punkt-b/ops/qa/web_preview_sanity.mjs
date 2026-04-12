#!/usr/bin/env node
/**
 * Smoke-check runtime errors that TypeScript/build won't catch.
 *
 * Usage:
 *   node ops/qa/web_preview_sanity.mjs /conclusions/<id> [/other/path...]
 *
 * Exits non-zero if any page emits console.error or pageerror.
 */

import { spawn } from 'node:child_process';
import process from 'node:process';

const HOST = '127.0.0.1';
const PORT = Number(process.env.PB_PREVIEW_PORT ?? '4173');
const BASE_URL = `http://${HOST}:${PORT}`;
const PATHS = process.argv.slice(2).filter(Boolean);

if (PATHS.length === 0) {
  // eslint-disable-next-line no-console
  console.error('Usage: node ops/qa/web_preview_sanity.mjs /path [/path...]');
  process.exit(2);
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const waitForServer = async (timeoutMs = 15000) => {
  const startedAt = Date.now();
  // Node 18+ has fetch globally in this project.
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const res = await fetch(`${BASE_URL}/`, { redirect: 'manual' });
      if (res && (res.status === 200 || res.status === 304 || res.status === 404)) {
        return;
      }
    } catch {
      // ignore
    }
    await sleep(250);
  }
  throw new Error(`Preview server did not start on ${BASE_URL} within ${timeoutMs}ms`);
};

const startPreview = () => {
  const child = spawn(
    'node',
    ['node_modules/vite/bin/vite.js', 'preview', '--host', HOST, '--port', String(PORT)],
    // Start vite directly to avoid orphaned npm child processes.
    { stdio: 'inherit', env: process.env, cwd: 'web' }
  );
  return child;
};

const stopPreview = (child) =>
  new Promise((resolve) => {
    if (!child || child.killed) {
      resolve();
      return;
    }
    child.once('exit', () => resolve());
    child.kill('SIGTERM');
    setTimeout(() => {
      if (!child.killed) child.kill('SIGKILL');
      resolve();
    }, 2000).unref();
  });

const main = async () => {
  const preview = startPreview();
  try {
    await waitForServer();
    const { chromium } = await import('playwright');
    const browser = await chromium.launch();
    try {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', (e) => errors.push(`pageerror: ${String(e)}`));
      page.on('console', (msg) => {
        if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
      });

      for (const p of PATHS) {
        const url = p.startsWith('http://') || p.startsWith('https://') ? p : `${BASE_URL}${p.startsWith('/') ? '' : '/'}${p}`;
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(1500);
      }

      if (errors.length) {
        // eslint-disable-next-line no-console
        console.error(errors.join('\n---\n'));
        process.exitCode = 1;
      }
    } finally {
      await browser.close();
    }
  } finally {
    await stopPreview(preview);
  }
};

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(err?.stack || String(err));
  process.exit(1);
});
