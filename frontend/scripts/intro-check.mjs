// Dev tool: checks the /story intro flow in headless Chrome:
//   video present and playing → Skip → choice screen → "Watch without
//   sound" → story playing. Reports exceptions. Needs the dev server.
//   node scripts/intro-check.mjs
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'intro-'));
const chrome = spawn(CHROME, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required', '--window-size=1600,900', '--remote-debugging-port=9337', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let url;
for (let i = 0; i < 60 && !url; i++) {
  try {
    url = (await (await fetch('http://127.0.0.1:9337/json')).json()).find((x) => x.type === 'page')?.webSocketDebuggerUrl;
  } catch {}
  await sleep(250);
}
const ws = new WebSocket(url);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0;
const pend = new Map();
const errs = [];
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id) pend.get(m.id)?.(m);
  else if (m.method === 'Runtime.exceptionThrown') errs.push((m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text).slice(0, 200));
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
await send('Runtime.enable');
await send('Page.enable');
await send('Page.navigate', { url: (process.env.APP_URL || 'http://localhost:5173') + '/story' });
// The page shares the CPU with software WebGL loading the basin, so give
// the video a moment to decode its first frames.
for (let i = 0; i < 20; i++) {
  await sleep(500);
  if (await ev(`(document.querySelector('.intro-video')?.currentTime || 0) > 0.2`)) break;
}

const step = (name, ok, extra = '') => console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}${extra ? '  ' + extra : ''}`);

const v = await ev(`(() => { const v = document.querySelector('.intro-video'); return v ? { t: +v.currentTime.toFixed(2), paused: v.paused, dur: v.duration, ready: v.readyState, w: v.videoWidth } : null })()`);
step('loading video shown', !!v, JSON.stringify(v));
step('video playing', !!v && !v.paused && v.t > 0);
await ev(`document.querySelector('.intro-skip')?.click()`);
// Poll: under software WebGL the page's timers can run seconds late.
let choice = '';
for (let i = 0; i < 40 && !choice.includes('BEFORE THE BIT'); i++) {
  await sleep(500);
  choice = await ev(`document.querySelector('.intro-title')?.textContent || ''`);
}
step('choice screen after skip', choice.includes('BEFORE THE BIT'), JSON.stringify(choice));
// wait for the 3D world to be ready (buttons enable)
let enabled = false;
for (let i = 0; i < 80 && !enabled; i++) {
  await sleep(500);
  enabled = await ev(`(() => { const b = document.querySelector('.intro-secondary'); return !!b && !b.disabled })()`);
}
step('buttons enabled once the world has loaded', enabled);
await ev(`document.querySelector('.intro-secondary')?.click()`);
for (let i = 0; i < 40; i++) {
  await sleep(500);
  if (await ev(`!document.querySelector('.intro') && document.querySelector('.story-transport .story-btn')?.getAttribute('aria-label') === 'Pause'`)) break;
}
// The story clock advances at most 0.1 s per rendered frame, and software
// WebGL renders well under 1 fps here, so check the play state itself.
const after = await ev(`({ intro: !!document.querySelector('.intro'), title: document.querySelector('.story-title')?.textContent, playBtn: document.querySelector('.story-transport .story-btn')?.getAttribute('aria-label') })`);
step('story playing after "Watch without sound"', !after.intro && after.playBtn === 'Pause', JSON.stringify(after));
console.log('exceptions:', errs.length ? errs.slice(0, 5) : 'none');
ws.close();
chrome.kill();
