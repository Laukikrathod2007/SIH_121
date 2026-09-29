import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, Tooltip, useMap } from 'react-leaflet';
import type { LatLngBoundsExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Well } from '../types';

// A real interactive map (Leaflet + free CartoDB dark tiles, no API key
// required) — replaces the earlier schematic SVG that projected lat/lon
// with hand-tuned constants and drew fake fault-line/basin-info overlays as
// static decoration. Well positions below are the real surface_lat/lon from
// the API, rendered through Leaflet's actual projection, not a hand-rolled one.

const DARK_TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const DARK_TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

interface BasinMapProps {
  wells: Well[];
  activeWellId: string;
  selectedWellId: string;
  onSelectWell: (wellId: string) => void;
  radiusKm?: number;
}

function FitToWells({ wells }: { wells: Well[] }) {
  const map = useMap();
  useEffect(() => {
    if (wells.length === 0) return;
    const bounds: LatLngBoundsExpression = wells.map((w) => [w.surface_lat, w.surface_lon]);
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
  }, [wells, map]);
  return null;
}

export const BasinMap: React.FC<BasinMapProps> = ({ wells, activeWellId, selectedWellId, onSelectWell, radiusKm }) => {
  const activeWell = useMemo(() => wells.find((w) => w.well_id === activeWellId), [wells, activeWellId]);
  const center: [number, number] = activeWell
    ? [activeWell.surface_lat, activeWell.surface_lon]
    : wells.length > 0
    ? [wells[0].surface_lat, wells[0].surface_lon]
    : [27.15, 95.3];

  return (
    <MapContainer
      center={center}
      zoom={11}
      className="w-full h-full"
      style={{ background: '#090c12' }}
      zoomControl={true}
    >
      <TileLayer url={DARK_TILE_URL} attribution={DARK_TILE_ATTRIBUTION} />
      <FitToWells wells={wells} />
      {activeWell && radiusKm && (
        <Circle
          center={[activeWell.surface_lat, activeWell.surface_lon]}
          radius={radiusKm * 1000}
          pathOptions={{ color: '#06b6d4', weight: 1.5, opacity: 0.5, fillColor: '#06b6d4', fillOpacity: 0.06, dashArray: '6 4' }}
        />
      )}
      {wells.map((w) => {
        const isActive = w.well_id === activeWellId;
        const isSelected = w.well_id === selectedWellId;
        const color = isActive ? '#06b6d4' : isSelected ? '#f59e0b' : '#64748b';
        const radius = isActive ? 10 : isSelected ? 8 : 6;
        return (
          <CircleMarker
            key={w.well_id}
            center={[w.surface_lat, w.surface_lon]}
            radius={radius}
            pathOptions={{
              color: isActive ? '#e0f2fe' : isSelected ? '#fef3c7' : '#94a3b8',
              weight: isActive || isSelected ? 2 : 1,
              fillColor: color,
              fillOpacity: isActive || isSelected ? 0.85 : 0.55,
            }}
            eventHandlers={{ click: () => onSelectWell(w.well_id) }}
          >
            <Tooltip direction="top" offset={[0, -8]} opacity={1} permanent={isActive}>
              <span className="font-mono text-[11px]">{w.well_name}{isActive ? ' (ACTIVE)' : ''}</span>
            </Tooltip>
            <Popup>
              <div className="font-mono text-xs space-y-1">
                <div className="font-bold">{w.well_name} ({w.well_id})</div>
                <div>Field: {w.field}</div>
                <div>Type: {w.well_type} &middot; TD: {w.total_depth_md_m}m</div>
                <div>Status: {w.status}</div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
};
