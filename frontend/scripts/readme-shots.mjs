// Captures the screenshots used in the root README (docs/readme/*.jpg).
//   node scripts/readme-shots.mjs            (dev server on :5173)
// Story frames use the dev-only /story?t=<s> jump; app pages are captured
// after their data loads. Output is written as JPEG for a small repo.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const BASE = process.env.APP_URL || 'http://localhost:5173';
const OUT = path.resolve('../docs/readme');
fs.mkdirSync(OUT, { recursive: true });

const SHOTS = [
  // [file, path, wait-for (JS expression), extra settle ms]
  ['story-earth', '/story?t=3.6', 'document.documentElement.dataset.storyRendered', 9000],
  ['story-rig', '/story?t=12.6', 'document.documentElement.dataset.storyRendered', 9000],
  ['story-reports', '/story?t=22', 'document.documentElement.dataset.storyRendered', 9000],
  ['story-ranking', '/story?t=42', 'document.documentElement.dataset.storyRendered', 9000],
  ['story-correlate', '/story?t=50', 'document.documentElement.dataset.storyRendered', 9000],
  ['story-bit', '/story?t=63', 'document.documentElement.dataset.storyRendered', 10000],
  ['story-decide', '/story?t=71', 'document.documentElement.dataset.storyRendered', 9000],
  ['app-command-center', '/app/command-center', "document.body.innerText.includes('NHK')", 7000],
  ['app-offset-map', '/app/offset-map', "document.querySelector('.leaflet-container')", 7000],
  ['app-wells', '/app/wells', "document.body.innerText.includes('NHK')", 5000],
  ['app-correlation', '/app/correlation', "document.body.innerText.includes('Kopili') || document.body.innerText.includes('KOPILI')", 6000],
  ['app-docs', '/docs', "document.body.innerText.length > 400", 3000],
];

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'readme-'));
const chrome = spawn(CHROME, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--hide-scrollbars', '--window-size=1600,900', '--remote-debugging-port=9341', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let url;
for (let i = 0; i < 60 && !url; i++) {
  try {
    url = (await (await fetch('http://127.0.0.1:9341/json')).json()).find((x) => x.type === 'page')?.webSocketDebuggerUrl;
  } catch {}
  await sleep(250);
}
const ws = new WebSocket(url);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0;
const pend = new Map();
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id) pend.get(m.id)?.(m);
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result?.result?.value;
await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 900, deviceScaleFactor: 1, mobile: false });
// Dark theme for the app (the product default).
await send('Page.addScriptToEvaluateOnNewDocument', { source: "try{localStorage.setItem('drillwise-theme','dark')}catch(e){}" });

for (const [name, p, waitFor, settle] of SHOTS) {
  await send('Page.navigate', { url: BASE + p });
  let ok = false;
  for (let i = 0; i < 240 && !ok; i++) {
    await sleep(250);
    ok = !!(await ev(`!!(${waitFor})`));
  }
  await sleep(settle);
  const shot = await send('Page.captureScreenshot', { format: 'jpeg', quality: 86 });
  fs.writeFileSync(path.join(OUT, name + '.jpg'), Buffer.from(shot.result.data, 'base64'));
  console.log(`${ok ? 'ok  ' : 'WAIT'} ${name}`);
}
ws.close();
chrome.kill();
process.exit(0);
