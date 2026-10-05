import * as React from 'react';
import { Canvas, ThreeEvent, useFrame } from '@react-three/fiber';
import { Html, Line, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import type { FormationObservation, Stage, Well, WellData } from './data-contract';
import { formationMD, nearbyWells, normalizedFormationName, rankedOffsetsWithinRadius } from './geometry';
import { SCENE_METRES_TO_UNITS, stationToFieldPoint, wellheadENU } from './spatialFrame';

interface Props {
  stage: Stage; wells: Well[]; active: Well | null; data: Map<string, WellData>;
  radiusKm: number; selectedId: string | null; onSelect: (id: string) => void;
  layers: { formations: boolean; trajectories: boolean; events: boolean; hazards: boolean; casing: boolean };
  evaluationDepthM?: number | null;
  onSelectObject?: (value: { type: string; wellId: string; depthM?: number; label: string } | null) => void;
}

const color = { active: '#f2a65a', selected: '#6de0cf', offset: '#73a8d1', quiet: '#66747d', event: '#ffd166', hazard: '#ef6b63', formation: '#b1c67a', surface: '#87989e' };
// Earth/mineral-inspired categorical colors distinguish recorded formation
// names; they do not assert lithology or measured rock properties.
const formationPalette = ['#d2aa70','#aa7959','#7f8c83','#b68b66','#7c9a9b','#987b91','#bd9a52'];
function formationColor(name: string) {
  let hash=0; for (const char of name.toLocaleLowerCase()) hash=(hash*31+char.charCodeAt(0))|0;
  return formationPalette[Math.abs(hash)%formationPalette.length];
}
const unit = SCENE_METRES_TO_UNITS;

function ClickTarget({ wellId, onSelect, onSelectObject, type, label, depthM, children }: {
  wellId: string; onSelect: (id: string) => void; onSelectObject?: Props['onSelectObject']; type: string; label: string; depthM?: number; children: React.ReactNode;
}) {
  return <group onClick={(event: ThreeEvent<MouseEvent>) => { event.stopPropagation(); onSelect(wellId); onSelectObject?.({ type, wellId, depthM, label }); }}>{children}</group>;
}

function CameraJourney({ stage, target, downholePoint, radiusKm, trajectoryExtent }: { stage: Stage; target: THREE.Vector3; downholePoint: THREE.Vector3; radiusKm: number; trajectoryExtent: number }) {
  const controls = React.useRef<any>(null);
  const to = React.useRef(new THREE.Vector3());
  const lookAt = React.useRef(target.clone());
  const viewMode = React.useRef('orbit');
  const lastStage = React.useRef(stage);
  const transitioning = React.useRef(false);
  const radiusForCamera = stage === 'subsurface' ? 0 : radiusKm;
  React.useEffect(() => {
    const radiusExtent = radiusKm * 1000 * unit;
    // At depth, frame the actual surveyed paths. The surface search radius is
    // context only and can be kilometres wide; letting it set camera distance
    // made short/partial surveys almost disappear.
    if (lastStage.current !== stage) {
      viewMode.current = 'orbit';
      lastStage.current = stage;
    }
    const extent = stage === 'subsurface'
      ? Math.max(8, trajectoryExtent * 1.45)
      : Math.max(55, radiusExtent * 1.72, trajectoryExtent * 1.45);
    const focus = viewMode.current === 'downhole' ? downholePoint : target;
    lookAt.current.copy(focus);
    if (stage === 'global') to.current.set(0, 0, 345);
    else if (stage === 'field') to.current.set(0, Math.max(42, radiusExtent * 2.45), 0.01);
    else if (viewMode.current === 'plan') to.current.copy(focus).add(new THREE.Vector3(0, extent * 2.1, 0.01));
    else if (viewMode.current === 'section') to.current.copy(focus).add(new THREE.Vector3(0, extent * 0.08, extent * 2.2));
    else if (viewMode.current === 'downhole') {
      const closeRange = Math.max(9, Math.min(26, trajectoryExtent * 0.085));
      to.current.copy(focus).add(new THREE.Vector3(closeRange * 0.8, closeRange * 0.32, closeRange));
    }
    // Y is positive up and survey TVD is plotted downward. Keep the camera
    // above the trajectory centre and far enough away to frame the full path
    // instead of looking upward from below it or clipping the trajectory ends.
    else to.current.copy(target).add(new THREE.Vector3(extent * 1.45, extent * 0.85, extent * 1.75));
    transitioning.current = true;
  }, [stage, radiusForCamera, trajectoryExtent, target.x, target.y, target.z, downholePoint.x, downholePoint.y, downholePoint.z]);
  React.useEffect(() => {
    const reframe = () => {
      const extent = Math.max(8, trajectoryExtent * 1.45);
      viewMode.current = 'orbit';
      to.current.copy(target).add(new THREE.Vector3(extent * 1.45, extent * 0.85, extent * 1.75));
      lookAt.current.copy(target);
      transitioning.current = true;
    };
    window.addEventListener('nwis:fit-subsurface', reframe);
    return () => window.removeEventListener('nwis:fit-subsurface', reframe);
  }, [target, trajectoryExtent]);
  React.useEffect(() => {
    const changeView = (event: Event) => {
      const mode = (event as CustomEvent<{ mode?: string }>).detail?.mode;
      viewMode.current = mode ?? 'orbit';
      const extent = Math.max(8, trajectoryExtent * 1.45);
      const focus = mode === 'downhole' ? downholePoint : target;
      lookAt.current.copy(focus);
      if (mode === 'plan') to.current.copy(focus).add(new THREE.Vector3(0, extent * 2.1, 0.01));
      else if (mode === 'section') to.current.copy(focus).add(new THREE.Vector3(0, extent * 0.08, extent * 2.2));
      else if (mode === 'downhole') {
        const closeRange = Math.max(9, Math.min(26, trajectoryExtent * 0.085));
        to.current.copy(focus).add(new THREE.Vector3(closeRange * 0.8, closeRange * 0.32, closeRange));
      }
      else to.current.copy(focus).add(new THREE.Vector3(extent * 1.45, extent * 0.85, extent * 1.75));
      transitioning.current = true;
    };
    window.addEventListener('nwis:scene-view', changeView);
    return () => window.removeEventListener('nwis:scene-view', changeView);
  }, [target, downholePoint, trajectoryExtent]);
  useFrame(({ camera }, delta) => {
    // Animate framing only after the target changes. Continuously forcing the
    // destination prevented OrbitControls from keeping the user's orbit/zoom.
    if (!transitioning.current) return;
    const positionAlpha = 1 - Math.exp(-delta * (stage === 'subsurface' ? 2.1 : 1.05));
    camera.position.lerp(to.current, positionAlpha);
    if (!controls.current) return;
    controls.current.target.lerp(lookAt.current, 1 - Math.exp(-delta * 1.25));
    controls.current.update();
    if (camera.position.distanceToSquared(to.current) < 0.01 && controls.current.target.distanceToSquared(lookAt.current) < 0.01) {
      camera.position.copy(to.current);
      controls.current.target.copy(lookAt.current);
      transitioning.current = false;
      controls.current.update();
    }
  });
  return <OrbitControls ref={controls} makeDefault enableDamping dampingFactor={0.075} minDistance={stage === 'global' ? 112 : 1} maxDistance={stage === 'global' ? 1100 : 12000} minPolarAngle={0.12} maxPolarAngle={Math.PI - 0.12} screenSpacePanning />;
}

function ActiveTvdScale({ data, well, active }: { data: WellData; well: Well; active: Well }) {
  const stations = data.trajectory?.stations ?? [];
  if (well.well_id !== active.well_id || stations.length < 2) return null;
  const tvds = stations.map(station => station.tvd_m).filter(Number.isFinite);
  if (tvds.length < 2) return null;
  const minTvd = Math.min(...tvds), maxTvd = Math.max(...tvds);
  const interval = maxTvd - minTvd < 800 ? 100 : 500;
  const firstTick = Math.ceil(minTvd / interval) * interval;
  const ticks: Array<{ value: number; point: THREE.Vector3 }> = [];
  for (let value = firstTick; value <= maxTvd; value += interval) {
    const station = stations.reduce((best, item) => Math.abs(item.tvd_m - value) < Math.abs(best.tvd_m - value) ? item : best, stations[0]);
    const position = stationToFieldPoint(station, active, well);
    if (position && (!ticks.length || ticks.at(-1)!.point.distanceTo(new THREE.Vector3(position.x, position.y, position.z)) > 2)) {
      ticks.push({ value, point: new THREE.Vector3(position.x, position.y, position.z) });
    }
  }
  if (!ticks.length) return null;
  return <group>
    <Html position={[ticks[0].point.x + 4.2, ticks[0].point.y + 1.8, ticks[0].point.z]} center={false} distanceFactor={32} style={{ pointerEvents: 'none' }}><span className="world-label muted">ACTIVE WELL TVD · LOCAL DATUM</span></Html>
    {ticks.map(tick => <React.Fragment key={tick.value}>
      <Line points={[[tick.point.x, tick.point.y, tick.point.z], [tick.point.x + 3.4, tick.point.y, tick.point.z]]} color="#9aadb0" lineWidth={1.25} transparent opacity={0.88} />
      <Html position={[tick.point.x + 3.9, tick.point.y, tick.point.z]} center={false} distanceFactor={30} style={{ pointerEvents: 'none' }}><span className="world-label muted">{tick.value.toLocaleString()} m TVD</span></Html>
    </React.Fragment>)}
  </group>;
}

/** An open TVD reference frame. No formation geometry is drawn without picks. */
function SubsurfaceSectionBackdrop({ points, activeData }: { points: THREE.Vector3[]; activeData: WellData }) {
  const layout = React.useMemo(() => {
    if (points.length < 2) return null;
    const bounds = new THREE.Box3().setFromPoints(points);
    const maxTvd = Math.max(...(activeData.trajectory?.stations.map(station => station.tvd_m) ?? [0]));
    const width = Math.max(24, bounds.max.x - bounds.min.x + 18);
    const centerX = (bounds.min.x + bounds.max.x) / 2;
    const left = centerX - width / 2, right = centerX + width / 2;
    const top = Math.max(0, bounds.max.y) + 1.5, bottom = Math.min(bounds.min.y, -maxTvd * unit) - 2;
    const z = bounds.min.z - Math.max(5, width * 0.12);
    const horizontal: Array<{ y: number; depth: number }> = [];
    for (let depth = 500; depth <= maxTvd; depth += 500) horizontal.push({ y: -depth * unit, depth });
    return { left, right, top, bottom, z, horizontal, maxTvd };
  }, [points, activeData]);
  if (!layout) return null;
  const { left, right, top, bottom, z, horizontal, maxTvd } = layout;
  return <group>
    {/* Fine open guides retain measured depth context without implying a
        continuous formation surface or placing the well on a floating slab. */}
    <Line points={[[left,0,z],[right,0,z]]} color="#f2a65a" lineWidth={1.7} transparent opacity={0.82} />
    <Line points={[[left,0,z],[left,bottom,z]]} color="#829096" lineWidth={0.8} transparent opacity={0.3} />
    <Line points={[[right,0,z],[right,bottom,z]]} color="#829096" lineWidth={0.8} transparent opacity={0.18} />
    <Html position={[right,0.8,z]} center={false} distanceFactor={27} style={{pointerEvents:'none'}}><span className="world-label depth-reference-label">WELLHEAD DATUM · 0 m TVD</span></Html>
    {horizontal.map(({ y, depth }) => <React.Fragment key={`section-tvd-${depth}`}>
      <Line points={[[left,y,z],[right,y,z]]} color="#aab4af" lineWidth={0.8} transparent opacity={0.2} />
      <Line points={[[left-0.7,y,z],[left+0.7,y,z]]} color="#d6b28d" lineWidth={1} transparent opacity={0.65} />
      <Html position={[left-1.4,y,z]} center={false} distanceFactor={26} style={{pointerEvents:'none'}}><span className="world-label depth-reference-label">{depth.toLocaleString()} m TVD</span></Html>
    </React.Fragment>)}
    <Html position={[left,top + 1.25,z]} center={false} distanceFactor={27} style={{pointerEvents:'none'}}><span className="world-label depth-reference-label">DEPTH GUIDES · {Math.round(maxTvd).toLocaleString()} m TVD · NO FORMATION DATA</span></Html>
  </group>;
}
function Trajectory({ well, active, data, selected, rank, props }: { well: Well; active: Well; data: WellData; selected: boolean; rank: number; props: Props }) {
  const trajectory = data.trajectory;
  const points = React.useMemo(() => trajectory?.stations.map(s => stationToFieldPoint(s, active, well)).filter((p): p is NonNullable<typeof p> => p != null).map(p => new THREE.Vector3(p.x, p.y, p.z)) ?? [], [trajectory, active, well]);
  const directionMarkers = React.useMemo(() => {
    if (points.length < 12) return [];
    return [0.34, 0.68].map(fraction => {
      const index = Math.min(points.length - 2, Math.floor((points.length - 1) * fraction));
      const tangent = points[index + 1].clone().sub(points[index]).normalize();
      return { position: points[index], quaternion: new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent) };
    });
  }, [points]);
  // Small survey-station beads reveal the measured sampling cadence without
  // inventing geology or turning the trajectory into a thick fake drill pipe.
  const stationMarkers = React.useMemo(() => {
    const stride = Math.max(1, Math.ceil(points.length / 10));
    return points.filter((_, index) => index === 0 || index === points.length - 1 || index % stride === 0);
  }, [points]);
  const isActive = well.well_id === active.well_id;
  const lineColor = isActive ? color.active : selected ? color.selected : rank < 0 ? color.quiet : color.offset;
  const opacity = isActive || selected ? 0.98 : rank > 2 ? 0.43 : 0.76;
  const tube = React.useMemo(() => {
    // A narrow shaded body makes the trajectory legible as a 3D wellbore.
    // It follows the actual ordered survey stations; its display diameter is
    // schematic and never represents measured casing or hole size.
    if (points.length < 2) return null;
    const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal');
    const segments = Math.max(48, Math.min(1600, points.length * 2));
    // Display-only line weight is slightly exaggerated so the measured path
    // stays legible at field scale; this is not a borehole/casing diameter.
    const radius = isActive ? 0.15 : selected ? 0.12 : 0.07;
    const radialSegments = 10;
    const geometry = new THREE.TubeGeometry(curve, segments, radius, radialSegments, false);
    const startColor = new THREE.Color(isActive ? '#f4a85c' : selected ? '#69e0ce' : lineColor);
    const endColor = new THREE.Color(isActive ? '#78b9a7' : selected ? '#668fda' : lineColor);
    const colors = new Float32Array(geometry.getAttribute('position').count * 3);
    for (let vertex=0; vertex<geometry.getAttribute('position').count; vertex++) {
      const sampleIndex=Math.floor(vertex/(radialSegments+1));
      const t=Math.min(1,sampleIndex/segments);
      const value=new THREE.Color().lerpColors(startColor,endColor,t);
      colors[vertex*3]=value.r; colors[vertex*3+1]=value.g; colors[vertex*3+2]=value.b;
    }
    geometry.setAttribute('color',new THREE.BufferAttribute(colors,3));
    return geometry;
  }, [points, isActive, selected, lineColor]);
  React.useEffect(() => () => { tube?.dispose(); }, [tube]);
  if (!trajectory || points.length < 2) return null;
  const formationMarks = props.layers.formations ? formationRows(data.formations, trajectory.stations, well, active) : [];
  const events = props.layers.events ? data.events : [];
  const hazards = props.layers.hazards ? data.corridors : [];
  const mdStart = trajectory.stations[0]?.md_m ?? null, mdEnd = trajectory.stations.at(-1)?.md_m ?? null;
  const telemetryMd = data.telemetry.map(t => finite(t.measured_depth_m ?? t.current_measured_depth_m)).filter((n): n is number => n != null).at(-1);
  const bitStation = telemetryMd == null ? null : interpolateStation(trajectory.stations, telemetryMd);
  const worldBit = bitStation ? stationToFieldPoint(bitStation, active, well) : null;
  return <group>
    {props.layers.trajectories && <ClickTarget wellId={well.well_id} onSelect={props.onSelect} onSelectObject={props.onSelectObject} type="trajectory" label={well.well_id}>
      {tube && <mesh geometry={tube}><meshStandardMaterial color="#ffffff" vertexColors emissive="#15212a" emissiveIntensity={0.22} roughness={0.29} metalness={0.42} transparent opacity={opacity} /></mesh>}
      {selected && !isActive && <Line points={points} color={lineColor} lineWidth={7} transparent opacity={0.12} />}
      <Line points={points} color={lineColor} lineWidth={isActive ? 1.7 : selected ? 1.6 : rank < 0 ? 1.1 : 1.35} transparent opacity={opacity*0.62} />
      {stationMarkers.map((point, index) => <mesh key={`survey-station-${index}`} position={point}>
        <sphereGeometry args={[0.09, 8, 6]} />
        <meshBasicMaterial color={lineColor} transparent opacity={isActive || selected ? 0.62 : 0.32} />
      </mesh>)}
      {directionMarkers.map((marker, index) => <mesh key={`direction-${index}`} position={marker.position} quaternion={marker.quaternion}>
        <coneGeometry args={[0.28, 1.2, 8]} />
        <meshBasicMaterial color={lineColor} transparent opacity={isActive || selected ? 0.88 : 0.55} />
      </mesh>)}
      <mesh position={points[0]}><sphereGeometry args={[isActive ? 0.9 : 0.58, 18, 12]} /><meshStandardMaterial color={lineColor} emissive={lineColor} emissiveIntensity={0.16} /></mesh>
      <Html position={[points[0].x + 1.4, 1.8, points[0].z]} center={false} distanceFactor={18} style={{pointerEvents:'none'}}><span className="world-label" style={{color:lineColor}}>{well.well_id}</span></Html>
      {mdStart != null && mdEnd != null && <Html position={[points.at(-1)!.x, points.at(-1)!.y - 1.8, points.at(-1)!.z]} center distanceFactor={18} style={{pointerEvents:'none'}}><span className="world-label muted">{`${Math.round(mdEnd).toLocaleString()} m MD · ${Math.round(trajectory.stations.at(-1)!.tvd_m).toLocaleString()} m TVD`}</span></Html>}
    </ClickTarget>}
    {formationMarks.map((mark, index) => {
      const interval = mark.endMd == null ? [] : stationPathBetweenMD(trajectory.stations, mark.md, mark.endMd, active, well);
      const intervalColor=formationColor(mark.name);
      return <ClickTarget key={`formation-${index}`} wellId={well.well_id} onSelect={props.onSelect} onSelectObject={props.onSelectObject} type="formation" label={`${mark.name} · ${Math.round(mark.md)} m MD`} depthM={mark.md}>
        {interval.length > 1
          ? <Line points={interval} color={intervalColor} lineWidth={6} transparent opacity={0.52} />
          : <mesh position={mark.point}><sphereGeometry args={[0.42, 12, 10]} /><meshStandardMaterial color={intervalColor} roughness={0.38} metalness={0.16} transparent opacity={0.88} /></mesh>}
        <Html position={[mark.point.x + 1, mark.point.y, mark.point.z]} center={false} distanceFactor={18} style={{pointerEvents:'none'}}><span className="world-label formation-label">{mark.name}{mark.endMd != null ? ` · ${Math.round(mark.md)}–${Math.round(mark.endMd)} m MD` : ''}</span></Html>
      </ClickTarget>;
    })}
    {events.map((event, index) => {
      const md = finite(event.depth_start_md_m); if (md == null) return null;
      const station = interpolateStation(trajectory.stations, md); if (!station) return null;
      const point = stationToFieldPoint(station, active, well); if (!point) return null;
       const label = [event.event_type, event.severity, event.formation].filter(Boolean).map(String).join(' · ') || 'Event';
       return <ClickTarget key={`event-${index}`} wellId={well.well_id} onSelect={props.onSelect} onSelectObject={props.onSelectObject} type="event" label={`${label} · ${Math.round(md)} m MD`} depthM={md}><mesh position={[point.x, point.y, point.z]}><octahedronGeometry args={[0.72, 0]} /><meshStandardMaterial color={color.event} roughness={0.58} metalness={0.12} /></mesh><Html position={[point.x + 1, point.y + 0.75, point.z]} center={false} distanceFactor={18} style={{pointerEvents:'none'}}><span className="world-label event-label">{label} · {Math.round(md).toLocaleString()} m MD</span></Html></ClickTarget>;
    })}
    {hazards.map((hazard, index) => {
      const a = finite(hazard.depth_start_m), b = finite(hazard.depth_end_m); if (a == null || b == null) return null;
      const inside = trajectory.stations.filter(s => s.md_m >= a && s.md_m <= b);
      const stationList = [interpolateStation(trajectory.stations, a), ...inside, interpolateStation(trajectory.stations, b)].filter((s): s is NonNullable<typeof s> => s != null);
      const path = stationList.map(s => stationToFieldPoint(s, active, well)).filter((p): p is NonNullable<typeof p> => p != null).map(p => new THREE.Vector3(p.x, p.y, p.z));
      if (path.length < 2) return null;
       const callout = path[Math.floor(path.length / 2)];
       return <ClickTarget key={`hazard-${index}`} wellId={well.well_id} onSelect={props.onSelect} onSelectObject={props.onSelectObject} type="hazard" label={`${hazard.risk_level ?? 'Risk'} · ${Math.round(a)}–${Math.round(b)} m MD`} depthM={a}><Line points={path} color={color.hazard} lineWidth={5} transparent opacity={0.76} /><Html position={[callout.x + 1, callout.y, callout.z]} center={false} distanceFactor={18} style={{pointerEvents:'none'}}><span className="world-label hazard-label">{hazard.risk_level ?? 'RISK'} · {Math.round(a)}–{Math.round(b)} m MD</span></Html></ClickTarget>;
    })}
    {props.layers.casing && data.casing.map((section, index) => {
      const a = finite(section.depth_start_md_m), b = finite(section.depth_end_md_m); if (a == null || b == null) return null;
      const casingPath = stationPathBetweenMD(trajectory.stations, a, b, active, well); if (casingPath.length < 2) return null;
      return <Line key={`casing-${index}`} points={casingPath} color="#abb4b1" lineWidth={3.5} transparent opacity={0.42} />;
    })}
    {isActive && telemetryMd != null && worldBit && <ClickTarget wellId={well.well_id} onSelect={props.onSelect} onSelectObject={props.onSelectObject} type="telemetry" label={`Telemetry depth · ${Math.round(telemetryMd)} m MD`} depthM={telemetryMd}><mesh position={[worldBit.x,worldBit.y,worldBit.z]}><octahedronGeometry args={[1.08, 1]} /><meshStandardMaterial color="#fff1ba" emissive={color.active} emissiveIntensity={0.75} /></mesh></ClickTarget>}
    {props.evaluationDepthM != null && isActive && mdStart != null && mdEnd != null && props.evaluationDepthM >= mdStart && props.evaluationDepthM <= mdEnd && (() => {
      const station = interpolateStation(trajectory.stations, props.evaluationDepthM); if (!station) return null;
      const p = stationToFieldPoint(station, active, well); if (!p) return null;
      return <ClickTarget wellId={well.well_id} onSelect={props.onSelect} onSelectObject={props.onSelectObject} type="evaluation depth" label={`Evaluation · ${Math.round(props.evaluationDepthM)} m MD`} depthM={props.evaluationDepthM}><mesh position={[p.x,p.y,p.z]}><sphereGeometry args={[0.63,14,10]} /><meshBasicMaterial color="#f4f0dc" /></mesh><Html position={[p.x + 1, p.y, p.z]} center={false} distanceFactor={18} style={{pointerEvents:'none'}}><span className="world-label muted">EVALUATION · {Math.round(props.evaluationDepthM)} m MD</span></Html></ClickTarget>;
    })()}
  </group>;
}

function formationRows(rows: FormationObservation[], stations: NonNullable<WellData['trajectory']>['stations'], well: Well, active: Well) {
  const result: Array<{ name: string; md: number; endMd?: number; point: THREE.Vector3 }> = [];
  for (const row of rows) {
    if (row.well_id && row.well_id !== well.well_id) continue;
    const md = formationMD(row); if (md == null) continue;
    const station = interpolateStation(stations, md); if (!station) continue;
    const p = stationToFieldPoint(station, active, well); if (!p) continue;
    const explicitEnd = finite(row.base_md_m ?? row.depth_base_md_m ?? row.base_depth_md_m ?? row.depth_bottom_md_m);
    const endMd = explicitEnd != null && explicitEnd > md ? explicitEnd : undefined;
    result.push({ name: normalizedFormationName(row), md, endMd, point: new THREE.Vector3(p.x,p.y,p.z) });
  }
  return result;
}

/** Follow the actual surveyed centerline between two MDs; never draw a chord through a curved section. */
function stationPathBetweenMD(
  stations: NonNullable<WellData['trajectory']>['stations'], startMd: number, endMd: number, active: Well, well: Well,
): THREE.Vector3[] {
  const low = Math.min(startMd, endMd), high = Math.max(startMd, endMd);
  const start = interpolateStation(stations, low), end = interpolateStation(stations, high);
  if (!start || !end) return [];
  const stationByMd = new Map<number, typeof start>();
  stationByMd.set(start.md_m, start);
  for (const station of stations) if (station.md_m > low && station.md_m < high) stationByMd.set(station.md_m, station);
  stationByMd.set(end.md_m, end);
  return [...stationByMd.values()].sort((a, b) => a.md_m - b.md_m).flatMap(station => {
    const point = stationToFieldPoint(station, active, well);
    return point ? [new THREE.Vector3(point.x, point.y, point.z)] : [];
  });
}

function interpolateStation(stations: NonNullable<WellData['trajectory']>['stations'], md: number) {
  if (!stations.length || md < stations[0].md_m || md > stations.at(-1)!.md_m) return null;
  const upper = stations.findIndex(s => s.md_m >= md); if (upper <= 0) return stations[0];
  const a=stations[upper-1], b=stations[upper], t=b.md_m===a.md_m?0:(md-a.md_m)/(b.md_m-a.md_m);
  const lerp=(x:number,y:number)=>x+(y-x)*t;
  return { ...a, md_m: md, tvd_m:lerp(a.tvd_m,b.tvd_m),ns_m:lerp(a.ns_m,b.ns_m),ew_m:lerp(a.ew_m,b.ew_m),tvdss_m:a.tvdss_m==null||b.tvdss_m==null?null:lerp(a.tvdss_m,b.tvdss_m),inclination_deg:a.inclination_deg,azimuth_deg:a.azimuth_deg };
}
function finite(v: unknown): number | null { const n = typeof v==='number'?v:Number(v); return v == null || !Number.isFinite(n)?null:n; }

function SceneContents(props: Props) {
  const active = props.active;
  const selectedSet = new Set([active?.well_id, props.selectedId].filter(Boolean));
  const activeData = active ? props.data.get(active.well_id) : undefined;
  const ranked = active ? rankedOffsetsWithinRadius(active,props.wells,activeData?.offsets??[],props.radiusKm) : [];
  const ids = [active?.well_id, props.selectedId, ...ranked.map(o=>o.well_id)].filter((v,i,a):v is string=>!!v&&a.indexOf(v)===i).slice(0,5);
  const activeStations=activeData?.trajectory?.stations??[];
  const target=React.useMemo(()=>{
    if(!active||!activeStations.length)return new THREE.Vector3(0,-12,0);
    const points = ids.flatMap(id => {
      const well = props.wells.find(item => item.well_id === id);
      const stations = props.data.get(id)?.trajectory?.stations ?? [];
      if (!well) return [];
      return stations.map(station => stationToFieldPoint(station, active, well)).filter((p): p is NonNullable<typeof p> => p != null).map(p => new THREE.Vector3(p.x,p.y,p.z));
    });
    if (!points.length) return new THREE.Vector3(0,-12,0);
    const bounds = new THREE.Box3().setFromPoints(points);
    return bounds.getCenter(new THREE.Vector3());
  },[active,activeStations,ids.join('|'),props.wells,props.data]);
  const downholePoint = React.useMemo(() => {
    if (!active || activeStations.length < 2) return target;
    const middleStation = activeStations[Math.floor(activeStations.length * 0.55)];
    const station = props.evaluationDepthM == null
      ? middleStation
      : interpolateStation(activeStations, props.evaluationDepthM) ?? middleStation;
    const point = stationToFieldPoint(station, active, active);
    return point ? new THREE.Vector3(point.x, point.y, point.z) : target;
  }, [active, activeStations, props.evaluationDepthM, target]);
  const trajectoryExtent=React.useMemo(()=>{
    if(!active)return 8;
    return ids.reduce((max,id)=>{
      const well=props.wells.find(item=>item.well_id===id);
      const stations=props.data.get(id)?.trajectory?.stations??[];
      if(!well)return max;
      return stations.reduce((value,station)=>{
        const point=stationToFieldPoint(station,active,well);
        return point?Math.max(value,new THREE.Vector3(point.x,point.y,point.z).distanceTo(target)):value;
      },max);
    },0);
  },[active,ids.join('|'),props.wells,props.data,target]);
  const scenePoints=React.useMemo(()=>ids.flatMap(id=>{
    const well=props.wells.find(item=>item.well_id===id);
    const stations=props.data.get(id)?.trajectory?.stations??[];
    return well?stations.map(station=>stationToFieldPoint(station,active??well,well)).filter((p):p is NonNullable<typeof p>=>p!=null).map(p=>new THREE.Vector3(p.x,p.y,p.z)):[];
  }),[active,ids.join('|'),props.wells,props.data]);

  return <>
    <color attach="background" args={['#10161c']} />
    <fog attach="fog" args={['#10161c', props.stage==='subsurface'?260:400, props.stage==='subsurface'?1200:1500]} />
    <ambientLight intensity={1.25}/><directionalLight position={[-60,90,50]} intensity={2.1} color="#ffe8d2"/><hemisphereLight args={['#d0e0e5','#172128',0.7]}/>
    <CameraJourney stage={props.stage} target={target} downholePoint={downholePoint} radiusKm={props.radiusKm} trajectoryExtent={trajectoryExtent}/>
    {props.stage==='global' && <>
      <mesh><sphereGeometry args={[100,64,48]}/><meshStandardMaterial color="#203744" roughness={0.86} metalness={0.04}/></mesh>
      <mesh><sphereGeometry args={[100.35,32,20]}/><meshBasicMaterial color="#7d999f" wireframe transparent opacity={0.13}/></mesh>
      {props.wells.filter(w=>w.latitude!=null&&w.longitude!=null).map(w=>{
        const lat=w.latitude!*Math.PI/180,lon=w.longitude!*Math.PI/180;const p=new THREE.Vector3(-Math.cos(lat)*Math.cos(lon),Math.sin(lat),Math.cos(lat)*Math.sin(lon)).multiplyScalar(101);
        return <ClickTarget key={w.well_id} wellId={w.well_id} onSelect={props.onSelect} onSelectObject={props.onSelectObject} type="well" label={w.well_id}><mesh position={p}><sphereGeometry args={[w.well_id===active?.well_id?2.7:1.8,16,12]}/><meshBasicMaterial color={w.well_id===active?.well_id?color.active:color.offset}/></mesh></ClickTarget>;
      })}
    </>}
    {props.stage==='field' && active && <>
      <gridHelper args={[Math.max(40,props.radiusKm*1000*unit*2),24,'#536069','#28333b']} position={[0,-0.04,0]}/>
      <mesh rotation={[-Math.PI/2,0,0]} position={[0,-0.1,0]}><circleGeometry args={[props.radiusKm*1000*unit,96]}/><meshBasicMaterial color="#63aaa0" transparent opacity={0.08} side={THREE.DoubleSide} depthWrite={false}/></mesh>
      <mesh rotation={[-Math.PI/2,0,0]} position={[0,-0.04,0]}><ringGeometry args={[props.radiusKm*1000*unit-0.12,props.radiusKm*1000*unit,96]}/><meshBasicMaterial color="#83c8bb" transparent opacity={0.75} side={THREE.DoubleSide}/></mesh>
      <mesh position={[0,0,0]}><sphereGeometry args={[0.9,16,12]}/><meshBasicMaterial color={color.active}/></mesh>
      {nearbyWells(active,props.wells,props.radiusKm).map(({well:w,distanceKm:d})=>{
        const enu=wellheadENU(active,w);if(!enu)return null;
        const selected=w.well_id===props.selectedId;return <ClickTarget key={w.well_id} wellId={w.well_id} onSelect={props.onSelect} onSelectObject={props.onSelectObject} type="well" label={`${w.well_id} · ${d.toFixed(2)} km`}><mesh position={[enu.eastM*unit,0.3,enu.northM*unit]}><sphereGeometry args={[selected?0.85:0.55,16,12]}/><meshStandardMaterial color={selected?color.selected:color.offset} emissive={selected?color.selected:color.offset} emissiveIntensity={0.15}/></mesh><Html position={[enu.eastM*unit+0.9,1.3,enu.northM*unit]} center={false} distanceFactor={22} style={{pointerEvents:'none'}}><span className="world-label">{w.well_id}</span></Html></ClickTarget>;
      })}
      <Html position={[0,0.2,props.radiusKm*1000*unit+2]} center distanceFactor={22} style={{pointerEvents:'none'}}><span className="world-label muted">{`SURFACE-DISTANCE SEARCH · ${props.radiusKm} KM`}</span></Html>
    </>}
    {props.stage==='subsurface' && <>
      {active && <>
        {/* Keep the deep scene tied to the surface wellhead, but avoid drawing
            the kilometre-scale search radius as a giant underground grid. */}
        <Line points={[[-8,0,0],[8,0,0]]} color="#83949a" lineWidth={1} transparent opacity={0.42}/>
        <Line points={[[0,0,-8],[0,0,8]]} color="#83949a" lineWidth={1} transparent opacity={0.42}/>
        <mesh position={[0,0.18,0]}><sphereGeometry args={[0.38,16,12]}/><meshBasicMaterial color={color.active}/></mesh>
        <Html position={[0,1.15,0]} center distanceFactor={20} style={{pointerEvents:'none'}}><span className="world-label muted">ACTIVE WELLHEAD · SURFACE DATUM</span></Html>
        {activeData?.trajectory&&<SubsurfaceSectionBackdrop points={scenePoints} activeData={activeData}/>}
        {ids.map((id,index)=>{
          const well=props.wells.find(w=>w.well_id===id) ?? (id===active.well_id?active:null);if(!well)return null;
          const wellData=props.data.get(id);if(!wellData?.trajectory)return null;
          const rank=ranked.findIndex(o=>o.well_id===id);return <Trajectory key={id} well={well} active={active} data={wellData} selected={selectedSet.has(id)} rank={rank} props={props}/>;
        })}
        {activeData?.trajectory && active && <ActiveTvdScale data={activeData} well={active} active={active} />}
        {activeData && !activeData.trajectory && <Html position={[0,-9,0]} center distanceFactor={22} style={{pointerEvents:'none'}}><span className="world-label muted">{`No survey trajectory is available for ${active.well_id}.`}</span></Html>}
      </>}
    </>}
  </>;
}

export function Scene3D(props: Props) {
  return <div className="scene-host" aria-label={`${props.stage} spatial visualization`}>
    <Canvas camera={{ position: [0,0,345], fov: 45, near: 0.05, far: 15000 }} dpr={[1,1.5]} gl={{ antialias: true, powerPreference: 'high-performance' }}>
      <SceneContents {...props}/>
    </Canvas>
  </div>;
}
