// Dev tool: opens /story?t=<t> headless and prints what the 3D scene
// actually contains: camera position/target, fog, visible meshes near the
// camera, and any exceptions. Needs window.__story (set in dev builds).
//   node scripts/scene-probe.mjs 8
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const t = process.argv[2] ?? '8';
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-'));
const chrome = spawn(CHROME, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--window-size=1600,900', '--remote-debugging-port=9336', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let url;
for (let i = 0; i < 60 && !url; i++) {
  try {
    url = (await (await fetch('http://127.0.0.1:9336/json')).json()).find((x) => x.type === 'page')?.webSocketDebuggerUrl;
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
  else if (m.method === 'Runtime.exceptionThrown') errs.push((m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text).slice(0, 300));
  else if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errs.push('console.error ' + m.params.args.map((a) => a.value ?? a.description).join(' ').slice(0, 300));
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send('Runtime.enable');
await send('Page.enable');
await send('Page.navigate', { url: `http://localhost:5173/story?t=${t}` });
for (let i = 0; i < 160; i++) {
  await sleep(250);
  const r = await send('Runtime.evaluate', { expression: 'document.documentElement.dataset.storyRendered||""', returnByValue: true });
  if (r.result.result.value) break;
}
await sleep(3000);
const r = await send('Runtime.evaluate', {
  returnByValue: true,
  expression: `(() => {
    const s = window.__story; if (!s) return 'no __story';
    const { camera, scene } = s.get();
    const c = camera.position, st = s.state.current;
    const out = { cam: [c.x, c.y, c.z].map(v => +v.toFixed(3)), fov: +camera.fov.toFixed(1), near: camera.near, far: camera.far,
      stateCam: [st.camPos.x, st.camPos.y, st.camPos.z].map(v => +v.toFixed(3)), world: st.world, cut: st.cutaway, dip: st.dip,
      fog: scene.fog ? { d: scene.fog.density, c: '#' + scene.fog.color.getHexString() } : null, bg: scene.background ? (scene.background.isColor ? '#' + scene.background.getHexString() : 'tex') : null };
    let meshes = 0, vis = 0; const big = [];
    scene.traverseVisible(o => { if (o.isMesh) { vis++; const d = o.getWorldPosition(new o.position.constructor()).distanceTo(c); if (d < 0.5) big.push((o.name || o.geometry?.type) + '@' + d.toFixed(3)); } });
    scene.traverse(o => { if (o.isMesh) meshes++; });
    out.meshes = meshes; out.visible = vis; out.near = big.slice(0, 12);
    // What the centre of the view hits, and every light's on-screen intensity.
    const R = new (camera.position.constructor === Object ? Object : window.__story.THREE.Raycaster)();
    R.setFromCamera({ x: 0, y: 0 }, camera);
    out.hit = R.intersectObjects(scene.children, true).slice(0, 5).map(h => (h.object.material?.type || '') + ' ' + (h.object.geometry?.type || '') + ' d=' + h.distance.toFixed(4) + ' col=' + (h.object.material?.color ? '#' + h.object.material.color.getHexString() : '-') + ' emis=' + (h.object.material?.emissive ? '#' + h.object.material.emissive.getHexString() : '-'));
    const lights = []; scene.traverseVisible(o => { if (o.isLight && o.intensity > 0) lights.push(o.type + ' i=' + o.intensity.toFixed(4) + ' d=' + o.getWorldPosition(new window.__story.THREE.Vector3()).distanceTo(c).toFixed(4) + (o.distance ? ' range=' + o.distance : '')); });
    out.lights = lights.slice(0, 14);
    out.exposure = window.__story.get().gl.toneMappingExposure;
    return out;
  })()`,
});
console.log(JSON.stringify(r.result.result.value, null, 1));
console.log('errors:', errs.length ? errs.slice(0, 6) : 'none');
ws.close();
chrome.kill();
