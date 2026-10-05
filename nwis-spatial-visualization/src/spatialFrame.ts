import type { SurveyStation, Well } from './data-contract';
import type { Point3 } from './trajectoryGeometry';

/**
 * Shared local field frame. Origin is the active wellhead; units are metres
 * before the renderer's uniform 0.02 scene scale. X=east, Y=up, Z=north.
 * Wellhead offsets use a local equirectangular ENU approximation at the active
 * latitude. Survey EW/NS offsets are added in that well's own local frame.
 * TVD is positive down and is kept relative to each wellhead: it is not a
 * cross-well TVD/TVDSS correlation unless a common vertical datum is supplied.
 */
export const SCENE_METRES_TO_UNITS = 0.02;
export interface SpatialFramePoint extends Point3 { x: number; y: number; z: number }

export function wellheadENU(active: Well, well: Well): { eastM: number; northM: number } | null {
  if (![active.latitude, active.longitude, well.latitude, well.longitude].every(v => typeof v === 'number' && Number.isFinite(v))) return null;
  const lat0 = active.latitude as number;
  const eastM = ((well.longitude as number) - (active.longitude as number)) * 111_320 * Math.cos(lat0 * Math.PI / 180);
  const northM = ((well.latitude as number) - lat0) * 110_574;
  return { eastM, northM };
}

export function haversineKm(a: Well, b: Well): number | null {
  if (![a.latitude,a.longitude,b.latitude,b.longitude].every(v=>typeof v==='number'&&Number.isFinite(v))) return null;
  const r=Math.PI/180,latA=a.latitude!*r,latB=b.latitude!*r,dLat=(b.latitude!-a.latitude!)*r,dLon=(b.longitude!-a.longitude!)*r;
  const h=Math.sin(dLat/2)**2+Math.cos(latA)*Math.cos(latB)*Math.sin(dLon/2)**2;
  return 6371*2*Math.atan2(Math.sqrt(h),Math.sqrt(1-h));
}

/** Keep very close verified wellheads distinguishable from a true zero distance. */
export function formatDistanceKm(distanceKm: number): string {
  return distanceKm < 0.1 ? distanceKm.toFixed(3) : distanceKm.toFixed(1);
}

export function fieldXY(active: Well, well: Well): { x: number; y: number } | null {
  const point=wellheadENU(active,well);return point?{x:point.eastM/1000,y:point.northM/1000}:null;
}

/** Coordinates are authoritative for the gate; DORS metadata only orders survivors. */
export function rankedOffsetsWithinRadius<T extends { well_id: string; dors_score?: number | null; component_scores?: { total?: number | null } }>(active: Well, wells: Well[], offsets: T[], radiusKm: number): T[] {
  const byId=new Map(wells.map(w=>[w.well_id,w]));
  return offsets.flatMap(offset=>{
    const candidate=byId.get(offset.well_id),distance=candidate?haversineKm(active,candidate):null;
    return distance!=null&&distance<=radiusKm?[offset]:[];
  }).sort((a,b)=>(b.dors_score??b.component_scores?.total??-Infinity)-(a.dors_score??a.component_scores?.total??-Infinity));
}

export function nearbyWells(active: Well, wells: Well[], radiusKm: number): Array<{well:Well;distanceKm:number}> {
  return wells.flatMap(w=>{if(w.well_id===active.well_id)return[];const distanceKm=haversineKm(active,w);return distanceKm!=null&&distanceKm<=radiusKm?[{well:w,distanceKm}]:[];}).sort((a,b)=>a.distanceKm-b.distanceKm);
}

export function stationToFieldPoint(station: SurveyStation, active: Well, well: Well): SpatialFramePoint | null {
  const head = wellheadENU(active, well);
  // A single active trajectory can still be explored in its own local frame
  // when its verified wellhead location is absent. Unlocated offsets are never
  // placed arbitrarily into the shared multi-well frame.
  if (!head) {
    if (active.well_id !== well.well_id) return null;
    return { x: station.ew_m * SCENE_METRES_TO_UNITS, y: -station.tvd_m * SCENE_METRES_TO_UNITS, z: station.ns_m * SCENE_METRES_TO_UNITS };
  }
  return {
    x: (head.eastM + station.ew_m) * SCENE_METRES_TO_UNITS,
    y: -station.tvd_m * SCENE_METRES_TO_UNITS,
    z: (head.northM + station.ns_m) * SCENE_METRES_TO_UNITS,
  };
}
