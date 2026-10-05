import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const envPath = fileURLToPath(new URL('../.env.local', import.meta.url));
if (existsSync(envPath)) {
  for (const line of readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const match = line.match(/^\s*(NWIS_BACKEND_URL|NWIS_API_KEY|NWIS_TELEMETRY_MD)\s*=\s*(.*)\s*$/);
    if (match && process.env[match[1]] == null) process.env[match[1]] = match[2].replace(/^(['"])(.*)\1$/, '$2');
  }
}

const base = (process.env.NWIS_BACKEND_URL || '').trim().replace(/\/$/, '');
const key = process.env.NWIS_API_KEY || '';
const depth = process.env.NWIS_TELEMETRY_MD;
if (!base) {
  console.error('Set NWIS_BACKEND_URL to the explicitly verified backend source URL. No default port will be queried.');
  process.exit(2);
}

function pathId(id) { return String(id).split('/').map(encodeURIComponent).join('/'); }
async function request(label, path, headers = {}) {
  const response = await fetch(`${base}${path}`, { headers: { Accept: 'application/json', ...headers } });
  let body = null;
  try { body = await response.json(); } catch { /* status is still useful */ }
  console.log(`${label}: HTTP ${response.status}`);
  return { status: response.status, body };
}
function sample(body, key) { return Array.isArray(body?.[key]) ? body[key][0] ?? null : null; }
function show(label, value) { console.log(`${label}: ${JSON.stringify(value)}`); }

const health = await request('HEALTH', '/api/v2/health');
if (health.status !== 200) process.exit(1);
const authRequired = health.body?.auth?.status === 'enabled';
if (authRequired && !key) {
  console.error('The backend reports auth enabled. Set server-side NWIS_API_KEY before running protected probes. The key is never printed.');
  process.exit(2);
}
const headers = authRequired ? { 'X-API-Key': key } : {};
const wells = await request('WELLS', '/api/v2/wells', headers);
const coordinates = await request('MAP WELLS', '/api/v2/map/wells', headers);
if (wells.status !== 200) process.exit(1);
show('well_count', wells.body?.total);
show('well_ids', (wells.body?.wells ?? []).map(w => w.well_id));
show('well_sample', sample(wells.body, 'wells'));
show('coordinate_sample', sample(coordinates.body, 'wells'));

const activeId = health.body?.data_store?.active_well_id;
if (!activeId) { console.error('Health did not return data_store.active_well_id.'); process.exit(1); }
show('active_well_id', activeId);
const activePath = pathId(activeId);
const [well, formations, events] = await Promise.all([
  request('ACTIVE WELL DETAIL', `/api/v2/wells/${activePath}`, headers),
  request('ACTIVE FORMATIONS', `/api/v2/formations/${activePath}`, headers),
  request('ACTIVE EVENTS', `/api/v2/events/${activePath}`, headers),
]);
show('active_well_sample', well.body?.well);
show('formation_count', formations.body?.total);
show('formation_sample', sample(formations.body, 'formation_tops'));
show('event_count', events.body?.total);
show('event_sample', sample(events.body, 'events'));

const volveId = (wells.body?.wells ?? []).find(w => w.well_id === '15/9-F-12')?.well_id;
if (volveId) {
  const [trajectory, casing] = await Promise.all([
    request('VOLVE F-12 TRAJECTORY', `/api/v2/trajectory/${pathId(volveId)}`, headers),
    request('VOLVE F-12 CASING', `/api/v2/casing/${pathId(volveId)}`, headers),
  ]);
  show('volve_trajectory', { well_id: trajectory.body?.well_id, method: trajectory.body?.method, station_count: trajectory.body?.stations?.length, sample_station: sample(trajectory.body, 'stations') });
  show('volve_casing', { total: casing.body?.total, sample_record: sample(casing.body, 'casing_records') });
} else {
  console.log('Volve trajectory/casing probes skipped: 15/9-F-12 is not in this backend dataset.');
}

if (!depth || !Number.isFinite(Number(depth)) || Number(depth) < 0) {
  console.log('Telemetry, DORS and corridors require NWIS_TELEMETRY_MD (a confirmed MD in metres); those probes were skipped.');
} else {
  const md = encodeURIComponent(String(Number(depth)));
  const [telemetry, dors, corridors] = await Promise.all([
    request('ACTIVE TELEMETRY', `/api/v2/telemetry/${activePath}?depth=${md}&window=5`, headers),
    request('ACTIVE DORS', `/api/v2/offset_rank/${activePath}?depth=${md}&radius_km=5&top_n=10`, headers),
    request('ACTIVE CORRIDORS', `/api/v2/corridors/${activePath}?depth=${md}`, headers),
  ]);
  show('telemetry_response', { depth_m: telemetry.body?.depth_m, records_returned: telemetry.body?.records_returned, sample_record: sample(telemetry.body, 'records') });
  show('dors_response', { depth_m: dors.body?.depth_m, radius_km: dors.body?.radius_km, total_ranked: dors.body?.total_ranked, sample_ranking: sample(dors.body, 'rankings') });
  show('corridors_response', { depth_m: corridors.body?.depth_m, total_corridors: corridors.body?.total_corridors, sample_corridor: sample(corridors.body, 'corridors') });
}
