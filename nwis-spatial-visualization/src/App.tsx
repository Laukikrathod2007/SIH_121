import * as React from 'react';
import { Activity, AlertCircle, ArrowDownRight, ArrowRight, CircleHelp, Compass, Crosshair, Database, Drill, Eye, Globe2, Layers3, LocateFixed, MapPin, Maximize2, RefreshCw, Search, ShieldAlert, Waypoints } from 'lucide-react';
import { visualizationDataProvider } from './dataProvider';
import { assamDocumentedLocationsProvider } from './assamDocumentedLocationsProvider';
import { realVolveTrajectoryProvider } from './realVolveTrajectoryProvider';
import { nwisLiveProvider } from './nwisLiveProvider';
import { loadVisualizationWellData } from './VisualizationDataProvider';
import { SurveyOverview } from './SurveyOverview';
import { formatDistanceKm, haversineKm, nearbyWells, rankedOffsetsWithinRadius } from './geometry';
import type { Offset3DDataProvider, OffsetScore, Stage, Well, WellData } from './data-contract';

const Scene3D = React.lazy(() => import('./Scene3D').then(module => ({ default: module.Scene3D })));
const CesiumEarth = React.lazy(() => import('./CesiumEarth').then(module => ({ default: module.CesiumEarth })));

type Health = { service?: string; status?: string; version?: string; data_store?: { loaded?: boolean; wells?: number; active_well_id?: string; [key: string]: unknown }; [key: string]: unknown };
const RADII = [1, 3, 5, 10];
const standaloneProviders: Record<string, Offset3DDataProvider> = {
  VOLVE_SURVEY: realVolveTrajectoryProvider,
  NWIS_TESTBED_SYNTHETIC: nwisLiveProvider,
  OIL_ASSAM_PUBLIC_LOCATIONS: assamDocumentedLocationsProvider,
};
const stageNames: Array<{ id: Stage; title: string; glyph: string }> = [
  { id: 'global', title: 'Global', glyph: '01' }, { id: 'field', title: 'Offset discovery', glyph: '02' }, { id: 'subsurface', title: 'Subsurface', glyph: '03' },
];
const number = (v: unknown) => typeof v === 'number' && Number.isFinite(v) ? v : null;
const format = (v: number | null | undefined, places = 1) => v == null ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: places });
const errText = (e: unknown) => e instanceof Error ? e.message : 'Unable to reach the configured data source.';

export interface AppProps { /** Host applications can inject their own backend adapter. */ provider?: Offset3DDataProvider }

export default function App({ provider: injectedProvider }: AppProps) {
  const [provider, setProvider] = React.useState<Offset3DDataProvider>(injectedProvider ?? visualizationDataProvider);
  React.useEffect(() => { if (injectedProvider) setProvider(injectedProvider); }, [injectedProvider]);
  const providerIsVolve = provider.source === 'VOLVE_SURVEY';
  const providerIsNwisDemo = provider.source === 'NWIS_TESTBED_SYNTHETIC';
  const providerIsAssam = provider.source === 'OIL_ASSAM_PUBLIC_LOCATIONS';
  const sourceDisplayName = providerIsVolve ? 'EQUINOR VOLVE · VERIFIED SURVEY'
    : providerIsNwisDemo ? 'NWIS TESTBED · SYNTHETIC'
      : providerIsAssam ? 'OIL ASSAM · PUBLIC WELL LOCATIONS' : provider.source.replaceAll('_', ' ');
  const sourceDescription = providerIsVolve ? 'Historical survey trajectories'
    : providerIsNwisDemo ? 'Demo well and operations records'
      : providerIsAssam ? 'Two named OIL well locations from a government environmental filing; coordinates only.'
        : 'Connected through the host application data adapter';
  const [wells, setWells] = React.useState<Well[]>([]);
  const [wellRecords, setWellRecords] = React.useState<Map<string, Well>>(new Map());
  const [wellData, setWellData] = React.useState<Map<string, WellData>>(new Map());
  const [activeId, setActiveId] = React.useState('');
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [radiusKm, setRadiusKm] = React.useState(5);
  const [evaluationDepthMd, setEvaluationDepthMd] = React.useState('');
  const [telemetryQueryMd, setTelemetryQueryMd] = React.useState('');
  const [stage, setStage] = React.useState<Stage>('global');
  const [sceneView, setSceneView] = React.useState<'orbit'|'plan'|'section'|'downhole'>('orbit');
  const [selectedObject, setSelectedObject] = React.useState<{type:string;wellId:string;depthM?:number;label:string}|null>(null);
  const [health, setHealth] = React.useState<Health | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [loadingWell, setLoadingWell] = React.useState(false);
  const [error, setError] = React.useState('');
  const [connected, setConnected] = React.useState(false);
  const [showLayers, setShowLayers] = React.useState({ formations: true, trajectories: true, events: true, hazards: true, casing: true });
  const [showKey, setShowKey] = React.useState(false);
  const [surfaceMode, setSurfaceMode] = React.useState<'satellite' | 'terrain' | 'photoreal' | 'fallback'>('satellite');
  const [wellSearch, setWellSearch] = React.useState('');
  const [keepSubsurfaceMounted, setKeepSubsurfaceMounted] = React.useState(false);
  const abortRef = React.useRef<AbortController | null>(null);
  const autoConnectProvider = React.useRef<Offset3DDataProvider | null>(null);

  const active = wellRecords.get(activeId) ?? wells.find(w => w.well_id === activeId) ?? null;
  const activeData = wellData.get(activeId);
  const ranked = activeData?.offsets ?? [];
  const scoreWellMap = React.useMemo(() => new Map(ranked.map(o => [o.well_id, o as Well])), [ranked]);
  const allWells = React.useMemo(() => {
    const merged = new Map(wells.map(w => [w.well_id, w]));
    for (const [id, w] of scoreWellMap) merged.set(id, { ...merged.get(id), ...w, well_id: id, name: String(w.name ?? merged.get(id)?.name ?? id) } as Well);
    return [...merged.values()];
  }, [wells, scoreWellMap]);
  const selectedWellForDistance = selectedId ? allWells.find(w => w.well_id === selectedId) ?? null : null;
  const selectedWell = selectedWellForDistance ?? (selectedId ? wellRecords.get(selectedId) ?? null : null);
  const selectedData = selectedId ? wellData.get(selectedId) : undefined;
  const activeOffsetDistanceKm = active && selectedWellForDistance ? haversineKm(active, selectedWellForDistance) : null;

  React.useEffect(() => {
    let cancelled = false;
    setHealth(null);
    if (!provider.getHealth) return () => { cancelled = true; };
    provider.getHealth().then(value => { if (!cancelled) setHealth(value as Health); }).catch(() => { if (!cancelled) setHealth(null); });
    return () => { cancelled = true; };
  }, [provider]);

  const connect = async () => {
    setBusy(true); setError('');
    try {
      const next = await provider.getWells();
      if (!next.length) throw new Error('The wells endpoint returned no well records.');
      const currentHealth = provider.getHealth
        ? await provider.getHealth().catch(() => null) as Health | null
        : null;
      if (currentHealth) setHealth(currentHealth);
      setWells(next); setWellRecords(new Map(next.map(w => [w.well_id, w]))); setConnected(true);
      const preferred = (provider.source === 'VOLVE_SURVEY' ? next.find(w => w.well_id === 'WELL-15_9-F-12') : undefined)
        ?? next.find(w => w.well_id === currentHealth?.data_store?.active_well_id) ?? next[0];
      const comparison = provider.source === 'VOLVE_SURVEY' ? next.find(w => w.well_id === 'WELL-15_9-F-1') : undefined;
      setActiveId(preferred.well_id); setSelectedId(comparison?.well_id ?? null); setWellData(new Map()); setStage('global');
    } catch (e) { setConnected(false); setError(errText(e)); }
    finally { setBusy(false); }
  };
  const connectRef = React.useRef(connect);
  connectRef.current = connect;

  // Load the configured provider on entry so the globe never opens as an
  // unpopulated shell. The source action remains available as a refresh.
  React.useEffect(() => {
    if (autoConnectProvider.current === provider) return;
    autoConnectProvider.current = provider;
    abortRef.current?.abort();
    setConnected(false); setHealth(null); setWells([]); setWellRecords(new Map()); setWellData(new Map());
    setActiveId(''); setSelectedId(null); setSelectedObject(null); setStage('global');
    void connectRef.current();
  }, [provider]);

  React.useEffect(() => {
    if (!connected || !active) return;
    abortRef.current?.abort(); const ctrl = new AbortController(); abortRef.current = ctrl;
    setLoadingWell(true); setError('');
    const queryMd = telemetryQueryMd.trim() === '' ? null : Number(telemetryQueryMd);
    const evaluationMd = evaluationDepthMd.trim() === '' ? null : Number(evaluationDepthMd);
    loadVisualizationWellData(provider, active, evaluationMd != null && Number.isFinite(evaluationMd) ? evaluationMd : null, radiusKm, ctrl.signal, true, queryMd != null && Number.isFinite(queryMd) ? queryMd : null).then(async data => {
      if (ctrl.signal.aborted) return;
      const nextMap = new Map(wellData); nextMap.set(active.well_id, data);
      const offsetWells = data.offsets.slice(0, 4).flatMap(o => {
        const w = allWells.find(x => x.well_id === o.well_id) ?? (o.latitude != null && o.longitude != null ? o as Well : null);
        return w ? [w] : [];
      });
      const selectedComparison = provider.source === 'VOLVE_SURVEY' && selectedId
        ? wells.find(w => w.well_id === selectedId) : undefined;
      const possible = selectedComparison ? [...offsetWells, selectedComparison] : offsetWells;
      const newOnes = possible.filter(w => !nextMap.has(w.well_id));
      setWellRecords(prev => { const n = new Map(prev); for (const w of possible) n.set(w.well_id, { ...n.get(w.well_id), ...w }); return n; });
      setWellData(nextMap);
      await Promise.all(newOnes.map(async w => {
        const d = await loadVisualizationWellData(provider, w, evaluationMd != null && Number.isFinite(evaluationMd) ? evaluationMd : null, radiusKm, ctrl.signal, false, null);
        if (!ctrl.signal.aborted) setWellData(prev => new Map(prev).set(w.well_id, d));
      }));
    }).catch(e => { if (!ctrl.signal.aborted) setError(errText(e)); }).finally(() => { if (!ctrl.signal.aborted) setLoadingWell(false); });
    return () => ctrl.abort();
    // wellData is intentionally omitted to prevent refetch loops; each response merges into current state.
  }, [connected, activeId, radiusKm, evaluationDepthMd, telemetryQueryMd, selectedId, provider]);

  const pick = (id: string) => {
    setSelectedObject(null);
    if (stage === 'global') { setActiveId(id); setSelectedId(null); setWellData(new Map()); setStage('field'); }
    else if (id === activeId) setSelectedId(null);
    else setSelectedId(id);
  };
  const pickActive = (id: string) => { setActiveId(id); setSelectedId(null); setSelectedObject(null); setWellData(new Map()); setStage('field'); };
  const selectedScore = selectedId ? ranked.find(o => o.well_id === selectedId) : undefined;
  const evaluationDepthValue = number(evaluationDepthMd);
  const selectedNearestEvent = evaluationDepthValue != null ? selectedData?.events.map(event => ({ event, md:number(event.depth_start_md_m) })).filter((x):x is {event:WellData['events'][number];md:number}=>x.md!=null).sort((a,b)=>Math.abs(a.md-evaluationDepthValue)-Math.abs(b.md-evaluationDepthValue))[0] : undefined;
  const activeStations = activeData?.trajectory?.stations ?? [];
  const firstSurveyStation = activeStations[0];
  const lastSurveyStation = activeStations.at(-1);
  const rangeText = (start?: number | null, end?: number | null) => start == null || end == null ? 'Unavailable' : `${format(start, 0)}–${format(end, 0)} m`;
  const scoreValue = (o?: OffsetScore) => number(o?.dors_score) ?? number(o?.component_scores?.total);
  const topVisible = active ? rankedOffsetsWithinRadius(active, allWells, ranked, radiusKm).slice(0,4) : [];
  const nearby = active ? nearbyWells(active, allWells, radiusKm) : [];
  const directoryWells = React.useMemo(() => {
    const query = wellSearch.trim().toLocaleLowerCase();
    return [...allWells].filter(w => !query || `${w.well_id} ${w.name} ${w.field ?? ''}`.toLocaleLowerCase().includes(query))
      .sort((a, b) => a.well_id.localeCompare(b.well_id));
  }, [allWells, wellSearch]);
  const locatedWellCount = allWells.filter(w => w.latitude != null && w.longitude != null).length;

  React.useEffect(() => {
    if (!connected || !active || !selectedId) return;
    const selected = allWells.find(w => w.well_id === selectedId);
    const distance = selected ? haversineKm(active, selected) : null;
    // Unknown coordinates cannot pass the real spatial-distance gate.
    if (distance == null || distance > radiusKm) {
      setSelectedId(null);
      setSelectedObject(null);
    }
  }, [connected, active, selectedId, radiusKm, allWells]);

  React.useEffect(() => {
    if (stage === 'subsurface') { setKeepSubsurfaceMounted(true); return; }
    if (!keepSubsurfaceMounted) return;
    const timer = window.setTimeout(() => setKeepSubsurfaceMounted(false), 1500);
    return () => window.clearTimeout(timer);
  }, [stage]);

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Drill size={19}/></div><span>NWIS<span className="brand-dot">.</span></span><i>SPATIAL INTELLIGENCE</i></div>
      <div className="top-status"><span className={`status-dot ${connected?'online':''}`} />{connected?'SPATIAL DATA READY':'DATA SOURCE NOT LOADED'}<span className="top-divider"/>{providerIsVolve?'LOCAL VERIFIED SURVEYS':health?.service ?? sourceDisplayName}{health?.version ? ` · v${health.version}` : ''}</div>
      <button className="icon-button" title="Toggle layer display" onClick={() => setShowLayers(v => ({ ...v, trajectories: !v.trajectories }))}><Layers3 size={16}/></button>
      <button className="icon-button" title="Help" onClick={() => setShowKey(v => !v)}><CircleHelp size={16}/></button>
    </header>

    <section className="command-head">
      <div><div className="eyebrow"><span className="live-pulse"/>{providerIsVolve?'EQUINOR VOLVE · VERIFIED SURVEY SOURCE':providerIsNwisDemo?'NWIS TESTBED · SYNTHETIC DEMONSTRATION':providerIsAssam?'OIL ASSAM · PUBLICLY DOCUMENTED LOCATIONS':`${sourceDisplayName} · DATA SOURCE`}</div><h1>Spatial context <span>for the wellpath.</span></h1><p>{providerIsVolve?'Explore verified survey geometry with honest location and coverage limits.':providerIsNwisDemo?'Explore synthetic NWIS demo wells, radius-filtered DORS offsets and source-backed depth context.':providerIsAssam?'Fly into publicly documented Assam well locations. Trajectories and operations data are unavailable in this source.':'Explore wells and engineering context supplied by the connected backend.'}</p></div>
      <div className="head-meta"><span>{providerIsVolve?'EQUINOR VOLVE · SURVEY DATA':providerIsNwisDemo?'NWIS TESTBED · DEMO DATA':sourceDisplayName}</span><b>{connected?'SOURCE READY':'SOURCE AVAILABLE'}</b></div>
    </section>

    <nav className="journey" aria-label="Visualization journey">{stageNames.map((item,i)=><React.Fragment key={item.id}><button className={`journey-step ${stage===item.id?'active':''} ${stageNames.findIndex(x=>x.id===stage)>i?'complete':''}`} onClick={()=>setStage(item.id)} disabled={!connected || (item.id==='subsurface'&&!active)}><span>{stage===item.id?<span className="journey-bullet"/>:item.glyph}</span><strong>{item.title}</strong></button>{i<2&&<div className="journey-line"/>}</React.Fragment>)}<div className="journey-tail">{active ? <><MapPin size={13}/>{active.well_id}</> : 'SELECT A WELL TO BEGIN'}</div></nav>

    <section className={`workspace ${stage==='subsurface'?'workspace-subsurface':''}`}>
      <aside className="control-column">
        <section className="panel connect-panel source-panel">
          <div className="panel-kicker"><Database size={14}/>DATA SOURCE</div>
          <div className="source-choice"><span className={`status-dot ${connected?'online':''}`}/><div><b>{sourceDisplayName}</b><small>{sourceDescription}</small></div><span className="source-tag">{connected?'READY':providerIsVolve?'LOCAL':'CONFIGURED'}</span></div>
          {!injectedProvider&&<label className="source-picker-label">EXPLORE A DATASET<select value={provider.source} onChange={event=>{const next=standaloneProviders[event.target.value];if(next)setProvider(next)}} aria-label="Visualization data source"><option value="VOLVE_SURVEY">Equinor Volve · verified surveys</option><option value="OIL_ASSAM_PUBLIC_LOCATIONS">Oil Assam · documented well locations</option><option value="NWIS_TESTBED_SYNTHETIC">NWIS testbed · synthetic</option></select></label>}
          <div className="hint">{providerIsVolve?'Survey data is bundled locally; no NWIS records are joined.':providerIsNwisDemo?'Protected source access is routed through the configured server proxy.':providerIsAssam?'Coordinates only from a public environmental filing. No trajectory, DORS, formation, event, hazard, casing, or telemetry data is included.':'Requests are handled by the host application provider; keep credentials server-side.'}</div>
          <button className="button primary full" onClick={connect} disabled={busy}>{busy?<RefreshCw size={14} className="spin"/>:<Activity size={14}/>} {busy?'Loading…':connected?'Refresh data':'Open spatial workspace'}</button>
          {error&&<div className="inline-error"><AlertCircle size={14}/><span>{error}</span></div>}
          {connected&&health?.data_store?.active_well_id&&<div className="health-detail"><span>Server active well</span><strong>{String(health.data_store.active_well_id)}</strong></div>}
        </section>

        <section className="panel">
          <div className="panel-title"><div><div className="panel-kicker"><LocateFixed size={14}/>WELL CONTEXT</div><h2>Choose active well</h2></div><span className="counter">{connected?`${wells.length} indexed`:'—'}</span></div>
          <select value={activeId} onChange={e=>pickActive(e.target.value)} disabled={!connected || !wells.length} aria-label="Active well">
            {wells.length===0&&<option value="">Connect to load source wells</option>}{wells.map(w=><option key={w.well_id} value={w.well_id}>{w.well_id} · {w.name}</option>)}
          </select>
          {connected&&providerIsAssam&&<div className="telemetry-query location-source-note"><b>LOCATION RECORDS ONLY</b><small>Subsurface survey, DORS, formations, events, hazards, casing, and telemetry are unavailable in this public source.</small><a href="https://environmentclearance.nic.in/writereaddata/Online/EDS/0_0_20_Feb_2023_2224388631ADSNDBNFeb23c.pdf" target="_blank" rel="noreferrer">Open the source filing ↗</a></div>}
          {connected&&!providerIsAssam&&<div className="telemetry-query"><label className="field-label" htmlFor="evaluation-depth">Evaluation depth <span>MD · m</span></label><input id="evaluation-depth" inputMode="decimal" type="number" min="0" step="0.1" placeholder="Set analysis depth" value={evaluationDepthMd} onChange={e=>setEvaluationDepthMd(e.target.value)} /><small>{providerIsVolve?'Use this as a visual MD reference. Volve DORS and event/hazard layers are unavailable.':'This drives depth-dependent DORS and hazard context. It is not a telemetry value or cross-well TVD correlation.'}</small><label className="field-label" htmlFor="telemetry-depth">Telemetry query <span>optional, confirmed MD</span></label><input id="telemetry-depth" inputMode="decimal" type="number" min="0" step="0.1" placeholder="No bit position until sampled" value={telemetryQueryMd} onChange={e=>setTelemetryQueryMd(e.target.value)} /><small>A bit marker appears only when telemetry is returned and the loaded trajectory covers its reported MD.</small></div>}
          <div className="well-facts"><div><small>FIELD</small><b>{active?.field ?? 'Unavailable'}</b></div><div><small>LOCATION</small><b>{active?.latitude!=null&&active.longitude!=null?`${format(active.latitude,4)}, ${format(active.longitude,4)}`:'Unavailable'}</b></div><div><small>EVALUATION DEPTH</small><b>{evaluationDepthValue==null?'Not set':`${format(evaluationDepthValue,0)} m MD`}</b></div><div><small>TELEMETRY DEPTH</small><b>{format(activeData?.telemetry.map(t=>number(t.measured_depth_m??t.current_measured_depth_m)).filter((x):x is number=>x!=null).at(-1),0)} m MD</b></div></div>
        </section>

        <section className="panel well-directory-panel" aria-label="Well directory">
          <div className="panel-title"><div><div className="panel-kicker"><Database size={14}/>WELL DIRECTORY</div><h2>Browse source wells</h2></div><span className="counter">{allWells.length} WELLS</span></div>
          <label className="well-directory-search"><Search size={13}/><input value={wellSearch} onChange={event=>setWellSearch(event.target.value)} placeholder="Search well ID or field" aria-label="Search wells" /></label>
          <div className="well-directory-list" role="listbox" aria-label="Available wells">
            {directoryWells.map(w=>{
              const isActive=w.well_id===activeId;
              const hasLocation=w.latitude!=null&&w.longitude!=null;
              const trajectory=wellData.get(w.well_id)?.trajectory;
              return <button key={w.well_id} role="option" aria-selected={isActive} className={`well-directory-row ${isActive?'active':''}`} onClick={()=>pickActive(w.well_id)}>
                <span className="directory-status" aria-hidden="true"/>
                <span className="directory-well-name"><b>{w.name||w.well_id}</b><small>{w.well_id}{w.field?` · ${w.field}`:''}</small></span>
                <span className="directory-well-meta">{hasLocation?`${w.latitude!.toFixed(3)}, ${w.longitude!.toFixed(3)}`:trajectory?`${trajectory.stations.length} stations`:'NO LOCATION'}</span>
              </button>;
            })}
            {!directoryWells.length&&<div className="empty-block"><Search size={14}/><span>No wells match that search.</span></div>}
          </div>
          <div className="directory-footnote">{locatedWellCount} with source coordinates · select a row to focus</div>
        </section>

        <section className="panel radius-panel">
          <div className="panel-title"><div><div className="panel-kicker"><Crosshair size={14}/>SHARED SEARCH RADIUS</div><h2>Nearby wells</h2></div><strong className="radius-value">{radiusKm}<small> km</small></strong></div>
          <div className="radius-options">{RADII.map(r=><button className={radiusKm===r?'chosen':''} key={r} onClick={()=>setRadiusKm(r)} disabled={!connected}>{r} km</button>)}</div>
          <div className="radius-caption"><span>FIELD SEARCH</span><ArrowRight size={13}/><span>DORS QUERY</span><ArrowRight size={13}/><span>3D INFLUENCE</span></div><div className="radius-result-count" aria-live="polite">{nearby.length} {nearby.length===1?'well':'wells'} within {radiusKm} km{selectedId?` · ${selectedId} selected`:''}</div>
        </section>

        {stage!=='global'&&<section className="panel offsets-panel">
          <div className="panel-title"><div><div className="panel-kicker"><Waypoints size={14}/>DORS · OFFSET RANKING</div><h2>Relevant offsets</h2></div><span className="counter">TOP {topVisible.length}</span></div>
          {!connected?<div className="empty-block"><Database size={18}/><span>Connect to load ranked offsets.</span></div>:loadingWell?<div className="empty-block"><RefreshCw size={15} className="spin"/><span>Loading well context…</span></div>:topVisible.length===0?<div className="empty-block"><AlertCircle size={15}/><span>{activeData?.unavailable['DORS offsets'] ?? 'No ranked offsets returned for this well.'}</span></div>:<div className="offset-list">{topVisible.map((o,i)=>{
            const well=allWells.find(w=>w.well_id===o.well_id), dist=active&&well?haversineKm(active,well):null, selected=selectedId===o.well_id;
            return <button key={o.well_id} className={`offset-row ${selected?'selected':''}`} onClick={()=>setSelectedId(o.well_id)}><span className={`rank rank-${i+1}`}>{String(i+1).padStart(2,'0')}</span><span className="offset-name"><b>{well?.name??o.well_id}</b><small>{o.well_id} · {dist==null?'DISTANCE UNAVAILABLE':`${format(dist)} km`}</small></span><span className="offset-score">{scoreValue(o)==null?'—':format(scoreValue(o),2)}</span></button>;
          })}</div>}
          {selectedScore&&<div className="why-card"><div className="why-header"><ShieldAlert size={14}/>WHY THIS OFFSET?<button onClick={()=>setSelectedId(null)} aria-label="Clear selected offset">×</button></div><b>{selectedWell?.well_id}</b><div className="score-grid">{(['spatial','formation','depth','trajectory','hazard'] as const).map(k=><div key={k}><small>{k.toUpperCase()}</small><strong>{number(selectedScore.component_scores?.[k])==null?'—':format(number(selectedScore.component_scores?.[k]),2)}</strong></div>)}</div><p>Backend component scores are shown as returned, without changing their scale.</p><button className="button subtle full" onClick={()=>selectedId&&pickActive(selectedId)}>Set as active well <ArrowRight size={13}/></button></div>}
        </section>}
        {stage==='subsurface'&&<section className="panel selected-card subsurface-intelligence"><div className="panel-kicker"><MapPin size={14}/>OFFSET INTELLIGENCE</div>{selectedWell?<><h2>{selectedWell.name}</h2><div className="selected-id">{selectedWell.well_id}</div><div className="selected-stats"><span>WELLHEAD DISTANCE <b>{active&&haversineKm(active,selectedWell)!=null?`${format(haversineKm(active,selectedWell),3)} km`:'Unavailable'}</b></span><span>DORS SCORE <b>{scoreValue(selectedScore)==null?'Unavailable':format(scoreValue(selectedScore),2)}</b></span><span>TRAJECTORY <b>{selectedData?.trajectory?`${selectedData.trajectory.stations.length} stations${selectedData.trajectory.coverage_status==='partial'?' · partial':''}`:'Unavailable'}</b></span><span>FORMATIONS / EVENTS <b>{selectedData?`${selectedData.layerProvenance.formations.availability==='unavailable'?'Unavailable':selectedData.formations.length} / ${selectedData.layerProvenance.events.availability==='unavailable'?'Unavailable':selectedData.events.length}`:'Not loaded'}</b></span>{evaluationDepthValue!=null&&selectedNearestEvent&&<span>NEAREST EVENT BY MD <b>{`${format(selectedNearestEvent.md,0)} m · Δ ${format(selectedNearestEvent.md-evaluationDepthValue,0)} m`}</b></span>}{selectedObject&&<span>SELECTED OBJECT <b>{selectedObject.label}</b></span>}</div>{evaluationDepthValue!=null&&selectedNearestEvent&&<p className="depth-caveat">Measured-depth difference only. This does not imply equal TVD or physical depth correlation.</p>}</>:<div className="empty-block"><Search size={15}/><span>Select a nearby well to inspect its source-backed data.</span></div>}</section>}
      </aside>

      <section className="viz-column">
        <div className="viz-header"><div><div className="panel-kicker">{stage==='global'?<Globe2 size={14}/>:stage==='field'?<Crosshair size={14}/>:<Layers3 size={14}/>} {stage==='global'?'GLOBAL · EARTH':stage==='field'?'FIELD · OFFSET DISCOVERY':'SUBSURFACE · DEPTH CONTEXT'}</div><h2>{stage==='global'?'Navigate the real Earth':stage==='field'?'Explore the local well neighborhood':'Trajectory relationship & wellbore context'}</h2></div><div className="viz-tools"><span className="orbit-label"><Compass size={13}/>{stage==='subsurface'?'ORBIT · DRAG TO ROTATE':'DRAG TO ROTATE EARTH · SCROLL TO ZOOM'}</span>{stage==='subsurface'&&<button className="button subtle return-surface" onClick={()=>setStage('field')} title="Return to the field view">RETURN TO FIELD <ArrowRight size={13}/></button>}{stage==='field'&&active&&<button className="button primary subsurface-cta" onClick={()=>setStage('subsurface')}>ENTER SUBSURFACE <ArrowDownRight size={14}/></button>}<button className="icon-button" title={stage==='subsurface'?'Reframe active survey':'Focus active well or fit Earth'} aria-label={stage==='subsurface'?'Reframe active survey':'Focus active well or fit Earth'} onClick={()=>{if(stage==='subsurface')setSceneView('orbit');window.dispatchEvent(new Event(stage==='subsurface'?'nwis:fit-subsurface':'nwis:fit'));}}><Maximize2 size={15}/></button></div></div>
        <div className={`scene-frame scene-stage-${stage}`}>
          <div className={`engine-layer earth-engine ${stage==='subsurface'?'earth-subsurface-surface':'earth-visible'}`} aria-hidden={false}>
            <React.Suspense fallback={<div className="scene-loading">Preparing real Earth…</div>}><CesiumEarth stage={stage==='subsurface'?'field':stage} surfaceContext={stage==='subsurface'} wells={allWells} active={active} radiusKm={radiusKm} selectedId={selectedId} dorsIds={topVisible.map(o=>o.well_id)} sourceLabel={sourceDisplayName} onSelect={pick} onSurfaceStatus={setSurfaceMode}/></React.Suspense>
          </div>
          {keepSubsurfaceMounted&&<div className={`engine-layer subsurface-engine ${stage==='subsurface'?'underground-entering':'underground-leaving'}`} aria-hidden={stage!=='subsurface'}><React.Suspense fallback={<div className="scene-loading">Loading subsurface scene…</div>}><Scene3D stage="subsurface" wells={allWells} active={active} data={wellData} radiusKm={radiusKm} selectedId={selectedId} onSelect={pick} onSelectObject={setSelectedObject} evaluationDepthM={number(evaluationDepthMd)} layers={showLayers}/></React.Suspense></div>}
          {stage==='subsurface'&&<div className="surface-context-caption"><b>EARTH SURFACE · {surfaceMode==='photoreal'?'PHOTOREALISTIC 3D TILES':surfaceMode==='terrain'?'TERRAIN + IMAGERY':surfaceMode==='fallback'?'GLOBE FALLBACK':'SATELLITE IMAGERY'}</b><span>{active&&active.latitude!=null&&active.longitude!=null?`${Math.abs(active.latitude).toFixed(4)}° ${active.latitude>=0?'N':'S'} · ${Math.abs(active.longitude).toFixed(4)}° ${active.longitude>=0?'E':'W'} · ${active.field??'FIELD UNSPECIFIED'}`:'SOURCE WELLHEAD LOCATION'}</span><small>Terrain view is geographic context; surface equipment is representational.</small></div>}
          <div className="scene-overlay scene-top-left"><span className="live-pulse"/>{stage==='field'?`SEARCH RADIUS · ${radiusKm} KM`:sourceDisplayName}<small>{stage==='global'?`${wells.filter(w=>w.latitude!=null&&w.longitude!=null).length} LOCATED`:stage==='field'?`${allWells.length} WELL RECORDS`:`${[...wellData.values()].filter(d=>!!d.trajectory).length} SURVEYS LOADED${activeOffsetDistanceKm!=null&&selectedId?` · WELLHEAD SPACING ${formatDistanceKm(activeOffsetDistanceKm)} KM`:''}`}</small>{stage==='subsurface'&&selectedId&&<small>OFFSET {selectedId}{selectedData?.trajectory?` · ${selectedData.trajectory.stations.length} STATIONS${selectedData.trajectory.coverage_status==='partial'?' · PARTIAL SURVEY':''}`:' · SURVEY UNAVAILABLE'}</small>}</div>
          <div className="scene-overlay scene-top-right">{active&&<><small>ACTIVE WELL</small><b>{active.well_id}</b></>}</div>
          
          {stage==='subsurface'&&<>
            <div className="scene-view-controls" role="group" aria-label="Subsurface camera view">{(['orbit','plan','section','downhole'] as const).map(mode=><button key={mode} className={sceneView===mode?'selected':''} aria-pressed={sceneView===mode} onClick={()=>{setSceneView(mode);window.dispatchEvent(new CustomEvent('nwis:scene-view',{detail:{mode}}));}}>{mode.toUpperCase()}</button>)}</div>
            <div className="scene-radius-context"><b>{radiusKm} km</b><span>FIELD FILTER · SURFACE DISTANCE</span></div>
            {active&&<SurveyOverview active={active} selected={selectedWell} data={wellData} onSelect={pick} />}
            <div className="scene-legend">
              <span><i className="legend-active"/>ACTIVE · VERIFIED SURVEY</span>
              {selectedData?.trajectory&&<span><i className="legend-offset"/>SELECTED · VERIFIED SURVEY</span>}
              {(activeData?.trajectory||selectedData?.trajectory)&&<span><i className="legend-station"/>SURVEY STATIONS</span>}
              {[...wellData.values()].some(d=>d.events.length>0)&&<span><i className="legend-event"/>RECORDED EVENTS</span>}
              {[...wellData.values()].some(d=>d.corridors.length>0)&&<span><i className="legend-risk"/>RECORDED RISK INTERVALS</span>}
              {[...wellData.values()].some(d=>d.formations.length>0)&&<span><i className="legend-form"/>RECORDED FORMATION INTERVALS</span>}
              {!([...wellData.values()].some(d=>d.events.length||d.corridors.length||d.formations.length))&&<span className="legend-unavailable">NO FORMATION, EVENT OR HAZARD RECORDS IN THIS SOURCE</span>}
            </div>
          </>}
          {stage==='subsurface'&&<div className="scene-help"><span>LEFT DRAG ORBIT</span><span>RIGHT DRAG PAN</span><span>SCROLL ZOOM</span></div>}
        </div>
          <div className="viz-footer"><div className="dataset-meta">{stage==='subsurface'?<><span><i className={`status-dot ${activeData?.trajectory?'online':''}`}/>{activeData?.trajectory?`${activeData.trajectory.stations.length} SURVEY STATIONS${activeData.trajectory.coverage_status==='partial'?' · PARTIAL COVERAGE':''}`:'TRAJECTORY UNAVAILABLE'}</span><span><i className={`status-dot ${activeData?.layerProvenance.formations.availability==='available'?'online':''}`}/>{activeData?.formations.length?`${activeData.formations.length} FORMATION RECORDS`:activeData?.layerProvenance.formations.detail??'FORMATION UNAVAILABLE'}</span><span><i className={`status-dot ${activeData?.telemetry.length?'online':''}`}/>{activeData?.telemetry.length?'TELEMETRY SAMPLE RETURNED':'BIT POSITION UNAVAILABLE'}</span></>:<><span><i className={`status-dot ${active?'online':''}`}/>{active&&active.latitude!=null&&active.longitude!=null?`${active.well_id} · ${active.latitude.toFixed(4)}, ${active.longitude.toFixed(4)}`:'WELL LOCATION UNAVAILABLE'}</span><span><i className={`status-dot ${surfaceMode==='fallback'?'':'online'}`}/>{surfaceMode==='photoreal'?'PHOTOREALISTIC 3D TILES':surfaceMode==='terrain'?'SATELLITE + ELEVATION':surfaceMode==='satellite'?'SATELLITE · ELEVATION FALLBACK':'OPEN MAP FALLBACK'}</span><span>WELLHEAD MARKERS · SOURCE COORDINATES</span></>}</div><div className="data-source">{stage==='subsurface'?'LOCAL FRAME · EAST / UP / NORTH · UNIFORM SCALE 0.02':'GEOGRAPHIC FRAME · WGS84'}</div></div>
        {stage==='subsurface'&&<div className="engineering-row">
          <div className="panel engineering-panel"><div className="panel-title"><div><div className="panel-kicker"><Activity size={14}/>DATA LAYERS</div><h2>Engineering context</h2></div><span className="counter">{providerIsVolve?'VERIFIED SURVEY':providerIsNwisDemo?'SYNTHETIC DEMO':providerIsAssam?'PUBLIC LOCATIONS ONLY':'CONNECTED SOURCE'}</span></div><div className="layer-toggles">{Object.entries(showLayers).map(([key,on])=>{const layerKey=(key==='trajectories'?'trajectory':key) as keyof WellData['layerProvenance'];const layer=activeData?.layerProvenance[layerKey];const availability=layer?.availability??'unavailable';const state=availability==='unavailable'?'NO DATA':availability==='partial'?'PARTIAL':on?'ON':'OFF';return <button key={key} title={layer?.detail??layer?.source??'Layer has not been loaded'} aria-label={`${key}: ${state}${availability==='unavailable'?'. Unavailable for this source.':''}`} disabled={availability==='unavailable'} className={`${on?'layer-on':''} ${availability==='unavailable'?'layer-unavailable':''}`} onClick={()=>setShowLayers(prev=>({...prev,[key]:!prev[key as keyof typeof prev]}))}><Eye size={13}/>{key.toUpperCase()}<span>{state}</span></button>})}</div>{activeStations.length>1?<div className="survey-depth-summary"><div><small>MEASURED DEPTH · MD</small><b>{rangeText(firstSurveyStation?.md_m,lastSurveyStation?.md_m)}</b></div><div><small>VERTICAL DEPTH · TVD</small><b>{rangeText(firstSurveyStation?.tvd_m,lastSurveyStation?.tvd_m)}</b></div><div><small>SUBSEA DATUM · TVDSS</small><b>{rangeText(firstSurveyStation?.tvdss_m,lastSurveyStation?.tvdss_m)}</b></div></div>:<p className="scene-data-note">No survey-depth range is available for this well.</p>}<p className="scene-data-note">Trajectory follows reported survey stations. Tube hue runs from survey start toward survey end; it is not lithology coloring. The shaded body is schematic and is not a casing-diameter claim. Cross-well depth alignment is not inferred.</p></div>
        </div>}
        {stage==='field'&&active&&<div className="panel field-results"><div className="panel-title"><div><div className="panel-kicker"><MapPin size={14}/>WELL PROXIMITY</div><h2>Within {radiusKm} km</h2></div><span className="counter">{nearby.length} LOCATED WELLS</span></div><div className="well-chip-list">{nearby.slice(0,12).map(({well:w,distanceKm})=>{const d=ranked.find(o=>o.well_id===w.well_id);return <button key={w.well_id} onClick={()=>{setSelectedId(w.well_id);setSelectedObject(null)}} className={selectedId===w.well_id?'active':''}><span>{w.well_id}</span><small>{formatDistanceKm(distanceKm)} km {d&&`· DORS ${format(scoreValue(d),2)}`}</small></button>})}{!nearby.length&&<div className="empty-block"><AlertCircle size={15}/><span>No source wells with verified coordinates fall inside this radius.</span></div>}</div></div>}
        {stage==='global'&&connected&&<div className="field-results global-note"><Globe2 size={16}/><span>Real Earth imagery with source coordinates overlaid. Select a located well or choose one from Well Context to fly into its field. {wells.filter(w=>w.latitude!=null&&w.longitude!=null).length} locations are available in this source.</span></div>}
      </section>
    </section>
    <footer className="bottom-note"><span>NWIS SPATIAL INTELLIGENCE</span><span>{providerIsNwisDemo?'SYNTHETIC NWIS TESTBED':providerIsVolve?'EQUINOR VOLVE · SEPARATE VERIFIED DATASET':providerIsAssam?'OIL ASSAM · DOCUMENTED LOCATIONS ONLY':'PROVENANCE · CONNECTED SOURCE ADAPTER'}</span><span>DATA STATUS · {connected?'SOURCE READY':health?.status?.toUpperCase()??'NOT LOADED'}</span></footer>
    {showKey&&<div className="modal-backdrop" onClick={()=>setShowKey(false)}><div className="help-modal" onClick={e=>e.stopPropagation()}><div className="panel-kicker"><CircleHelp size={14}/>DATA & CONTROLS</div><h2>Spatial workspace</h2><p>{providerIsVolve?'The selected source is the local Equinor Volve survey dataset; it is never joined to NWIS records.':providerIsNwisDemo?'NWIS requests pass through a same-origin server proxy, which attaches NWIS_API_KEY without exposing it to browser JavaScript.':providerIsAssam?'The selected Assam source contains two coordinates transcribed from a government environmental filing. It contains no trajectory or operating history.':'The host application supplies this data adapter. Keep credentials in its server-side proxy; the renderer receives only normalized records.'}</p><ol><li><b>Source adapter</b> supplies normalized wells, trajectories and available engineering layers.</li><li><b>Radius filter</b> uses calculated wellhead distance; records without coordinates are excluded.</li><li><b>Depths</b> keep evaluation MD and telemetry MD separate. MD, TVD and TVDSS are not interchangeable.</li></ol><p>Layers appear only where the selected source returns usable records. Unknown coverage remains unavailable.</p><button className="button subtle" onClick={()=>setShowKey(false)}>Close</button></div></div>}
  </main>;
}
