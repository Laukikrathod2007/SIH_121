import { describe, expect, it, vi } from 'vitest';
import { readFile } from 'node:fs/promises';
import { realVolveTrajectoryProvider } from './realVolveTrajectoryProvider';
import { nwisLiveProvider } from './nwisLiveProvider';
import { loadVisualizationWellData } from './VisualizationDataProvider';
import { haversineKm, nearbyWells, rankedOffsetsWithinRadius, stationToFieldPoint } from './spatialFrame';
import { stationToVec3 } from './trajectoryGeometry';
import type { Offset3DDataProvider, VisualizationWell } from './data-contract';

const active: VisualizationWell = { well_id:'WELL-HGJ-012', name:'Active', latitude:20, longitude:80, source:'NWIS_TESTBED_SYNTHETIC' };
const near: VisualizationWell = { well_id:'WELL-HGJ-011', name:'Near', latitude:20.01, longitude:80, source:'NWIS_TESTBED_SYNTHETIC' };
const far: VisualizationWell = { well_id:'WELL-HGJ-010', name:'Far', latitude:20.04, longitude:80, source:'NWIS_TESTBED_SYNTHETIC' };

describe('shared spatial frame and radius', () => {
  it('uses measured coordinates for distance and excludes unknown/far wells', () => {
    expect(haversineKm(active, near)).toBeCloseTo(1.112, 2);
    expect(nearbyWells(active, [active, near, far, {well_id:'unknown',name:'Unknown',source:active.source}], 1.2).map(x=>x.well.well_id)).toEqual([near.well_id]);
  });
  it('applies the real-coordinate radius gate before ordering by returned DORS', () => {
    const offsets=[{well_id:far.well_id,dors_score:99,distance_km:0.1},{well_id:near.well_id,dors_score:60,distance_km:99}];
    expect(rankedOffsetsWithinRadius(active,[active,near,far],offsets,1.2).map(x=>x.well_id)).toEqual([near.well_id]);
  });
  it('keeps the survey convention E / negative TVD / N at a uniform scale', () => {
    const point=stationToVec3({md_m:100,inclination_deg:0,azimuth_deg:0,tvd_m:90,ns_m:30,ew_m:40,tvdss_m:80});
    expect(point.toArray()).toEqual([0.8,-1.8,0.6]);
  });
  it('allows one unlocated active survey in its local frame, but never invents an offset placement', () => {
    const unlocated={well_id:'WELL-15_9-F-10',name:'Volve',source:'VOLVE_SURVEY' as const};
    const station={md_m:10,inclination_deg:0,azimuth_deg:0,tvd_m:9,ns_m:3,ew_m:4,tvdss_m:null};
    expect(stationToFieldPoint(station,unlocated,unlocated)).toEqual({x:0.08,y:-0.18,z:0.06});
    expect(stationToFieldPoint(station,active,unlocated)).toBeNull();
  });
});

describe('normalized provider and depth contracts', () => {
  it('loads the bundled Volve records with exact IDs and honest partial survey coverage', async () => {
    const dataset = await readFile(new URL('../public/data/volve/real_trajectories_witsml.json', import.meta.url), 'utf8');
    vi.stubGlobal('fetch', vi.fn(async () => new Response(dataset, { status: 200, headers: { 'Content-Type':'application/json' } })));
    const wells=await realVolveTrajectoryProvider.getWells();
    const f12=wells.find(w=>w.well_id==='WELL-15_9-F-12')!, f1=wells.find(w=>w.well_id==='WELL-15_9-F-1')!;
    const [t12,t1]=await Promise.all([realVolveTrajectoryProvider.getTrajectory!(f12.well_id),realVolveTrajectoryProvider.getTrajectory!(f1.well_id)]);
    expect(wells).toHaveLength(22);
    expect(t12?.stations).toHaveLength(438);
    expect(t1?.stations).toHaveLength(8);
    expect(t1?.stations.at(-1)?.md_m).toBeCloseTo(210.7,1);
    expect(t1?.coverage_status).toBe('partial');
    expect(t12?.source).toBe('VOLVE_SURVEY');
    expect(t12?.well_id).toBe('WELL-15_9-F-12');
    vi.unstubAllGlobals();
  });

  it('keeps evaluation depth separate from an explicitly queried telemetry depth', async () => {
    const spy=vi.fn();
    const provider: Offset3DDataProvider={
      source:'NWIS_TESTBED_SYNTHETIC', getWells:async()=>[active], getWell:async()=>active,
      getTrajectory:async()=>null, getFormations:async()=>[], getEvents:async()=>[], getCasing:async()=>[],
      getDorsOffsets:async(_id,_radius,md)=>{spy('dors',md);return[];},
      getHazards:async(_id,md)=>{spy('hazards',md);return[];},
      getTelemetryAtDepth:async(_id,md)=>{spy('telemetry',md);return[{well_id:active.well_id,measured_depth_m:md}];},
    };
    const result=await loadVisualizationWellData(provider,active,2350,5,undefined,true,2310);
    expect(spy.mock.calls).toEqual([['dors',2350],['hazards',2350],['telemetry',2310]]);
    expect(result.layers.trajectory.availability).toBe('unavailable');
    expect(result.layers.events.items).toEqual([]);
    expect(result.layers.events.availability).toBe('available');
    expect(result.layers.events.reason).toContain('no event records');
    expect(result.layers.telemetry.items).toHaveLength(1);
    expect(result.layerProvenance.events.isSynthetic).toBe(true);
  });

  it('keeps NWIS HGJ records isolated and scopes returned telemetry to the requested well', async () => {
    const requested: string[]=[];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url=String(input);requested.push(url);
      const body=url.endsWith('/wells')?{wells:[
        {well_id:'WELL-HGJ-012',well_name:'HGJ-012',surface_lat:20,surface_lon:80},
        {well_id:'WELL-15_9-F-12',well_name:'15/9-F-12',field:'Volve',surface_lat:58.4,surface_lon:1.8},
        {well_id:'WELL-OTHER-001',well_name:'Other'},
      ]}:{records:[{well_id:'WELL-HGJ-012',depth_m:2310},{well_id:'WELL-HGJ-011',depth_m:2310}]};
      return new Response(JSON.stringify(body),{status:200,headers:{'Content-Type':'application/json'}});
    }));
    const wells=await nwisLiveProvider.getWells();
    const telemetry=await nwisLiveProvider.getTelemetryAtDepth!('WELL-HGJ-012',2310);
    expect(wells.map(w=>w.well_id)).toEqual(['WELL-HGJ-012']);
    expect(wells[0].source).toBe('NWIS_TESTBED_SYNTHETIC');
    expect(telemetry.map(row=>row.measured_depth_m)).toEqual([2310]);
    expect(requested.at(-1)).toContain('depth=2310');
    vi.unstubAllGlobals();
  });
});
