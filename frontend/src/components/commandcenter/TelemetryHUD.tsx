import React from 'react';
import { TelemetryRecord } from '../../types';

// Compact ROGII-style HUD strip, real depth-indexed telemetry
// (getTelemetryRecords, Module 02 -- not the frozen Module 03 placeholder
// every other page in this app reads). Deliberately a plain HTML overlay,
// not floating 3D labels, per the visual-reference synthesis.

function Field({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="text-[10px] font-mono text-slate-500 uppercase">{label}</span>
      <span className="text-sm font-mono font-bold text-slate-100">{value}</span>
      <span className="text-[10px] font-mono text-slate-500">{unit}</span>
    </div>
  );
}

export const TelemetryHUD: React.FC<{ telemetry: TelemetryRecord | null; depth: number }> = ({ telemetry, depth }) => {
  return (
    <div className="scada-panel px-4 py-2 flex items-center justify-between flex-wrap gap-3">
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-cyan-400" />
        <span className="text-[10px] font-mono text-cyan-300 uppercase">Replay</span>
      </div>
      <Field label="MD" value={depth.toFixed(0)} unit="m" />
      {telemetry ? (
        <>
          <Field label="ROP" value={telemetry.rop_m_hr.toFixed(1)} unit="m/hr" />
          <Field label="WOB" value={telemetry.wob_klbs.toFixed(0)} unit="klbs" />
          <Field label="RPM" value={telemetry.rpm.toFixed(0)} unit="" />
          <Field label="Torque" value={telemetry.torque_kn_m.toFixed(1)} unit="kN·m" />
          <Field label="SPP" value={telemetry.standpipe_pressure_psi.toFixed(0)} unit="psi" />
          <Field label="MW" value={telemetry.mud_weight_ppg.toFixed(2)} unit="ppg" />
        </>
      ) : (
        <span className="text-[10px] font-mono text-slate-600">
          No telemetry data exists for this well (only WELL-HGJ-012 in the testbed has any)
        </span>
      )}
    </div>
  );
};
