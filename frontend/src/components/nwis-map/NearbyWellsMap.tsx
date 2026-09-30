/**
 * NearbyWellsMap — standalone interactive map: user-defined radius search
 * around an active well, with offset wells colour-ringed by incident type.
 *
 * Extracted from the NWIS project (PS 26121) as a self-contained component.
 * No app router, no global state, no backend required — it works with the
 * bundled wells-data.json out of the box. Swap `wells` prop for your own
 * data (same shape) to point it at a real dataset.
 *
 * Requires: react, leaflet, react-leaflet, lucide-react (icons only —
 * remove the two icon imports and their usage if you don't want the dep).
 *
 * Usage:
 *   import { NearbyWellsMap } from './NearbyWellsMap';
 *   import wells from './wells-data.json';
 *   <NearbyWellsMap wells={wells} activeWellId="WELL-HGJ-012" />
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, TileLayer, Circle, Marker, Polyline, Tooltip, useMap, CircleMarker } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Crosshair, Layers, Ruler, Target } from 'lucide-react';

// ---------------------------------------------------------------------------
// Types — this is the only shape the component needs. Map your own data to
// this (or just use wells-data.json, which is already in this shape).
// ---------------------------------------------------------------------------

export interface WellPoint {
  well_id: string;
  well_name: string;
  field: string;
  lat: number;
  lon: number;
  status: string;
  well_type: string;
  total_depth_md_m: number;
  total_events: number;
  npt_hours: number;
  /** e.g. { MUD_LOSS: 2, STUCK_PIPE: 1 } — any string keys work */
  events_by_type: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Colours — swap this palette for your own hazard taxonomy
// ---------------------------------------------------------------------------

const HAZARD_COLORS: Record<string, { color: string; soft: string; label: string }> = {
  MUD_LOSS: { color: '#2c64c9', soft: '#e6edf9', label: 'Mud loss' },
  STUCK_PIPE: { color: '#6f47c2', soft: '#eee9f8', label: 'Stuck pipe' },
  KICK: { color: '#b62f5e', soft: '#f7e6ec', label: 'Kick / overpressure' },
  WELLBORE_INSTABILITY: { color: '#a8740a', soft: '#f6eedb', label: 'Wellbore instability' },
  TORQUE_SPIKE: { color: '#1c7f75', soft: '#e1f0ee', label: 'Torque spike' },
  CEMENTING_FAILURE: { color: '#5b6471', soft: '#eceef1', label: 'Cementing issue' },
};
const colorOf = (h: string) => HAZARD_COLORS[h] ?? { color: '#5b6471', soft: '#eceef1', label: h.replace(/_/g, ' ').toLowerCase() };

const BASEMAPS = {
  light: { label: 'Light', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', attr: 'Tiles &copy; Esri' },
  streets: { label: 'Streets', url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attr: '&copy; OpenStreetMap contributors' },
  satellite: { label: 'Satellite', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr: 'Imagery &copy; Esri, Maxar' },
} as const;
type Basemap = keyof typeof BASEMAPS;

const RADIUS_PRESETS = [5, 10, 25, 50];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function wellIcon(w: WellPoint, opts: { isActive: boolean; selected: boolean; hovered: boolean; dim: boolean }) {
  if (opts.isActive) {
    return L.divIcon({
      className: '', iconSize: [44, 44], iconAnchor: [22, 22],
      html: `<div style="position:relative;width:44px;height:44px">
        <span style="position:absolute;inset:0;border-radius:50%;background:#0e5a69;opacity:.18;animation:nwisPulse 2s cubic-bezier(.2,.6,.4,1) infinite"></span>
        <span style="position:absolute;inset:9px;border-radius:50%;background:#fff;border:2.5px solid #0e5a69;box-shadow:0 2px 8px rgba(14,90,105,.35)"></span>
        <svg viewBox="0 0 24 24" style="position:absolute;inset:14px;width:16px;height:16px" fill="none" stroke="#0e5a69" stroke-width="2.4" stroke-linecap="round"><path d="M12 3v18M7 21h10M9 9l3-6 3 6"/></svg>
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
          return `${colorOf(h).color} ${a0}deg ${(acc / total) * 360}deg`;
        })
        .join(',')
    : '#c9c5bb 0deg 360deg';
  const ring = opts.selected ? '#17191d' : opts.hovered ? '#0e5a69' : '#fff';
  return L.divIcon({
    className: '', iconSize: [size, size], iconAnchor: [size / 2, size / 2],
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:conic-gradient(${stops});
      box-shadow:0 0 0 2px ${ring},0 2px 6px rgba(0,0,0,.25);opacity:${opts.dim ? 0.35 : 1};transition:all .15s;
      display:flex;align-items:center;justify-content:center">
      <div style="width:${size - 10}px;height:${size - 10}px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;
        font:600 ${size > 26 ? 11 : 9}px ui-monospace,monospace;color:#17191d">${total || ''}</div></div>`,
  });
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

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  const t = useRef<number>();
  useEffect(() => {
    window.clearTimeout(t.current);
    t.current = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(t.current);
  }, [value, ms]);
  return v;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface NearbyWellsMapProps {
  wells: WellPoint[];
  activeWellId: string;
  /** Called when the user clicks a non-active well marker or list row. */
  onSelectWell?: (well: WellPoint) => void;
  /** Initial radius in km. Default 25. */
  initialRadiusKm?: number;
  /** Pixel height of the map. Default '640px'. */
  height?: string;
}

export const NearbyWellsMap: React.FC<NearbyWellsMapProps> = ({
  wells, activeWellId, onSelectWell, initialRadiusKm = 25, height = '640px',
}) => {
  const [radius, setRadius] = useState(initialRadiusKm);
  const [basemap, setBasemap] = useState<Basemap>('light');
  const [hazardFilter, setHazardFilter] = useState<Set<string>>(new Set());
  const [showLinks, setShowLinks] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [fitNonce, setFitNonce] = useState(0);
  const debounced = useDebounced(radius, 180);

  const active = wells.find((w) => w.well_id === activeWellId);
  const center: [number, number] | null = active ? [active.lat, active.lon] : null;

  const withDistance = useMemo(() => {
    if (!active) return [];
    return wells.map((w) => ({
      ...w,
      distance_km: w.well_id === active.well_id ? 0 : haversineKm(active.lat, active.lon, w.lat, w.lon),
      is_active: w.well_id === active.well_id,
    }));
  }, [wells, active]);

  const inRadius = withDistance.filter((w) => !w.is_active && w.distance_km <= debounced);
  const matchesFilter = (w: WellPoint) => hazardFilter.size === 0 || [...hazardFilter].some((h) => (w.events_by_type[h] ?? 0) > 0);
  const visibleList = inRadius.filter(matchesFilter).sort((a, b) => a.distance_km - b.distance_km);

  const hazardTotals = useMemo(() => {
    const t: Record<string, number> = {};
    inRadius.forEach((w) => Object.entries(w.events_by_type).forEach(([h, c]) => (t[h] = (t[h] ?? 0) + c)));
    return t;
  }, [inRadius]);

  const toggleHazard = (h: string) =>
    setHazardFilter((s) => {
      const x = new Set(s);
      x.has(h) ? x.delete(h) : x.add(h);
      return x;
    });

  const select = (w: WellPoint) => {
    setSelected(w.well_id);
    onSelectWell?.(w);
  };

  if (!center) {
    return <div style={{ padding: 24, fontFamily: 'system-ui' }}>Active well "{activeWellId}" not found in `wells`.</div>;
  }

  return (
    <div style={{ position: 'relative', height, width: '100%', fontFamily: 'system-ui, sans-serif', fontSize: 14, color: '#17191d' }}>
      <style>{`@keyframes nwisPulse { 0% { transform: scale(0.6); opacity: 0.7; } 100% { transform: scale(2.2); opacity: 0; } }`}</style>
      <MapContainer center={center} zoom={10} style={{ position: 'absolute', inset: 0 }} zoomControl={false}>
        <TileLayer key={basemap} url={BASEMAPS[basemap].url} attribution={BASEMAPS[basemap].attr} subdomains="abc" maxZoom={19} />
        <FitRadius center={center} radiusKm={debounced} nonce={fitNonce} />
        <Circle
          center={center}
          radius={debounced * 1000}
          pathOptions={{
            color: basemap === 'satellite' ? '#ffffff' : '#0e5a69',
            weight: basemap === 'satellite' ? 2.5 : 1.5,
            dashArray: '6 6',
            fillColor: basemap === 'satellite' ? '#ffffff' : '#0e5a69',
            fillOpacity: basemap === 'satellite' ? 0.1 : 0.05,
          }}
        />
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
              <Tooltip sticky>{w.well_name} · {w.distance_km.toFixed(1)} km from {active.well_name}</Tooltip>
            </Polyline>
          ))}
        {withDistance.map((w) => (
          <Marker
            key={w.well_id}
            position={[w.lat, w.lon]}
            icon={wellIcon(w, { isActive: w.is_active, selected: selected === w.well_id, hovered: hovered === w.well_id, dim: !w.is_active && (w.distance_km > debounced || !matchesFilter(w)) })}
            zIndexOffset={w.is_active ? 1000 : selected === w.well_id ? 800 : 0}
            eventHandlers={{
              click: () => select(w),
              mouseover: () => setHovered(w.well_id),
              mouseout: () => setHovered(null),
            }}
          >
            <Tooltip direction="top" offset={[0, -14]}>
              <div style={{ fontWeight: 600 }}>{w.well_name}{w.is_active ? ' · active well' : ''}</div>
              <div style={{ opacity: 0.75 }}>
                {w.is_active ? `${w.field} · TD ${Math.round(w.total_depth_md_m)} m` : `${w.distance_km.toFixed(1)} km · ${w.total_events} events · ${w.npt_hours}h NPT`}
              </div>
            </Tooltip>
            {(w.is_active || w.distance_km <= debounced) && (
              <Tooltip permanent direction="bottom" offset={[0, 12]} className="nwis-map-label">{w.well_name}</Tooltip>
            )}
          </Marker>
        ))}
      </MapContainer>

      {/* Control card */}
      <div style={{ position: 'absolute', zIndex: 500, top: 16, left: 16, width: 300, background: 'rgba(255,255,255,0.97)', border: '1px solid #e3e0d8', borderRadius: 12, boxShadow: '0 12px 32px -8px rgba(22,24,29,0.18)' }}>
        <div style={{ padding: '14px 16px 12px', borderBottom: '1px solid #e3e0d8' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#868a91', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Ruler size={14} /> Search radius
            </div>
            <div style={{ fontSize: 18, fontWeight: 500 }}>{debounced} km</div>
          </div>
          <input type="range" min={1} max={60} step={1} value={radius} onChange={(e) => setRadius(Number(e.target.value))} style={{ width: '100%', marginTop: 8, accentColor: '#0e5a69' }} />
          <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
            {RADIUS_PRESETS.map((r) => (
              <button key={r} onClick={() => setRadius(r)} style={{ flex: 1, height: 24, borderRadius: 6, fontSize: 11, border: radius === r ? '1px solid #0e5a69' : '1px solid #e3e0d8', background: radius === r ? '#0e5a69' : 'transparent', color: radius === r ? '#fff' : '#4a4e56', cursor: 'pointer' }}>
                {r} km
              </button>
            ))}
          </div>
          <div style={{ fontSize: 12, color: '#4a4e56', marginTop: 10 }}>
            <b style={{ color: '#17191d' }}>{inRadius.length}</b> offset well{inRadius.length === 1 ? '' : 's'} within {debounced} km of <b style={{ color: '#17191d' }}>{active.well_name}</b>
          </div>
        </div>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #e3e0d8' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#868a91', marginBottom: 8 }}>Show wells that had</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {Object.keys(hazardTotals).length === 0 && <span style={{ fontSize: 11, color: '#868a91' }}>No incidents in radius</span>}
            {Object.entries(hazardTotals).map(([h]) => {
              const on = hazardFilter.has(h);
              const c = colorOf(h);
              return (
                <button key={h} onClick={() => toggleHazard(h)} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, padding: '4px 8px', borderRadius: 999, border: `1px solid ${on ? c.color : '#e3e0d8'}`, background: on ? c.soft : 'transparent', color: on ? c.color : '#4a4e56', cursor: 'pointer' }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: c.color }} />
                  {c.label}
                  <span style={{ opacity: 0.7 }}>{hazardTotals[h]}</span>
                </button>
              );
            })}
          </div>
        </div>
        <div style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <div style={{ display: 'flex', gap: 4 }}>
            {(Object.keys(BASEMAPS) as Basemap[]).map((b) => (
              <button key={b} onClick={() => setBasemap(b)} style={{ fontSize: 11, padding: '0 8px', height: 24, borderRadius: 6, border: 'none', background: basemap === b ? '#17191d' : 'transparent', color: basemap === b ? '#fff' : '#4a4e56', cursor: 'pointer' }}>
                {BASEMAPS[b].label}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <button title="Distance lines" onClick={() => setShowLinks((v) => !v)} style={{ width: 28, height: 24, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${showLinks ? 'rgba(14,90,105,0.3)' : '#e3e0d8'}`, background: showLinks ? '#e2eff0' : 'transparent', color: showLinks ? '#0e5a69' : '#4a4e56', cursor: 'pointer' }}>
              <Crosshair size={14} />
            </button>
            <button title="Re-centre" onClick={() => setFitNonce((x) => x + 1)} style={{ width: 28, height: 24, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #e3e0d8', color: '#4a4e56', cursor: 'pointer', background: 'transparent' }}>
              <Target size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div style={{ position: 'absolute', zIndex: 500, bottom: 16, left: 16, background: 'rgba(255,255,255,0.97)', border: '1px solid #e3e0d8', borderRadius: 8, boxShadow: '0 1px 2px rgba(0,0,0,0.06)', padding: '8px 12px', fontSize: 11, color: '#4a4e56', display: 'flex', alignItems: 'center', gap: 8 }}>
        <Layers size={14} color="#868a91" />
        <span>Ring colours = incident mix · number = incidents · size grows with incidents</span>
      </div>

      {/* Side list */}
      <div style={{ position: 'absolute', zIndex: 500, top: 16, right: 16, width: 280, maxHeight: `calc(${height} - 32px)`, background: 'rgba(255,255,255,0.97)', border: '1px solid #e3e0d8', borderRadius: 12, boxShadow: '0 12px 32px -8px rgba(22,24,29,0.18)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid #e3e0d8', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#868a91' }}>
          Offset wells, nearest first
        </div>
        <div style={{ overflowY: 'auto' }}>
          {visibleList.length === 0 && <div style={{ padding: 16, fontSize: 13, color: '#868a91' }}>No offset wells match. Widen the radius or clear the filter.</div>}
          {visibleList.map((w) => (
            <button
              key={w.well_id}
              onMouseEnter={() => setHovered(w.well_id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => select(w)}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: '10px 14px', borderBottom: '1px solid #e3e0d8', background: hovered === w.well_id ? '#f4f3ef' : 'transparent', border: 'none', borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: '#e3e0d8', cursor: 'pointer', fontFamily: 'inherit' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13, fontWeight: 500 }}>{w.well_name}</span>
                <span style={{ fontSize: 12, color: '#4a4e56' }}>{w.distance_km.toFixed(1)} km</span>
              </div>
              <div style={{ fontSize: 11, color: '#868a91', marginTop: 2 }}>{w.field} · {w.well_type} · TD {Math.round(w.total_depth_md_m)}m</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default NearbyWellsMap;
