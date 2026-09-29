import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Radio } from 'lucide-react';
import { api } from '../services/api';
import { FormationTop, SurveyStation, TelemetryData, RiskEvaluation } from '../types';

interface WellCutawayCockpitProps {
  wellId: string;
  wellName: string;
  telemetry: TelemetryData | null;
  activeRisk: RiskEvaluation | null;
}

const FORMATION_PALETTE = ['#78350f', '#92400e', '#57534e', '#3f3f46', '#1c1917', '#44403c', '#292524', '#0c0a09'];

// Real horizontal departure from the wellbore's surface location, derived
// from the same ns_m/ew_m the minimum-curvature computation already
// produced -- draws whatever shape the well actually has (vertical,
// J-type, horizontal), not an artistic guess.
function departureM(s: SurveyStation): number {
  return Math.sqrt(s.ns_m ** 2 + s.ew_m ** 2);
}

function interpolateAtMD(stations: SurveyStation[], md: number): SurveyStation | null {
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

const VB_W = 520;
const VB_H = 480;
const PAD_TOP = 40;
const PAD_BOTTOM = 20;

export const WellCutawayCockpit: React.FC<WellCutawayCockpitProps> = ({ wellId, wellName, telemetry, activeRisk }) => {
  const [formations, setFormations] = useState<FormationTop[]>([]);
  const [stations, setStations] = useState<SurveyStation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      api.getFormations(wellId).catch(() => []),
      api.getTrajectory(wellId).catch(() => null),
    ]).then(([forms, traj]) => {
      if (cancelled) return;
      setFormations(forms);
      setStations(traj?.stations ?? []);
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [wellId]);

  const maxTvd = Math.max(...formations.map((f) => f.top_md_m + f.thickness_m), ...stations.map((s) => s.tvd_m), 100);
  const maxDeparture = Math.max(...stations.map(departureM), 1);
  const plotH = VB_H - PAD_TOP - PAD_BOTTOM;
  const plotW = VB_W - 60;

  const yScale = (tvd: number) => PAD_TOP + (tvd / maxTvd) * plotH;
  const xScale = (dep: number) => 40 + (dep / Math.max(maxDeparture, 50)) * plotW * 0.85;

  const pathD = useMemo(() => {
    if (stations.length < 2) return '';
    return stations
      .map((s, i) => `${i === 0 ? 'M' : 'L'} ${xScale(departureM(s)).toFixed(1)} ${yScale(s.tvd_m).toFixed(1)}`)
      .join(' ');
  }, [stations, maxTvd, maxDeparture]);

  // Real kickoff point: first station where inclination genuinely departs
  // from vertical, not an arbitrary decorative marker.
  const kop = stations.find((s) => s.inclination_deg > 5);

  const bitStation = telemetry ? interpolateAtMD(stations, telemetry.measured_depth_m) : null;
  const bitPos = bitStation ? { x: xScale(departureM(bitStation)), y: yScale(bitStation.tvd_m) } : null;

  const kickScore = activeRisk?.fused_hazard_scores?.KICK ?? 0;
  const riskLevel = activeRisk?.overall_risk_level ?? 'LOW';

  return (
    <div className="scada-panel overflow-hidden">
      {/* Hazard watch banner -- real KICK fusion score, not a fabricated sensor reading */}
      <div
        className={`px-4 py-2 flex items-center justify-between border-b ${
          kickScore >= 0.5 ? 'bg-rose-950/40 border-rose-500/40' : 'bg-slate-900/60 border-slate-800'
        }`}
      >
        <div className="flex items-center gap-2 text-xs font-mono">
          <AlertTriangle className={`w-4 h-4 ${kickScore >= 0.5 ? 'text-rose-400' : 'text-slate-500'}`} />
          <span className={`font-bold uppercase ${kickScore >= 0.5 ? 'text-rose-300' : 'text-slate-400'}`}>
            Kick Watch · Fused Hazard Score
          </span>
          <span className={`font-mono font-bold ${kickScore >= 0.5 ? 'text-rose-300' : 'text-emerald-400'}`}>
            {(kickScore * 100).toFixed(0)}%
          </span>
        </div>
        <div className="text-[10px] font-mono text-slate-400 uppercase">Overall Risk: <span className="text-slate-200 font-bold">{riskLevel}</span></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0">
        {/* Cutaway earth cross-section */}
        <div className="lg:col-span-2 bg-[#0a0806] p-2">
          {loading ? (
            <div className="h-[420px] flex items-center justify-center text-slate-500 font-mono text-xs">Loading real subsurface data...</div>
          ) : (
            <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="w-full h-[420px]">
              {/* Formation bands -- real top/thickness per formation */}
              {formations.map((f, idx) => {
                const y0 = yScale(f.top_md_m);
                const y1 = yScale(f.top_md_m + f.thickness_m);
                return (
                  <g key={f.formation_name + idx}>
                    <rect x={0} y={y0} width={VB_W} height={Math.max(y1 - y0, 1)} fill={FORMATION_PALETTE[idx % FORMATION_PALETTE.length]} opacity={0.55} />
                    <text x={8} y={y0 + 12} fill="#e2e8f0" fontSize={9} fontFamily="monospace" opacity={0.85}>
                      {f.formation_name.toUpperCase()}
                    </text>
                  </g>
                );
              })}

              {/* Depth axis */}
              {formations.map((f, idx) => (
                <text key={`d-${idx}`} x={VB_W - 4} y={yScale(f.top_md_m) + 10} fill="#64748b" fontSize={8} fontFamily="monospace" textAnchor="end">
                  {f.top_md_m.toFixed(0)}m
                </text>
              ))}

              {/* Derrick */}
              <g stroke="#94a3b8" strokeWidth={1.5} fill="none" opacity={0.7}>
                <line x1={40} y1={PAD_TOP} x2={20} y2={4} />
                <line x1={40} y1={PAD_TOP} x2={60} y2={4} />
                <line x1={20} y1={4} x2={60} y2={4} />
              </g>

              {/* Real wellbore path */}
              {pathD && <path d={pathD} stroke="#22d3ee" strokeWidth={2.5} fill="none" strokeLinecap="round" />}

              {/* Real kickoff point marker */}
              {kop && (
                <g>
                  <circle cx={xScale(departureM(kop))} cy={yScale(kop.tvd_m)} r={4} fill="#f59e0b" />
                  <text x={xScale(departureM(kop)) + 8} y={yScale(kop.tvd_m) + 3} fill="#f59e0b" fontSize={8} fontFamily="monospace">
                    KOP {kop.md_m.toFixed(0)}m
                  </text>
                </g>
              )}

              {/* Real live bit position */}
              {bitPos && (
                <g>
                  <circle cx={bitPos.x} cy={bitPos.y} r={7} fill="#22d3ee" opacity={0.25}>
                    <animate attributeName="r" values="7;12;7" dur="1.6s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.35;0.05;0.35" dur="1.6s" repeatCount="indefinite" />
                  </circle>
                  <circle cx={bitPos.x} cy={bitPos.y} r={4} fill="#e0f2fe" stroke="#0891b2" strokeWidth={1.5} />
                </g>
              )}
            </svg>
          )}
        </div>

        {/* Real INC/AZI depth track -- the log-graph panel, honestly scoped to
            data we actually have (no fabricated GR/RES/RHOB curves) */}
        <div className="bg-slate-950/60 border-l border-slate-800 p-3">
          <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 uppercase mb-2">
            <span className="flex items-center gap-1"><Radio className="w-3 h-3 text-cyan-400" /> Survey Track</span>
            <span className="text-cyan-400">Live</span>
          </div>
          <svg viewBox={`0 0 200 ${VB_H - 40}`} className="w-full h-[380px]">
            {stations.map((s, i) => {
              if (i === 0) return null;
              const prev = stations[i - 1];
              const y0 = yScale(prev.tvd_m) - PAD_TOP;
              const y1 = yScale(s.tvd_m) - PAD_TOP;
              const incX0 = 10 + (prev.inclination_deg / 90) * 80;
              const incX1 = 10 + (s.inclination_deg / 90) * 80;
              const aziX0 = 110 + (prev.azimuth_deg / 360) * 80;
              const aziX1 = 110 + (s.azimuth_deg / 360) * 80;
              return (
                <g key={i}>
                  <line x1={incX0} y1={y0} x2={incX1} y2={y1} stroke="#22d3ee" strokeWidth={1.3} />
                  <line x1={aziX0} y1={y0} x2={aziX1} y2={y1} stroke="#f472b6" strokeWidth={1.3} />
                </g>
              );
            })}
            <text x={10} y={-4} fill="#22d3ee" fontSize={8} fontFamily="monospace">INC (0-90°)</text>
            <text x={110} y={-4} fill="#f472b6" fontSize={8} fontFamily="monospace">AZI (0-360°)</text>
          </svg>
        </div>
      </div>
    </div>
  );
};
