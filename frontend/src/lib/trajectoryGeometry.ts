import * as THREE from 'three';
import { SurveyStation } from '../types';

// Shared by every 3D/cutaway component that renders a real wellbore
// (LiveDrillingScene3D, WellTrajectory3D, WellCutawayCockpit, CommandCenterPage).
// Previously reimplemented independently in each of those 3 files with
// near-identical logic -- found during the visualization audit and
// extracted here so a future change to the coordinate convention only
// needs to happen once.
//
// Three.js is Y-up; TVD (positive downward in the real data) maps to -Y.
// Real NS/EW horizontal displacement (from the real minimum-curvature
// computation) maps to X/Z directly. SCALE only rescales for a workable
// camera distance -- it does not distort real proportions between wells.
export const TRAJECTORY_SCALE = 0.02;

export function stationToVec3(s: SurveyStation, scale: number = TRAJECTORY_SCALE): THREE.Vector3 {
  return new THREE.Vector3(s.ew_m * scale, -s.tvd_m * scale, s.ns_m * scale);
}

/** Interpolate a real 3D scene position along the trajectory at an arbitrary MD. */
export function positionAtMD(
  stations: SurveyStation[],
  md: number,
  scale: number = TRAJECTORY_SCALE,
): THREE.Vector3 | null {
  if (stations.length === 0) return null;
  if (md <= stations[0].md_m) return stationToVec3(stations[0], scale);
  for (let i = 0; i < stations.length - 1; i++) {
    const a = stations[i];
    const b = stations[i + 1];
    if (md >= a.md_m && md <= b.md_m) {
      const span = b.md_m - a.md_m;
      const t = span > 0 ? (md - a.md_m) / span : 0;
      return stationToVec3(a, scale).lerp(stationToVec3(b, scale), t);
    }
  }
  return stationToVec3(stations[stations.length - 1], scale);
}

/** Interpolate the full real survey station (not just position) at an arbitrary MD. */
export function stationAtMD(stations: SurveyStation[], md: number): SurveyStation | null {
  if (stations.length === 0) return null;
  if (md <= stations[0].md_m) return stations[0];
  for (let i = 0; i < stations.length - 1; i++) {
    const a = stations[i];
    const b = stations[i + 1];
    if (md >= a.md_m && md <= b.md_m) {
      const span = b.md_m - a.md_m;
      const t = span > 0 ? (md - a.md_m) / span : 0;
      return {
        md_m: md,
        inclination_deg: a.inclination_deg + (b.inclination_deg - a.inclination_deg) * t,
        azimuth_deg: a.azimuth_deg,
        tvd_m: a.tvd_m + (b.tvd_m - a.tvd_m) * t,
        ns_m: a.ns_m + (b.ns_m - a.ns_m) * t,
        ew_m: a.ew_m + (b.ew_m - a.ew_m) * t,
        tvdss_m: a.tvdss_m + (b.tvdss_m - a.tvdss_m) * t,
      };
    }
  }
  return stations[stations.length - 1];
}
