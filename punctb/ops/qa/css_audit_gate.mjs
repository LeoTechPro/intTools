#!/usr/bin/env node
/*
 * Lightweight CSS audit gate for web build.
 * - No stylelint dependency: fast, deterministic checks.
 * - Hard-fail on patterns that already produced regressions (cascade leaks, duplicates).
 *
 * Invoked from web/package.json as: node ../ops/qa/css_audit_gate.mjs
 */

import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const scriptDir = path.dirname(new URL(import.meta.url).pathname);
const repoRoot = path.resolve(scriptDir, '..', '..');
const webSrcDir = path.join(repoRoot, 'web', 'src');

const hardFailures = [];
const warnings = [];

function sha256(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

async function listFilesRecursive(dir) {
  const out = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...(await listFilesRecursive(p)));
      continue;
    }
    out.push(p);
  }
  return out;
}

function rel(p) {
  return path.relative(repoRoot, p).replaceAll(path.sep, '/');
}

function countMatches(haystack, re) {
  const m = haystack.match(re);
  return m ? m.length : 0;
}

function findLineNumber(text, idx) {
  // 1-based.
  return text.slice(0, idx).split('\n').length;
}

function addHard(file, message) {
  hardFailures.push(`${file}: ${message}`);
}

function addWarn(file, message) {
  warnings.push(`${file}: ${message}`);
}

async function main() {
  const all = await listFilesRecursive(webSrcDir);
  const cssFiles = all.filter((p) => p.endsWith('.css'));

  if (cssFiles.length === 0) {
    addHard('web/src', 'не найдено ни одного .css файла (ожидали как минимум index.css)');
  }

  // 1) Exact CSS duplicates (sha256 by full content).
  const byHash = new Map();
  for (const file of cssFiles) {
    const content = await fs.readFile(file, 'utf8');
    const h = sha256(content);
    const arr = byHash.get(h) ?? [];
    arr.push(rel(file));
    byHash.set(h, arr);
  }
  for (const [h, files] of byHash.entries()) {
    if (files.length > 1) {
      addHard(files[0], `точный дубль CSS (sha256=${h}) найден: ${files.join(', ')}`);
    }
  }

  // 2) Forbid button:not([class]) outside web/src/index.css.
  const allowButtonNotClass = new Set(['web/src/index.css']);
  for (const file of cssFiles) {
    const r = rel(file);
    const content = await fs.readFile(file, 'utf8');
    if (!allowButtonNotClass.has(r) && content.includes('button:not([class])')) {
      addHard(r, 'запрещен селектор button:not([class]) вне web/src/index.css (каскадные регрессии)');
    }
  }

  // 3) workspace-status-control must not style workspace-status-pill.
  // We hard-fail any selector that targets "...workspace-status-control... button" without excluding .workspace-status-pill.
  for (const file of cssFiles) {
    const r = rel(file);
    const content = await fs.readFile(file, 'utf8');
    const re = /workspace-status-control[^,{]*\bbutton\b[^,{]*\{/g;
    let match;
    while ((match = re.exec(content))) {
      const snippet = match[0];
      if (snippet.includes('workspace-status-pill')) continue;
      if (snippet.includes(':not(.workspace-status-pill)')) continue;
      const line = findLineNumber(content, match.index);
      addHard(r, `селектор workspace-status-control/button должен исключать .workspace-status-pill (строка ~${line})`);
    }
  }

  // 4) Baseline: do not let zonal "button:not(" spread unnoticed.
  // Lowering baselines is allowed (tightening). Raising must be explicit and reviewed.
  const buttonNotBaselines = {
    'web/src/workspace/workspace.css': 2,
    'web/src/client/workspace.css': 2,
    'web/src/test/workspace.css': 2,
    'web/src/profile/styles/workspace/index.css': 2,
    'web/src/workspace/conclusion.css': 0,
    'web/src/workspace/workspace-client.css': 2,
    'web/src/test/diag/workspace.css': 2,
  };

  for (const [fileRel, maxAllowed] of Object.entries(buttonNotBaselines)) {
    const abs = path.join(repoRoot, fileRel);
    try {
      const content = await fs.readFile(abs, 'utf8');
      const count = countMatches(content, /button:not\(/g);
      if (count > maxAllowed) {
        addHard(fileRel, `слишком много button:not( : ${count} > baseline ${maxAllowed}`);
      }
      if (count > 0) {
        addWarn(fileRel, `button:not( все еще используется (${count}); предпочтительнее явные классы/контейнеры`);
      }
    } catch {
      addWarn(fileRel, 'файл не найден (baseline check пропущен)');
    }
  }

  // 5) Warn-only: distributed Google Fonts imports (perf/order).
  for (const file of cssFiles) {
    const r = rel(file);
    const content = await fs.readFile(file, 'utf8');
    if (r !== 'web/src/fonts.css' && content.includes('fonts.googleapis.com')) {
      addWarn(r, 'найден @import/ссылка на fonts.googleapis.com; предпочтительно использовать web/src/fonts.css');
    }
  }

  // 6) Warn-only: huge css files (high regression risk).
  for (const file of cssFiles) {
    const r = rel(file);
    const content = await fs.readFile(file, 'utf8');
    const lines = content.split('\n').length;
    if (lines >= 10_000) {
      addWarn(r, `очень большой CSS файл (${lines} строк): высокий риск регрессий/копипасты`);
    }
  }

  // 7) Hard-fail: header-shared should only be used on <header> (prevent cascade leaks).
  // We scan TSX/JSX sources for <div|section|main|article|nav|aside className="... header-shared ...">
  const tsxFiles = all.filter((p) => p.endsWith('.tsx') || p.endsWith('.ts') || p.endsWith('.jsx') || p.endsWith('.js'));
  const tagRe = /<(div|section|main|article|nav|aside)[^>]*\bclass(Name)?=(["'{])[^"'}]*\bheader-shared\b/gi;
  for (const file of tsxFiles) {
    const r = rel(file);
    const content = await fs.readFile(file, 'utf8');
    let m;
    while ((m = tagRe.exec(content))) {
      const line = findLineNumber(content, m.index);
      addHard(r, `класс header-shared должен быть только на <header> (строка ~${line})`);
    }
  }

  if (warnings.length) {
    // eslint-disable-next-line no-console
    console.warn('[css:gate] WARNINGS:\n' + warnings.map((w) => `- ${w}`).join('\n'));
  }

  if (hardFailures.length) {
    // eslint-disable-next-line no-console
    console.error('[css:gate] FAILED:\n' + hardFailures.map((e) => `- ${e}`).join('\n'));
    process.exitCode = 1;
    return;
  }

  // eslint-disable-next-line no-console
  console.log(`[css:gate] OK (${cssFiles.length} css files)`);
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error('[css:gate] ERROR:', err);
  process.exitCode = 1;
});
