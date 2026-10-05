import * as THREE from 'three';
import type { SurveyStation } from './data-contract';

export interface Point3 { x: number; y: number; z: number }

/** NWIS/visualization frame: east, down-positive TVD, north; scale 0.02. */
export function stationToVec3(station: SurveyStation): THREE.Vector3 {
  return new THREE.Vector3(station.ew_m * 0.02, -station.tvd_m * 0.02, station.ns_m * 0.02);
}

export function surveyPoint(station: SurveyStation): Point3 {
  const p = stationToVec3(station);
  return { x: p.x, y: p.y, z: p.z };
}

export function positionAtMD(stations: SurveyStation[], md: number): Point3 | null {
  if (!stations.length || !Number.isFinite(md)) return null;
  const ordered = [...stations].sort((a, b) => a.md_m - b.md_m);
  if (md < ordered[0].md_m || md > ordered[ordered.length - 1].md_m) return null;
  let index = 1;
  while (index < ordered.length && ordered[index].md_m < md) index++;
  const a = ordered[index - 1], b = ordered[Math.min(index, ordered.length - 1)];
  const t = b.md_m === a.md_m ? 0 : (md - a.md_m) / (b.md_m - a.md_m);
  const pa = stationToVec3(a), pb = stationToVec3(b);
  return { x: THREE.MathUtils.lerp(pa.x, pb.x, t), y: THREE.MathUtils.lerp(pa.y, pb.y, t), z: THREE.MathUtils.lerp(pa.z, pb.z, t) };
}

export function trajectoryLine(stations: SurveyStation[]): THREE.Vector3[] {
  return stations.map(stationToVec3);
}
