import * as React from 'react';
import type { Well, WellData } from './data-contract';
import { SCENE_METRES_TO_UNITS, stationToFieldPoint } from './spatialFrame';

interface Props {
  active: Well;
  selected: Well | null;
  data: Map<string, WellData>;
  onSelect: (wellId: string) => void;
}
interface PlotPoint { x: number; y: number }
interface PlotPath { id: string; color: string; points: PlotPoint[] }

function fitPath(paths: PlotPath[], width = 150, height = 100) {
  const all = paths.flatMap(path => path.points);
  if (!all.length) return (_point: PlotPoint) => ({ x: width / 2, y: height / 2 });
  const minX = Math.min(...all.map(point => point.x)), maxX = Math.max(...all.map(point => point.x));
  const minY = Math.min(...all.map(point => point.y)), maxY = Math.max(...all.map(point => point.y));
  const pad = 11;
  const spanX = Math.max(1, maxX - minX), spanY = Math.max(1, maxY - minY);
  // Equal metres-per-pixel preserves physical proportions in both projections.
  const scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY);
  const drawnWidth = spanX * scale, drawnHeight = spanY * scale;
  const left = pad + (width - pad * 2 - drawnWidth) / 2;
  const top = pad + (height - pad * 2 - drawnHeight) / 2;
  return (point: PlotPoint) => ({ x: left + (point.x - minX) * scale, y: height - top - (point.y - minY) * scale });
}

function MiniPlot({ title, subtitle, paths, onSelect }: { title: string; subtitle: string; paths: PlotPath[]; onSelect: Props['onSelect'] }) {
  const project = React.useMemo(() => fitPath(paths), [paths]);
  return <section className="survey-mini-plot">
    <header><b>{title}</b><span>{subtitle}</span></header>
    <svg viewBox="0 0 150 100" role="img" aria-label={`${title}: measured survey projection`}>
      {[0, 1, 2, 3, 4].map(tick => <React.Fragment key={tick}>
        <line x1={8 + tick * 33.5} y1="8" x2={8 + tick * 33.5} y2="92" className="survey-plot-grid" />
        <line x1="8" y1={8 + tick * 21} x2="142" y2={8 + tick * 21} className="survey-plot-grid" />
      </React.Fragment>)}
      {paths.map(path => {
        const projected = path.points.map(project);
        if (projected.length < 2) return null;
        const d = projected.map((point, index) => `${index ? 'L' : 'M'}${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' ');
        return <g key={path.id} className="survey-plot-path" role="button" tabIndex={0} aria-label={`Select ${path.id}`} onClick={() => onSelect(path.id)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(path.id); } }}>
          <path d={d} fill="none" stroke={path.color} strokeWidth="1.25" vectorEffect="non-scaling-stroke" />
          {projected.length > 0 && <circle cx={projected[0].x} cy={projected[0].y} r="2.1" fill={path.color} />}
          {projected.length > 1 && <circle cx={projected.at(-1)!.x} cy={projected.at(-1)!.y} r="1.8" fill={path.color} />}
        </g>;
      })}
      {!paths.length && <text x="75" y="52" textAnchor="middle" className="survey-plot-empty">Survey unavailable</text>}
    </svg>
  </section>;
}

/** Synchronized plan/section projections built only from reported survey stations. */
export function SurveyOverview({ active, selected, data, onSelect }: Props) {
  const paths = React.useMemo(() => [active, ...(selected && selected.well_id !== active.well_id ? [selected] : [])].flatMap((well, index) => {
    const stations = data.get(well.well_id)?.trajectory?.stations;
    if (!stations?.length) return [];
    const color = index === 0 ? '#f2a65a' : '#65d8c7';
    const points = stations.flatMap(station => {
      const point = stationToFieldPoint(station, active, well);
      return point ? [{ x: point.x / SCENE_METRES_TO_UNITS, y: point.z / SCENE_METRES_TO_UNITS }] : [];
    });
    return points.length > 1 ? [{ id: well.well_id, color, points }] : [];
  }), [active, selected, data]);
  const profile = React.useMemo(() => {
    const stations = data.get(active.well_id)?.trajectory?.stations ?? [];
    return stations.length > 1 ? [{
      id: active.well_id,
      color: '#f2a65a',
      points: stations.map(station => ({ x: station.ew_m, y: -station.tvd_m })),
    }] : [];
  }, [active.well_id, data]);
  const activeStationCount = data.get(active.well_id)?.trajectory?.stations.length ?? 0;
  return <aside className="survey-overview" aria-label="Measured survey projections" onPointerDown={event => event.stopPropagation()}>
    <div className="survey-overview-heading"><span>MEASURED SURVEY · {activeStationCount.toLocaleString()} STATIONS</span><small>TRUE-SCALE PROJECTIONS</small></div>
    <div className="survey-overview-plots">
      <MiniPlot title="PLAN" subtitle="EAST × NORTH · m" paths={paths} onSelect={onSelect} />
      <MiniPlot title="SECTION" subtitle="EAST × TVD · m" paths={profile} onSelect={onSelect} />
    </div>
    <div className="survey-overview-legend"><i className="survey-active-key" />{active.well_id}{selected && selected.well_id !== active.well_id && paths.some(path => path.id === selected.well_id) && <><i className="survey-selected-key" />{selected.well_id}</>}</div>
    <span className="survey-overview-note">SECTION DATUM IS PER WELL · OFFSET TVD IS NOT ALIGNED</span>
  </aside>;
}
