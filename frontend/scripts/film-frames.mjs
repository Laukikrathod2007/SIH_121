// Dev tool: renders key frames of the film to PNGs with headless Chrome,
// for checking shots without watching the whole film.
//   node scripts/film-frames.mjs 12 30 52 70 88 100
// Needs the dev server running (npm run dev). Output: film-frames/*.png
//
// Drives one Chrome instance over the DevTools protocol (Node 22's global
// WebSocket, no extra dependency). For each time it opens /film?t=<t>,
// waits until the shot's scene has rendered (FilmCanvas sets
// data-film-rendered once its Suspense boundary resolves), then captures.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
// FILM_URL=http://localhost:5173/story to capture the story page instead.
const BASE = process.env.FILM_URL || 'http://localhost:5173/film';
const IS_STORY = BASE.includes('/story');
const PORT = 9333;
const out = path.resolve('film-frames');
fs.mkdirSync(out, { recursive: true });
const times = process.argv.slice(2).map(Number);

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'filmchrome-'));
const chrome = spawn(CHROME, [
  '--headless=new',
  '--use-angle=swiftshader',
  '--enable-unsafe-swiftshader',
  '--hide-scrollbars',
  '--window-size=1600,900',
  `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profile}`,
  'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function target() {
  for (let i = 0; i < 60; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(250);
  }
  throw new Error('Chrome did not start');
}

const ws = new WebSocket(await target());
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0;
const pending = new Map();
const logs = [];
ws.addEventListener('message', (e) => {
  const msg = JSON.parse(e.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  } else if (msg.method === 'Runtime.exceptionThrown') {
    logs.push('EXCEPTION ' + (msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text));
  } else if (msg.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(msg.params.type)) {
    const text = msg.params.args.map((a) => a.value ?? a.description ?? '').join(' ');
    if (!text.includes('React Router Future Flag')) logs.push(msg.params.type.toUpperCase() + ' ' + text.slice(0, 300));
  }
});
const send = (method, params = {}) =>
  new Promise((resolve) => {
    const i = ++id;
    pending.set(i, resolve);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
const evaluate = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result?.result?.value;

await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 900, deviceScaleFactor: 1, mobile: false });

for (const t of times) {
  logs.length = 0;
  await send('Page.navigate', { url: `${BASE}?t=${t}` });
  let rendered = null;
  for (let i = 0; i < 240 && !rendered; i++) {
    await sleep(250);
    rendered = await evaluate(IS_STORY ? "document.documentElement.dataset.storyRendered ? 'story' : null" : 'document.documentElement.dataset.filmRendered || null');
  }
  // Let textures, the terrain build and the camera smoothing settle.
  await sleep(rendered ? (IS_STORY ? 4000 : 1500) : 0);
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  const file = path.join(out, `t${String(t).padStart(5, '0')}.png`);
  fs.writeFileSync(file, Buffer.from(shot.result.data, 'base64'));
  console.log(`${rendered ? 'ok  ' : 'NOT RENDERED'} ${path.basename(file)} ${rendered ?? ''}`);
  for (const l of logs.slice(0, 6)) console.log('   ', l);
}

ws.close();
chrome.kill();
