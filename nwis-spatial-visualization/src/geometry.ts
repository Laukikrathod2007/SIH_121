import type { FormationObservation, Well } from './data-contract';
export { positionAtMD, stationToVec3, surveyPoint, trajectoryLine } from './trajectoryGeometry';
export { fieldXY, formatDistanceKm, haversineKm, nearbyWells, rankedOffsetsWithinRadius, wellheadENU, stationToFieldPoint, SCENE_METRES_TO_UNITS } from './spatialFrame';

export type { Point3 } from './trajectoryGeometry';

// NWIS renderer contract: x=east, y=negative TVD (down), z=north.
export function normalizedFormationName(f: FormationObservation): string {
  return String(f.formation ?? f.formation_name ?? f.name ?? 'Formation');
}

export function formationMD(f: FormationObservation): number | null {
  for (const k of ['depth_top_md_m', 'top_md_m', 'depth_md_m', 'md_m']) {
    const v = f[k]; if (typeof v === 'number' && Number.isFinite(v)) return v;
  }
  return null;
}
