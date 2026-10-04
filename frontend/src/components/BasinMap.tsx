import React, { useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, Tooltip, useMap } from 'react-leaflet';
import type { LatLngBoundsExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Well } from '../types';

// A real interactive map (Leaflet + free tile providers, no API key
// required) — replaces the earlier schematic SVG that projected lat/lon
// with hand-tuned constants and drew fake fault-line/basin-info overlays as
// static decoration. Well positions below are the real surface_lat/lon from
// the API, rendered through Leaflet's actual projection, not a hand-rolled one.
//
// 3 basemap styles, matching the "different map visualizations" pattern
// seen in a competitor's demo -- deliberately using free-tier providers
// (Esri, OpenStreetMap) rather than Google Maps, which needs a billed API
// key that would be a real risk to depend on for a live demo.
//
// "dark" was CARTO's free anonymous basemaps.cartocdn.com/dark_all
// endpoint, confirmed broken during the 3D-integration pass (CARTO retired
// free/keyless access to these image basemaps -- every tile now renders an
// "API KEY REQUIRED" watermark instead of the map, confirmed via a live
// screenshot, not just reading about the deprecation). Swapped for Esri's
// World_Dark_Gray_Base, the same free/keyless provider already used for
// "satellite" (World_Imagery) below -- confirmed working with a direct
// tile request (HTTP 200) before switching.
type MapStyle = 'dark' | 'streets' | 'satellite';

const MAP_STYLES: Record<MapStyle, { label: string; url: string; attribution: string }> = {
  dark: {
    label: 'Dark Vector',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, HERE, Garmin, FAO, NOAA, USGS',
  },
  streets: {
    label: 'Streets',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  },
  satellite: {
    label: 'Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community',
  },
};

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
  const [mapStyle, setMapStyle] = useState<MapStyle>('dark');
  const activeWell = useMemo(() => wells.find((w) => w.well_id === activeWellId), [wells, activeWellId]);
  const center: [number, number] = activeWell
    ? [activeWell.surface_lat, activeWell.surface_lon]
    : wells.length > 0
    ? [wells[0].surface_lat, wells[0].surface_lon]
    : [27.15, 95.3];

  return (
    <div className="relative w-full h-full">
      <div className="absolute top-2 right-2 z-[1000] bg-slate-950/90 border border-slate-800 rounded-lg p-1 flex gap-1">
        {(Object.keys(MAP_STYLES) as MapStyle[]).map((key) => (
          <button
            key={key}
            onClick={() => setMapStyle(key)}
            className={`px-2 py-1 rounded text-[10px] font-mono transition-colors ${
              mapStyle === key ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200 border border-transparent'
            }`}
          >
            {MAP_STYLES[key].label}
          </button>
        ))}
      </div>
    <MapContainer
      center={center}
      zoom={11}
      className="w-full h-full"
      style={{ background: '#090c12' }}
      zoomControl={true}
    >
      <TileLayer key={mapStyle} url={MAP_STYLES[mapStyle].url} attribution={MAP_STYLES[mapStyle].attribution} />
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
    </div>
  );
};
