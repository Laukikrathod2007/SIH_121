// Dev tool: smoke-checks that key routes render in headless Chrome and
// reports uncaught exceptions. Needs the dev server running.
//   node scripts/route-check.mjs
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const BASE = process.env.APP_URL || 'http://localhost:5173';
const ROUTES = [
  ['/app', 'Expand sidebar'],
  ['/app/command-center', 'Expand sidebar'],
  ['/film', 'THE WELL REMEMBERS'],
  // First 10 s of /story are the loading animation (its Skip button).
  ['/', 'DrillWise opening animation'],
  ['/story', 'DrillWise opening animation'],
  ['/docs', 'Docs'],
];

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'routecheck-'));
const chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=9334', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let url;
for (let i = 0; i < 60 && !url; i++) {
  try {
    url = (await (await fetch('http://127.0.0.1:9334/json')).json()).find((t) => t.type === 'page')?.webSocketDebuggerUrl;
  } catch {}
  await sleep(250);
}
const ws = new WebSocket(url);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0;
const pend = new Map();
let errs = [];
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id) pend.get(m.id)?.(m);
  else if (m.method === 'Runtime.exceptionThrown') errs.push((m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text).slice(0, 200));
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send('Runtime.enable');
await send('Page.enable');

let failed = 0;
for (const [route, expect] of ROUTES) {
  errs = [];
  await send('Page.navigate', { url: BASE + route });
  await sleep(5000);
  // Visible text plus accessible labels (the app's collapsed sidebar is icon-only).
const r = await send('Runtime.evaluate', {
  expression: `document.body.innerText + ' ' + [...document.querySelectorAll('[aria-label]')].map((e) => e.getAttribute('aria-label')).join(' ')`,
  returnByValue: true,
});
  const ok = (r.result.result.value ?? '').includes(expect);
  if (!ok || errs.length) failed++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${route}  (expects "${expect}")${errs.length ? '  exceptions: ' + errs.join(' | ') : ''}`);
}
ws.close();
chrome.kill();
process.exit(failed ? 1 : 0);
