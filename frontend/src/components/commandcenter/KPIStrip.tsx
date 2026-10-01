import React from 'react';
import { Gauge, Users, ShieldAlert, Wrench } from 'lucide-react';
import { NWISAnalysisResponse } from '../../types';

// Glanceable top-of-page KPI row -- always-visible summary numbers rather
// than buried in tabs (the genuinely good pattern from GeoMine's header
// cards). Every number here is real: pulled straight from analyzeWell's
// response, not a separate fabricated summary.

const RISK_STYLE: Record<string, string> = {
  CRITICAL: 'text-rose-400 border-rose-500/40 bg-rose-500/10',
  HIGH: 'text-amber-400 border-amber-500/40 bg-amber-500/10',
  MODERATE: 'text-amber-300 border-amber-500/25 bg-amber-500/5',
  LOW: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/5',
};

function KPICard({ icon: Icon, label, value, sub, riskLevel }: {
  icon: React.ElementType; label: string; value: string; sub?: string; riskLevel?: string;
}) {
  const style = riskLevel ? RISK_STYLE[riskLevel] || RISK_STYLE.LOW : 'text-slate-200 border-slate-800 bg-slate-900/40';
  return (
    <div className={`flex-1 min-w-[130px] border rounded px-3 py-2 ${style}`}>
      <div className="flex items-center gap-1.5 text-[9px] font-mono uppercase text-slate-400">
        <Icon className="w-3 h-3" /> {label}
      </div>
      <div className="text-lg font-mono font-bold leading-tight mt-0.5">{value}</div>
      {sub && <div className="text-[9px] font-mono text-slate-500 truncate">{sub}</div>}
    </div>
  );
}

export const KPIStrip: React.FC<{ analysis: NWISAnalysisResponse | null; eventCount: number }> = ({ analysis, eventCount }) => {
  if (!analysis) {
    return (
      <div className="flex gap-2">
        <KPICard icon={Gauge} label="Overall Risk" value="—" />
        <KPICard icon={Users} label="Offset Analogs" value="—" />
        <KPICard icon={ShieldAlert} label="Hazard Corridors" value="—" />
        <KPICard icon={Wrench} label="Events (Active Well)" value="—" />
      </div>
    );
  }

  const worstCorridor = [...analysis.active_risk_corridors].sort((a, b) => {
    const rank = { LOW: 0, MODERATE: 1, HIGH: 2, CRITICAL: 3 } as const;
    return (rank[b.risk_level] ?? 0) - (rank[a.risk_level] ?? 0);
  })[0];

  return (
    <div className="flex gap-2 flex-wrap">
      <KPICard
        icon={Gauge} label="Overall Risk" value={analysis.overall_risk_level}
        riskLevel={analysis.overall_risk_level}
      />
      <KPICard
        icon={Users} label="Offset Analogs" value={String(analysis.offset_rankings.length)}
        sub={analysis.offset_rankings[0] ? `Top: ${analysis.offset_rankings[0].well_name}` : undefined}
      />
      <KPICard
        icon={ShieldAlert} label="Hazard Corridors" value={String(analysis.active_risk_corridors.length)}
        sub={worstCorridor ? `${worstCorridor.hazard_type.replace(/_/g, ' ')} · ${worstCorridor.risk_level}` : 'None active'}
        riskLevel={worstCorridor?.risk_level}
      />
      <KPICard icon={Wrench} label="Events (Active Well)" value={String(eventCount)} />
    </div>
  );
};
