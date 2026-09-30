import React, { useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, TileLayer, Circle, Marker, Polyline, Tooltip, useMap, CircleMarker } from 'react-leaflet';
import L from 'leaflet';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowUpRight, Crosshair, Layers, Route as RouteIcon, Ruler, Target } from 'lucide-react';
import { api, type Hazard, type MapWell, type NearbyResponse, type Station, type WellProfile } from '../lib/api';
import { HAZARDS, hazardOf, km, m, n } from '../lib/format';
import { useLoad, useNwis } from '../state/nwis';
import { Button, ErrorNote, HazardChip, Loading, Panel, SeverityTag, SourceLink, cx } from '../ui/primitives';

// Key-free tile services (OpenStreetMap, Esri). Labels come from a separate
// reference layer so the light and satellite bases stay readable.
const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services';
const BASEMAPS = {
  light: {
    label: 'Light',
    url: `${ESRI}/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`,
    labels: `${ESRI}/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}`,
    attr: 'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors',
    maxNativeZoom: 16,
  },
  streets: { label: 'Streets', url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', labels: null, attr: '&copy; OpenStreetMap contributors', maxNativeZoom: 19 },
  satellite: {
    label: 'Satellite',
    url: `${ESRI}/World_Imagery/MapServer/tile/{z}/{y}/{x}`,
    labels: `${ESRI}/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}`,
    attr: 'Imagery &copy; Esri, Maxar, Earthstar Geographics',
    maxNativeZoom: 18,
  },
} as const;
type Basemap = keyof typeof BASEMAPS;

const RADIUS_PRESETS = [5, 10, 25, 50];

/** Marker: ring segments = share of each hazard in the well's history. */
function wellIcon(w: MapWell, opts: { selected: boolean; hovered: boolean; dim: boolean }) {
  if (w.is_active) {
    return L.divIcon({
      className: '',
      iconSize: [44, 44],
      iconAnchor: [22, 22],
      html: `<div style="position:relative;width:44px;height:44px">
        <span style="position:absolute;inset:0;border-radius:50%;background:var(--accent);opacity:.18;animation:pulseRing 2s cubic-bezier(.2,.6,.4,1) infinite"></span>
        <span style="position:absolute;inset:9px;border-radius:50%;background:#fff;border:2.5px solid var(--accent);box-shadow:0 2px 8px rgba(14,90,105,.35)"></span>
        <svg viewBox="0 0 24 24" style="position:absolute;inset:14px;width:16px;height:16px" fill="none" stroke="var(--accent)" stroke-width="2.4" stroke-linecap="round"><path d="M12 3 7 21M12 3l5 18M9 14h6M10.2 9h3.6M5 21h14"/></svg>
      </div>`,
    });
  }
  const total = Object.values(w.events_by_type).reduce((a, b) => a + b, 0);
  const size = Math.round(Math.min(34, 18 + total * 2.4)) + (opts.selected ? 6 : 0);
  let acc = 0;
  const stops = total
    ? Object.entries(w.events_by_type)
        .map(([h, c]) => {
          const a0 = (acc / total) * 360;
          acc += c;
          const a1 = (acc / total) * 360;
          return `${hazardOf(h).color} ${a0}deg ${a1}deg`;
        })
        .join(',')
    : '#c9c5bb 0deg 360deg';
  const ring = opts.selected ? 'var(--ink)' : opts.hovered ? 'var(--accent)' : '#fff';
  return L.divIcon({
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:conic-gradient(${stops});
      box-shadow:0 0 0 2px ${ring},0 2px 6px rgba(0,0,0,.25);opacity:${opts.dim ? 0.35 : 1};transition:all .15s;
      display:flex;align-items:center;justify-content:center">
      <div style="width:${size - 10}px;height:${size - 10}px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;
        font:600 ${size > 26 ? 11 : 9}px 'IBM Plex Mono',monospace;color:#17191d">${total || ''}</div></div>`,
  });
}

/** Surface location + survey offsets -> plan-view path in lat/lon. */
function planPath(lat: number, lon: number, stations: Station[]): [number, number][] {
  const mPerDegLat = 111_320;
  const mPerDegLon = 111_320 * Math.cos((lat * Math.PI) / 180);
  return stations.map((s) => [lat + s.ns_m / mPerDegLat, lon + s.ew_m / mPerDegLon]);
}

const FitRadius: React.FC<{ center: [number, number]; radiusKm: number; nonce: number }> = ({ center, radiusKm, nonce }) => {
  const map = useMap();
  useEffect(() => {
    const b = L.latLng(center).toBounds(radiusKm * 2000 * 1.08);
    map.flyToBounds(b, { duration: 0.6, padding: [24, 24] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center[0], center[1], radiusKm, nonce]);
  return null;
};

const FlyTo: React.FC<{ target: [number, number] | null }> = ({ target }) => {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo(target, Math.max(map.getZoom(), 12), { duration: 0.6 });
  }, [target, map]);
  return null;
};

export const MapView: React.FC = () => {
  const { activeWellId, activeWell, setActiveWellId } = useNwis();
  const nav = useNavigate();
  const [radius, setRadius] = useState(25);
  const [basemap, setBasemap] = useState<Basemap>('light');
  const [hazardFilter, setHazardFilter] = useState<Set<Hazard>>(new Set());
  const [showLinks, setShowLinks] = useState(true);
  const [showPaths, setShowPaths] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [fitNonce, setFitNonce] = useState(0);
  const [flyTarget, setFlyTarget] = useState<[number, number] | null>(null);
  const [paths, setPaths] = useState<Record<string, [number, number][]>>({});
  const debounced = useDebounced(radius, 180);

  const { data, error, loading, reload } = useLoad<NearbyResponse | null>(() => (activeWellId ? api.nearby(activeWellId, debounced) : Promise.resolve(null)), [activeWellId, debounced]);
  const profile = useLoad<WellProfile | null>(() => (selected ? api.profile(selected) : Promise.resolve(null)), [selected]);

  useEffect(() => { setSelected(null); }, [activeWellId]);

  const wells = data?.wells ?? [];
  const inRadius = wells.filter((w) => w.in_radius && !w.is_active);
  const matchesFilter = (w: MapWell) => hazardFilter.size === 0 || [...hazardFilter].some((h) => (w.events_by_type[h] ?? 0) > 0);
  const visibleList = inRadius.filter(matchesFilter);
  const center: [number, number] | null = data ? [data.center.lat, data.center.lon] : null;

  // Load plan-view trajectories for the active well + wells in radius (cached).
  useEffect(() => {
    if (!data || !showPaths) return;
    const need = wells.filter((w) => (w.in_radius || w.is_active) && !paths[w.well_id]);
    need.forEach((w) =>
      api.trajectory(w.well_id).then(
        (t) => setPaths((p) => ({ ...p, [w.well_id]: planPath(w.lat, w.lon, t.stations) })),
        () => setPaths((p) => ({ ...p, [w.well_id]: [] })),
      ),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, showPaths]);

  const hazardTotals = useMemo(() => {
    const t: Record<string, number> = {};
    inRadius.forEach((w) => Object.entries(w.events_by_type).forEach(([h, c]) => (t[h] = (t[h] ?? 0) + c)));
    return t;
  }, [inRadius]);

  const toggleHazard = (h: Hazard) =>
    setHazardFilter((s) => {
      const x = new Set(s);
      x.has(h) ? x.delete(h) : x.add(h);
      return x;
    });

  const select = (w: MapWell) => {
    setSelected(w.well_id);
    setFlyTarget([w.lat, w.lon]);
  };

  return (
    <div className="h-full flex min-h-0">
      {/* Map column */}
      <div className="relative flex-1 min-w-0">
        {error && <div className="absolute z-[500] top-3 left-3 right-3"><ErrorNote message={error} onRetry={reload} className="m-0 bg-white" /></div>}
        {center && (
          <MapContainer center={center} zoom={10} className="absolute inset-0" zoomControl={false} preferCanvas={false}>
            <TileLayer key={basemap} url={BASEMAPS[basemap].url} attribution={BASEMAPS[basemap].attr} subdomains="abc" maxZoom={19} maxNativeZoom={BASEMAPS[basemap].maxNativeZoom} />
            {BASEMAPS[basemap].labels && <TileLayer key={`${basemap}-labels`} url={BASEMAPS[basemap].labels!} maxZoom={19} maxNativeZoom={BASEMAPS[basemap].maxNativeZoom} zIndex={5} />}
            <FitRadius center={center} radiusKm={debounced} nonce={fitNonce} />
            <FlyTo target={flyTarget} />
            <Circle
              center={center}
              radius={debounced * 1000}
              pathOptions={{ color: basemap === 'satellite' ? '#ffffff' : '#0e5a69', weight: basemap === 'satellite' ? 2.5 : 1.5, dashArray: '6 6', fillColor: basemap === 'satellite' ? '#ffffff' : '#0e5a69', fillOpacity: basemap === 'satellite' ? 0.1 : 0.05 }}
            />
            {/* ring labels */}
            {[0.5, 1].map((f) => (
              <CircleMarker key={f} center={[center[0] + (debounced * f) / 111.32, center[1]]} radius={0} pathOptions={{ opacity: 0 }}>
                <Tooltip permanent direction="center" className="nwis-label">{`${+(debounced * f).toFixed(1)} km`}</Tooltip>
              </CircleMarker>
            ))}

            {showLinks &&
              visibleList.map((w) => (
                <Polyline
                  key={`l-${w.well_id}`}
                  positions={[center, [w.lat, w.lon]]}
                  pathOptions={{
                    color: hovered === w.well_id || selected === w.well_id ? '#0e5a69' : '#8a8f97',
                    weight: hovered === w.well_id || selected === w.well_id ? 2 : 1,
                    dashArray: '2 5',
                    opacity: hovered === w.well_id || selected === w.well_id ? 0.95 : 0.55,
                  }}
                >
                  <Tooltip sticky className="nwis-tip">{w.well_name} · {km(w.distance_km)} from {activeWell?.well_name}</Tooltip>
                </Polyline>
              ))}

            {showPaths &&
              wells
                .filter((w) => (w.in_radius || w.is_active) && (paths[w.well_id]?.length ?? 0) > 1)
                .map((w) => (
                  <Polyline
                    key={`p-${w.well_id}`}
                    positions={paths[w.well_id]}
                    pathOptions={{ color: w.is_active ? '#0e5a69' : '#17191d', weight: w.is_active ? 3 : 2, opacity: w.is_active ? 0.9 : 0.55, lineCap: 'round' }}
                  />
                ))}

            {wells.map((w) => (
              <Marker
                key={`${w.well_id}-${selected === w.well_id}-${hovered === w.well_id}-${w.in_radius}-${matchesFilter(w)}`}
                position={[w.lat, w.lon]}
                icon={wellIcon(w, { selected: selected === w.well_id, hovered: hovered === w.well_id, dim: !w.is_active && (!w.in_radius || !matchesFilter(w)) })}
                zIndexOffset={w.is_active ? 1000 : selected === w.well_id ? 800 : 0}
                eventHandlers={{
                  click: () => (w.is_active ? setSelected(w.well_id) : select(w)),
                  mouseover: () => setHovered(w.well_id),
                  mouseout: () => setHovered(null),
                }}
              >
                <Tooltip direction="top" offset={[0, -14]} className="nwis-tip">
                  <div className="font-medium">{w.well_name}{w.is_active ? ' · active well' : ''}</div>
                  <div style={{ opacity: 0.75 }}>
                    {w.is_active ? `${w.field} · TD ${m(w.total_depth_md_m)}` : `${km(w.distance_km)} · ${w.total_events} events · ${n(w.npt_hours, 0)} h NPT`}
                  </div>
                </Tooltip>
              </Marker>
            ))}
            {/* Name labels: separate non-interactive markers (a Leaflet layer holds only one tooltip). */}
            {wells.filter((w) => w.in_radius || w.is_active).map((w) => (
              <Marker
                key={`lbl-${w.well_id}`}
                position={[w.lat, w.lon]}
                interactive={false}
                zIndexOffset={-100}
                icon={L.divIcon({ className: '', iconSize: [90, 16], iconAnchor: [45, -14], html: `<div class="nwis-maplabel${w.is_active ? ' is-active' : ''}">${w.well_name}</div>` })}
              />
            ))}
          </MapContainer>
        )}
        {loading && !data && <div className="absolute inset-0 flex items-center justify-center"><Loading label="Loading wells" /></div>}

        {/* Floating control card */}
        <div className="absolute z-[500] top-4 left-4 w-[300px] bg-surface/95 backdrop-blur border border-line rounded-xl shadow-pop">
          <div className="px-4 pt-3.5 pb-3 border-b border-line">
            <div className="flex items-baseline justify-between">
              <div className="text-2xs uppercase tracking-[0.08em] text-ink-3 flex items-center gap-1.5"><Ruler className="w-3.5 h-3.5" /> Search radius</div>
              <div className="num text-[18px] font-medium">{debounced} km</div>
            </div>
            <input
              type="range" min={1} max={60} step={1} value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
              className="w-full mt-2" aria-label="Search radius in kilometres"
            />
            <div className="flex gap-1 mt-1.5">
              {RADIUS_PRESETS.map((r) => (
                <button key={r} onClick={() => setRadius(r)}
                  className={cx('flex-1 h-6 rounded-md text-[11px] num border', radius === r ? 'bg-accent text-white border-accent' : 'border-line text-ink-2 hover:bg-sunken')}>
                  {r} km
                </button>
              ))}
            </div>
            <div className="text-xs text-ink-2 mt-2.5">
              <span className="num font-medium text-ink">{inRadius.length}</span> offset well{inRadius.length === 1 ? '' : 's'} within {debounced} km of{' '}
              <span className="font-medium text-ink">{activeWell?.well_name}</span>
            </div>
          </div>
          <div className="px-4 py-3 border-b border-line">
            <div className="text-2xs uppercase tracking-[0.08em] text-ink-3 mb-2">Show wells that had</div>
            <div className="flex flex-wrap gap-1.5">
              {(Object.keys(HAZARDS) as Hazard[]).map((h) => {
                const on = hazardFilter.has(h);
                const hz = HAZARDS[h];
                return (
                  <button key={h} onClick={() => toggleHazard(h)}
                    className="inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-full border transition-colors"
                    style={{ borderColor: on ? hz.color : 'var(--line)', background: on ? hz.soft : 'transparent', color: on ? hz.color : 'var(--ink-2)' }}>
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: hz.color }} />
                    {hz.label}
                    <span className="num opacity-70">{hazardTotals[h] ?? 0}</span>
                  </button>
                );
              })}
            </div>
            {hazardFilter.size > 0 && <button className="text-[11px] text-accent mt-2 hover:underline" onClick={() => setHazardFilter(new Set())}>Clear filter</button>}
          </div>
          <div className="px-4 py-2.5 flex items-center justify-between gap-2">
            <div className="flex gap-1">
              {(Object.keys(BASEMAPS) as Basemap[]).map((b) => (
                <button key={b} onClick={() => setBasemap(b)} className={cx('text-[11px] px-2 h-6 rounded-md', basemap === b ? 'bg-ink text-white' : 'text-ink-2 hover:bg-sunken')}>
                  {BASEMAPS[b].label}
                </button>
              ))}
            </div>
            <div className="flex gap-1">
              <IconToggle on={showLinks} onClick={() => setShowLinks((v) => !v)} label="Distance lines"><Crosshair className="w-3.5 h-3.5" /></IconToggle>
              <IconToggle on={showPaths} onClick={() => setShowPaths((v) => !v)} label="Well paths (plan view)"><RouteIcon className="w-3.5 h-3.5" /></IconToggle>
              <IconToggle on={false} onClick={() => setFitNonce((x) => x + 1)} label="Re-centre on active well"><Target className="w-3.5 h-3.5" /></IconToggle>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="absolute z-[500] bottom-4 left-4 bg-surface/95 backdrop-blur border border-line rounded-lg shadow-card px-3 py-2 text-[11px] text-ink-2 flex items-center gap-3">
          <Layers className="w-3.5 h-3.5 text-ink-3" />
          <span>Ring colours = incident mix · number = incidents · size grows with incidents</span>
        </div>
      </div>

      {/* Side panel */}
      <aside className="w-[380px] shrink-0 border-l border-line bg-paper flex flex-col min-h-0">
        {selected && selected !== activeWellId ? (
          <SelectedWell
            well={wells.find((w) => w.well_id === selected)!}
            profile={profile.data}
            loading={profile.loading}
            onBack={() => setSelected(null)}
            onMakeActive={() => setActiveWellId(selected)}
            onOpen={() => nav(`/wells/${selected}`)}
          />
        ) : (
          <>
            <div className="px-4 pt-4 pb-3 border-b border-line">
              <div className="text-2xs uppercase tracking-[0.08em] text-ink-3">Offset wells, nearest first</div>
              <div className="text-xs text-ink-3 mt-1">Hover to locate · click for its history</div>
            </div>
            <div className="flex-1 overflow-y-auto">
              {visibleList.length === 0 && !loading && (
                <div className="p-6 text-[13px] text-ink-3">No offset wells match. Widen the radius or clear the hazard filter.</div>
              )}
              {visibleList.map((w) => (
                <button
                  key={w.well_id}
                  onMouseEnter={() => setHovered(w.well_id)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => select(w)}
                  className={cx('w-full text-left px-4 py-3 border-b border-line hover:bg-surface transition-colors', hovered === w.well_id && 'bg-surface')}
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="num text-[13px] font-medium">{w.well_name}</span>
                    <span className="num text-xs text-ink-2">{km(w.distance_km)}</span>
                  </div>
                  <div className="text-xs text-ink-3 mt-0.5">{w.field} · {w.well_type} · {w.status.toLowerCase()} · TD {m(w.total_depth_md_m)}</div>
                  <HazardBar counts={w.events_by_type} />
                </button>
              ))}
            </div>
          </>
        )}
      </aside>
    </div>
  );
};

const IconToggle: React.FC<{ on: boolean; onClick: () => void; label: string; children: React.ReactNode }> = ({ on, onClick, label, children }) => (
  <button title={label} aria-label={label} aria-pressed={on} onClick={onClick}
    className={cx('w-7 h-6 rounded-md flex items-center justify-center border', on ? 'bg-accent-soft border-accent/30 text-accent' : 'border-line text-ink-2 hover:bg-sunken')}>
    {children}
  </button>
);

const HazardBar: React.FC<{ counts: Record<string, number> }> = ({ counts }) => {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  if (!total) return <div className="text-[11px] text-ink-3 mt-2">No recorded incidents</div>;
  return (
    <div className="mt-2">
      <div className="flex h-1.5 rounded-full overflow-hidden bg-sunken">
        {Object.entries(counts).map(([h, c]) => (
          <span key={h} style={{ width: `${(c / total) * 100}%`, background: hazardOf(h).color }} />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5">
        {Object.entries(counts).map(([h, c]) => (
          <span key={h} className="text-[11px] text-ink-2"><span className="num font-medium" style={{ color: hazardOf(h).color }}>{c}</span> {hazardOf(h).label.toLowerCase()}</span>
        ))}
      </div>
    </div>
  );
};

const SelectedWell: React.FC<{ well: MapWell; profile: WellProfile | null; loading: boolean; onBack: () => void; onMakeActive: () => void; onOpen: () => void }> = ({ well, profile, loading, onBack, onMakeActive, onOpen }) => (
  <div className="flex flex-col min-h-0 h-full animate-fade-up">
    <div className="px-4 pt-3 pb-3 border-b border-line">
      <button onClick={onBack} className="text-xs text-ink-3 hover:text-ink mb-2">← All offset wells</button>
      <div className="flex items-baseline justify-between">
        <h2 className="num text-[20px] font-medium">{well.well_name}</h2>
        <span className="num text-[13px] text-ink-2">{km(well.distance_km)} away</span>
      </div>
      <div className="text-xs text-ink-3 mt-0.5">{well.field} field · {well.well_type} · {well.status.toLowerCase()}</div>
      <div className="grid grid-cols-3 gap-3 mt-3">
        <MiniStat label="Total depth" value={m(well.total_depth_md_m)} />
        <MiniStat label="Incidents" value={String(well.total_events)} />
        <MiniStat label="Lost time" value={`${n(well.npt_hours, 0)} h`} />
      </div>
      <div className="flex gap-2 mt-3">
        <Button size="sm" variant="primary" onClick={onOpen} icon={<ArrowUpRight className="w-3.5 h-3.5" />}>Open well file</Button>
        <Button size="sm" onClick={onMakeActive}>Set as active well</Button>
      </div>
    </div>
    <div className="flex-1 overflow-y-auto">
      <div className="px-4 pt-3 pb-1 text-2xs uppercase tracking-[0.08em] text-ink-3">What happened in this well, by depth</div>
      {loading && <Loading label="Loading history" />}
      {profile && profile.events.length === 0 && <div className="px-4 py-3 text-[13px] text-ink-3">No incidents on record.</div>}
      <ol className="px-4 pb-4">
        {profile?.events.map((e) => (
          <li key={e.event_id} className="relative pl-5 py-2.5 border-l border-line ml-1.5">
            <span className="absolute -left-[5px] top-4 w-2.5 h-2.5 rounded-full ring-2 ring-paper" style={{ background: hazardOf(e.event_type).color }} />
            <div className="flex items-center justify-between gap-2">
              <span className="num text-[13px] font-medium">{m(e.depth_start_md_m)}</span>
              <SeverityTag severity={e.severity} />
            </div>
            <div className="flex items-center gap-2 mt-1">
              <HazardChip hazard={e.event_type} />
              <span className="text-[11px] text-ink-3 truncate">{e.formation}</span>
            </div>
            <p className="text-xs text-ink-2 mt-1.5 leading-relaxed">{e.raw_narrative}</p>
            {e.mitigation_description && (
              <p className="text-xs mt-1.5 leading-relaxed"><span className="font-medium text-ink">What they did: </span><span className="text-ink-2">{e.mitigation_description}</span></p>
            )}
            <div className="mt-1.5"><SourceLink doc={e.source_document} page={e.source_page} /></div>
          </li>
        ))}
      </ol>
      {profile && (
        <div className="px-4 pb-5">
          <Link to={`/correlation?offset=${well.well_id}`} className="text-xs text-accent font-medium hover:underline">Compare its formations with the active well →</Link>
        </div>
      )}
    </div>
  </div>
);

const MiniStat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div>
    <div className="text-[10.5px] uppercase tracking-[0.08em] text-ink-3">{label}</div>
    <div className="num text-[14px] font-medium">{value}</div>
  </div>
);

function useDebounced<T>(value: T, ms: number) {
  const [v, setV] = useState(value);
  const t = useRef<number>();
  useEffect(() => {
    window.clearTimeout(t.current);
    t.current = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(t.current);
  }, [value, ms]);
  return v;
}
