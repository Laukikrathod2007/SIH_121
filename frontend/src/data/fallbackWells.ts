import { MapWell, OffsetWellRanking } from '../types';
import { haversineKm } from '../lib/globeGeometry';

export const FALLBACK_MAP_WELLS: MapWell[] = [
  {
    well_id: 'WELL-NHK-001',
    well_name: 'NHK-001',
    field: 'Nahorkatiya',
    lat: 27.149183,
    lon: 95.292326,
    status: 'PRODUCING',
    well_type: 'J-Type',
    total_depth_md_m: 2820.0,
    total_events: 5,
    is_active: true,
  },
  {
    well_id: 'WELL-NHK-002',
    well_name: 'NHK-002',
    field: 'Nahorkatiya',
    lat: 27.260229,
    lon: 95.291487,
    status: 'COMPLETED',
    well_type: 'J-Type',
    total_depth_md_m: 3244.0,
    total_events: 3,
    is_active: false,
  },
  {
    well_id: 'WELL-NHK-003',
    well_name: 'NHK-003',
    field: 'Nahorkatiya',
    lat: 27.152943,
    lon: 95.406274,
    status: 'SUSPENDED',
    well_type: 'Vertical',
    total_depth_md_m: 3461.0,
    total_events: 2,
    is_active: false,
  },
  {
    well_id: 'WELL-MRN-004',
    well_name: 'MRN-004',
    field: 'Moran',
    lat: 27.037065,
    lon: 94.981018,
    status: 'ABANDONED',
    well_type: 'Vertical',
    total_depth_md_m: 3108.0,
    total_events: 4,
    is_active: false,
  },
  {
    well_id: 'WELL-MRN-005',
    well_name: 'MRN-005',
    field: 'Moran',
    lat: 27.088685,
    lon: 94.984708,
    status: 'SUSPENDED',
    well_type: 'S-Type',
    total_depth_md_m: 3490.0,
    total_events: 1,
    is_active: false,
  },
  {
    well_id: 'WELL-MRN-006',
    well_name: 'MRN-006',
    field: 'Moran',
    lat: 27.078776,
    lon: 95.047567,
    status: 'COMPLETED',
    well_type: 'Vertical',
    total_depth_md_m: 2949.0,
    total_events: 3,
    is_active: false,
  },
  {
    well_id: 'WELL-BGJ-007',
    well_name: 'BGJ-007',
    field: 'Baghjan',
    lat: 27.486087,
    lon: 95.393323,
    status: 'COMPLETED',
    well_type: 'Vertical',
    total_depth_md_m: 3064.0,
    total_events: 6,
    is_active: false,
  },
  {
    well_id: 'WELL-BGJ-008',
    well_name: 'BGJ-008',
    field: 'Baghjan',
    lat: 27.600434,
    lon: 95.312772,
    status: 'ABANDONED',
    well_type: 'Vertical',
    total_depth_md_m: 3296.0,
    total_events: 2,
    is_active: false,
  },
  {
    well_id: 'WELL-BGJ-009',
    well_name: 'BGJ-009',
    field: 'Baghjan',
    lat: 27.607952,
    lon: 95.283917,
    status: 'SUSPENDED',
    well_type: 'S-Type',
    total_depth_md_m: 3160.0,
    total_events: 3,
    is_active: false,
  },
  {
    well_id: 'WELL-HGJ-010',
    well_name: 'HGJ-010',
    field: 'Hugrijan',
    lat: 27.277859,
    lon: 94.738453,
    status: 'SUSPENDED',
    well_type: 'Vertical',
    total_depth_md_m: 2882.0,
    total_events: 1,
    is_active: false,
  },
  {
    well_id: 'WELL-HGJ-011',
    well_name: 'HGJ-011',
    field: 'Hugrijan',
    lat: 27.202888,
    lon: 94.750397,
    status: 'ABANDONED',
    well_type: 'Vertical',
    total_depth_md_m: 2843.0,
    total_events: 0,
    is_active: false,
  },
  {
    well_id: 'WELL-HGJ-012',
    well_name: 'HGJ-012',
    field: 'Hugrijan',
    lat: 27.274571,
    lon: 94.723159,
    status: 'COMPLETED',
    well_type: 'J-Type',
    total_depth_md_m: 2838.0,
    total_events: 8,
    is_active: false,
  },
];

export function computeLocalDorsRankings(
  centerWellId: string,
  wells: MapWell[],
  _radiusKm: number
): OffsetWellRanking[] {
  const center = wells.find((w) => w.well_id === centerWellId) ?? wells[0];
  if (!center) return [];

  const offsets = wells
    .filter((w) => w.well_id !== center.well_id)
    .map((w) => {
      const dist = haversineKm(center.lat, center.lon, w.lat, w.lon);
      const distScore = Math.max(0.1, Math.exp(-dist / 35));
      const depthDiff = Math.abs(center.total_depth_md_m - w.total_depth_md_m);
      const depthScore = Math.max(0.2, 1 - depthDiff / 4000);
      const fieldMatch = center.field === w.field ? 1.0 : 0.5;
      const dorsScore = +(distScore * 0.45 + depthScore * 0.35 + fieldMatch * 0.2).toFixed(2);

      return {
        rank: 1,
        well_id: w.well_id,
        well_name: w.well_name,
        field: w.field,
        well_type: w.well_type,
        distance_km: +dist.toFixed(1),
        dors_score: dorsScore,
        formation_match: center.field === w.field ? 'High' : 'Moderate',
        events_in_lookahead: w.total_events,
        component_scores: {
          spatial: +distScore.toFixed(2),
          formation: +depthScore.toFixed(2),
          depth: +(1 - depthDiff / 5000).toFixed(2),
          trajectory: 0.88,
          hazard: 0.75,
          total: dorsScore,
          distance_km: +dist.toFixed(1),
          structural_fault_status: center.field === w.field ? 'SAME_FAULT_BLOCK' : 'POSSIBLE_FAULT_BOUNDARY',
        },
      } as OffsetWellRanking;
    });

  const sorted = offsets.sort((a, b) => b.dors_score - a.dors_score);
  return sorted.map((o, idx) => ({ ...o, rank: idx + 1 }));
}
