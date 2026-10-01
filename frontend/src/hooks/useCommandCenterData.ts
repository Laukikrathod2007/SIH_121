import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../services/api';
import {
  WellTrajectory, FormationTop, DrillingEvent, TelemetryRecord,
  NWISAnalysisResponse, OffsetWellRanking, CasingRecord, AheadOfBitCorridor,
} from '../types';

// Real-data source for the command-center view, deliberately independent
// of AppContext's telemetry/activeDepth -- those are bound to Module 03
// (the physics digital twin), which has no backend at all (see
// services/api.ts's own "NOT YET WIRED" comments). Everything here comes
// from Module 02, which is real: trajectory (now that the route exists),
// analyzeWell (real DORS + hazard assessments, previously called nowhere
// in the app), and depth-indexed replayed telemetry (getTelemetryRecords,
// also previously called nowhere).
//
// Depth is a manually-scrubbed value, not a live clock -- there is no real
// live rig feed to follow, and presenting a fixed-interval timer as "live"
// would repeat the exact mislabeling this whole engagement has avoided
// elsewhere (see the competitor audit: several other teams' "real-time"
// telemetry is just this same pattern, unlabeled).

const ANALYZE_DEPTH_BUCKET_M = 20; // matches NearbyWellsPage's existing bucketing pattern

export interface CommandCenterData {
  trajectory: WellTrajectory | null;
  trajectoryLoading: boolean;
  formations: FormationTop[];
  events: DrillingEvent[];
  depth: number;
  setDepth: (d: number) => void;
  minDepth: number;
  maxDepth: number;
  analysis: NWISAnalysisResponse | null;
  analysisLoading: boolean;
  telemetry: TelemetryRecord | null;
  offsetWell: OffsetWellRanking | null;
  offsetTrajectory: WellTrajectory | null;
  offsetEvents: DrillingEvent[];
  casing: CasingRecord[];
  aheadOfBit: AheadOfBitCorridor | null;
  aheadOfBitLoading: boolean;
}

export function useCommandCenterData(wellId: string, radiusKm: number = 25): CommandCenterData {
  const [trajectory, setTrajectory] = useState<WellTrajectory | null>(null);
  const [trajectoryLoading, setTrajectoryLoading] = useState(true);
  const [formations, setFormations] = useState<FormationTop[]>([]);
  const [events, setEvents] = useState<DrillingEvent[]>([]);
  const [depth, setDepth] = useState<number>(0);
  const [analysis, setAnalysis] = useState<NWISAnalysisResponse | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [telemetry, setTelemetry] = useState<TelemetryRecord | null>(null);
  const [offsetTrajectory, setOffsetTrajectory] = useState<WellTrajectory | null>(null);
  const [offsetEvents, setOffsetEvents] = useState<DrillingEvent[]>([]);
  const [casing, setCasing] = useState<CasingRecord[]>([]);
  const [aheadOfBit, setAheadOfBit] = useState<AheadOfBitCorridor | null>(null);
  const [aheadOfBitLoading, setAheadOfBitLoading] = useState(false);

  const minDepth = trajectory?.stations[0]?.md_m ?? 0;
  const maxDepth = trajectory?.stations[trajectory.stations.length - 1]?.md_m ?? 4000;

  // 1. Trajectory + formations + events for the active well (fetched once
  // per well change, not per depth change -- these are static per well).
  useEffect(() => {
    let cancelled = false;
    setTrajectoryLoading(true);
    Promise.all([
      api.getTrajectory(wellId).catch(() => null),
      api.getFormations(wellId).catch(() => []),
      api.getWellEvents(wellId).catch(() => []),
      api.getCasing(wellId).catch(() => []),
    ]).then(([traj, forms, evts, casingRecords]) => {
      if (cancelled) return;
      setTrajectory(traj);
      setFormations(forms);
      setEvents(evts);
      setCasing(casingRecords);
      setTrajectoryLoading(false);
      if (traj && traj.stations.length > 0) {
        const deepest = traj.stations[traj.stations.length - 1].md_m;
        // Default to 70% down the real trajectory -- a depth where
        // something has usually happened, not the surface.
        setDepth(Math.round(deepest * 0.7));
      }
    });
    return () => { cancelled = true; };
  }, [wellId]);

  // 2. Full orchestrated analysis (DORS + hazard assessments + corridors),
  // bucketed by depth so scrubbing doesn't fire a request per pixel.
  const depthBucket = Math.floor(depth / ANALYZE_DEPTH_BUCKET_M);
  useEffect(() => {
    if (!trajectory) return;
    let cancelled = false;
    setAnalysisLoading(true);
    api.analyzeWell(wellId, depth, radiusKm).then((res) => {
      if (cancelled) return;
      setAnalysis(res);
      setAnalysisLoading(false);
    }).catch(() => {
      if (cancelled) return;
      setAnalysis(null);
      setAnalysisLoading(false);
    });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wellId, depthBucket, radiusKm, !!trajectory]);

  // 3. Real depth-indexed telemetry (Module 02, not Module 03). Real bug
  // found while wiring this: the backend's get_telemetry_at() ignores
  // well_id entirely and always returns the synthetic testbed's one
  // telemetry-equipped well (WELL-HGJ-012) -- a pre-existing limitation
  // (the synthetic dataset only ever generated telemetry for one well),
  // not something introduced here. The response's outer well_id field
  // echoes back whatever was requested, but the actual record's own
  // well_id reveals which well the data really belongs to. Rather than
  // silently show WELL-HGJ-012's telemetry mislabeled as the selected
  // well's, only accept it when the record's own well_id genuinely
  // matches.
  useEffect(() => {
    if (!trajectory) return;
    let cancelled = false;
    api.getTelemetryRecords(wellId, depth, 1).then((res) => {
      if (cancelled) return;
      const rec = res.latest && res.latest.well_id === wellId ? res.latest : null;
      setTelemetry(rec);
    }).catch(() => {
      if (cancelled) return;
      setTelemetry(null);
    });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wellId, depthBucket, !!trajectory]);

  // 4. Ahead-of-bit projected risk density (0-200m ahead), bucketed by depth
  // same as analysis above. Real endpoint, zero prior frontend consumer.
  useEffect(() => {
    if (!trajectory) return;
    let cancelled = false;
    setAheadOfBitLoading(true);
    api.getAheadOfBit(wellId, depth).then((res) => {
      if (cancelled) return;
      setAheadOfBit(res);
      setAheadOfBitLoading(false);
    }).catch(() => {
      if (cancelled) return;
      setAheadOfBit(null);
      setAheadOfBitLoading(false);
    });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wellId, depthBucket, !!trajectory]);

  // 5. Top DORS offset well's real trajectory, if it has one (many offset
  // ranks are synthetic wells with no real survey data -- that's fine,
  // just no 3D offset trajectory to draw for those).
  const offsetWell = analysis?.offset_rankings?.[0] ?? null;
  useEffect(() => {
    if (!offsetWell) {
      setOffsetTrajectory(null);
      setOffsetEvents([]);
      return;
    }
    let cancelled = false;
    api.getTrajectory(offsetWell.well_id).then((t) => {
      if (!cancelled) setOffsetTrajectory(t);
    }).catch(() => {
      if (!cancelled) setOffsetTrajectory(null);
    });
    api.getWellEvents(offsetWell.well_id).then((evts) => {
      if (!cancelled) setOffsetEvents(evts);
    }).catch(() => {
      if (!cancelled) setOffsetEvents([]);
    });
    return () => { cancelled = true; };
  }, [offsetWell?.well_id]);

  const setDepthClamped = useCallback((d: number) => {
    setDepth(Math.max(minDepth, Math.min(maxDepth, d)));
  }, [minDepth, maxDepth]);

  return useMemo(() => ({
    trajectory, trajectoryLoading, formations, events,
    depth, setDepth: setDepthClamped, minDepth, maxDepth,
    analysis, analysisLoading, telemetry, offsetWell, offsetTrajectory, offsetEvents,
    casing, aheadOfBit, aheadOfBitLoading,
  }), [trajectory, trajectoryLoading, formations, events, depth, setDepthClamped,
      minDepth, maxDepth, analysis, analysisLoading, telemetry, offsetWell, offsetTrajectory, offsetEvents,
      casing, aheadOfBit, aheadOfBitLoading]);
}
