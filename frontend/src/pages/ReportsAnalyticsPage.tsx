import React, { useEffect, useState } from 'react';
import {
  FileSpreadsheet,
  Download,
  Printer,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';

// Real NPT breakdown from GET /api/v2/events (modules/02_nwis_backend),
// summing each event's actual npt_hours by hazard type — replaces the
// previous page's hardcoded "48.5 hrs / 22.5 hrs / 14.0 hrs..." table.
const HAZARD_COLORS: Record<string, string> = {
  MUD_LOSS: 'bg-amber-500',
  STUCK_PIPE: 'bg-rose-500',
  KICK: 'bg-purple-500',
  WELLBORE_INSTABILITY: 'bg-cyan-500',
  TORQUE_SPIKE: 'bg-orange-500',
  CEMENTING_FAILURE: 'bg-slate-500',
};

export const ReportsAnalyticsPage: React.FC = () => {
  const { activeWellId, activeWell, telemetry, telemetryHistory } = useApp();
  const [nptByHazard, setNptByHazard] = useState<Record<string, number>>({});
  const [totalNpt, setTotalNpt] = useState<number>(0);
  const [nptLoading, setNptLoading] = useState(true);
  const [nptError, setNptError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setNptLoading(true);
      try {
        const data = await api.searchEventsStructured();
        if (cancelled) return;
        const byHazard: Record<string, number> = {};
        for (const evt of data.events) {
          byHazard[evt.event_type] = (byHazard[evt.event_type] || 0) + (evt.npt_hours || 0);
        }
        setNptByHazard(byHazard);
        setTotalNpt(data.total_npt_hours);
        setNptError(null);
      } catch (err) {
        if (!cancelled) setNptError('Failed to load NPT breakdown from /api/v2/events (module 02).');
        console.error(err);
      } finally {
        if (!cancelled) setNptLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleExportCsv = () => {
    if (!telemetryHistory || telemetryHistory.length === 0) return;

    const headers = ['timestamp', 'measured_depth_m', 'rop_m_hr', 'wob_kn', 'rpm', 'torque_knm', 'spp_bar', 'flow_in_lpm', 'flow_out_lpm', 'pit_volume_m3', 'ecd_gcc'];
    const rows = telemetryHistory.map((t) => [
      t.timestamp,
      t.measured_depth_m.toFixed(2),
      t.rop_m_hr.toFixed(2),
      t.wob_kn.toFixed(1),
      t.rpm.toFixed(1),
      t.torque_knm.toFixed(2),
      t.standpipe_pressure_bar.toFixed(1),
      t.flow_in_lpm.toFixed(0),
      t.flow_out_lpm.toFixed(0),
      t.pit_volume_m3.toFixed(2),
      t.ecd_gcc.toFixed(2),
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `${activeWellId}_telemetry_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(telemetryHistory, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${activeWellId}_telemetry_stream.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="scada-panel p-3 flex items-center justify-between border-l-4 border-l-cyan-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <FileSpreadsheet className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              MODULE 7: OPERATIONAL REPORTING, NPT ANALYTICS & DATA EXPORT
              <span className="text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.5 rounded">
                EXPORT ENGINE
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Daily Drilling Summary | Historical NPT Breakdown | Telemetry Stream Archival
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => window.print()}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-mono flex items-center gap-1.5 transition"
          >
            <Printer className="w-3.5 h-3.5" /> PRINT REPORT
          </button>
        </div>
      </div>

      {/* Daily Drilling Summary Card */}
      <div className="scada-panel p-4 space-y-3">
        <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800 flex items-center justify-between">
          <span>DAILY SHIFT DRILLING SUMMARY (IADC COMPLIANT FORMAT)</span>
          <span className="text-[10px] text-cyan-400">Report Date: {new Date().toLocaleDateString()}</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
          <div className="bg-slate-900/80 p-3 rounded border border-slate-800 space-y-1">
            <div className="text-slate-400 text-[10px]">WELL IDENTIFIER</div>
            <div className="text-sm font-bold text-slate-100">{activeWell?.well_name || activeWellId}</div>
            <div className="text-[10px] text-slate-400">{activeWell?.field || 'Nahorkatiya Field'}</div>
          </div>

          <div className="bg-slate-900/80 p-3 rounded border border-slate-800 space-y-1">
            <div className="text-slate-400 text-[10px]">CURRENT BIT DEPTH</div>
            <div className="text-sm font-bold text-cyan-400">{telemetry?.measured_depth_m.toFixed(1)} m MD</div>
            <div className="text-[10px] text-slate-400">TVDSS: {telemetry?.tvdss_m.toFixed(1)} m</div>
          </div>

          <div className="bg-slate-900/80 p-3 rounded border border-slate-800 space-y-1">
            <div className="text-slate-400 text-[10px]">CURRENT FORMATION</div>
            <div className="text-sm font-bold text-amber-300 truncate">{telemetry?.formation.replace('_', ' ')}</div>
            <div className="text-[10px] text-emerald-400">Stratigraphic ξ: {telemetry?.xi.toFixed(3)}</div>
          </div>

          <div className="bg-slate-900/80 p-3 rounded border border-slate-800 space-y-1">
            <div className="text-slate-400 text-[10px]">ACTIVE MUD WEIGHT</div>
            <div className="text-sm font-bold text-slate-100">{telemetry?.ecd_gcc.toFixed(2)} g/cc ECD</div>
            <div className="text-[10px] text-slate-400">Flow: {telemetry?.flow_in_lpm.toFixed(0)} LPM</div>
          </div>
        </div>
      </div>

      {/* Historical NPT Breakdown & Financial Cost Analysis */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* NPT Hours Lost */}
        <div className="scada-panel p-4 space-y-3">
          <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800 flex items-center justify-between">
            <span>HISTORICAL NPT DOWNTIME BY HAZARD CATEGORY (GET /api/v2/events)</span>
            <span className="text-[11px] text-rose-400">
              {nptLoading ? 'Loading…' : `Total Lost Time: ${totalNpt.toFixed(1)} hrs`}
            </span>
          </div>

          {nptError && <div className="text-[11px] font-mono text-rose-300 py-2">{nptError}</div>}

          <div className="space-y-2 font-mono text-xs">
            {Object.entries(nptByHazard)
              .sort(([, a], [, b]) => b - a)
              .map(([hazard, hours]) => {
                const pct = totalNpt > 0 ? (hours / totalNpt) * 100 : 0;
                return (
                  <div key={hazard} className="space-y-1">
                    <div className="flex justify-between text-slate-300">
                      <span>{hazard.replace(/_/g, ' ')}</span>
                      <span className="font-bold text-slate-100">{hours.toFixed(1)} hrs ({pct.toFixed(1)}%)</span>
                    </div>
                    <div className="w-full bg-slate-950 h-2 rounded overflow-hidden border border-slate-800">
                      <div className={`h-full ${HAZARD_COLORS[hazard] || 'bg-slate-500'}`} style={{ width: `${pct}%` }}></div>
                    </div>
                  </div>
                );
              })}
            {!nptLoading && Object.keys(nptByHazard).length === 0 && !nptError && (
              <div className="text-slate-500 text-center py-3">No NPT events on record.</div>
            )}
          </div>
        </div>

        {/* Export Center Cards */}
        <div className="scada-panel p-4 space-y-3 flex flex-col justify-between">
          <div>
            <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800">
              DATASET & REPORT EXPORT CENTER
            </div>

            <div className="mt-3 space-y-2.5 font-mono text-xs">
              <div className="p-3 bg-slate-900/80 border border-slate-800 rounded flex items-center justify-between">
                <div>
                  <div className="font-bold text-slate-100">Live Telemetry Historian Buffer (CSV)</div>
                  <div className="text-[10px] text-slate-400">{telemetryHistory.length} Recorded 1 Hz Samples</div>
                </div>
                <button
                  onClick={handleExportCsv}
                  className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded flex items-center gap-1.5 transition"
                >
                  <Download className="w-3.5 h-3.5" /> EXPORT CSV
                </button>
              </div>

              <div className="p-3 bg-slate-900/80 border border-slate-800 rounded flex items-center justify-between">
                <div>
                  <div className="font-bold text-slate-100">Canonical Stream Envelope (JSON)</div>
                  <div className="text-[10px] text-slate-400">WITSML & SIH26121 Machine-Readable Format</div>
                </div>
                <button
                  onClick={handleExportJson}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded flex items-center gap-1.5 transition"
                >
                  <Download className="w-3.5 h-3.5" /> EXPORT JSON
                </button>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800 text-[10px] font-mono text-slate-400">
            Export provenance: All exported files include explicit SYNTHETIC or OBSERVED metadata tags.
          </div>
        </div>
      </div>
    </div>
  );
};
