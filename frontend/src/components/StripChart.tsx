import React, { useEffect, useRef, useState } from 'react';

export interface StripSeries {
  key: string;
  label: string;
  color: string;
  axis?: 'left' | 'right';
  dashed?: boolean;
  width?: number;
}

interface StripChartProps {
  data: Record<string, number>[];
  series: StripSeries[];
  xKey?: string;
  height?: number;
  leftPad?: number;
  rightPad?: number;
  leftDigits?: number;
  rightDigits?: number;
}

const GRID = '#1e293b';
const AXIS_TEXT = '#64748b';
const MARGIN = { top: 8, bottom: 18, side: 46 };

// Canvas strip chart: redraws in ~1 ms, so it keeps up with 25 Hz telemetry where SVG charts could not.
export const StripChart: React.FC<StripChartProps> = ({
  data,
  series,
  xKey = 't',
  height = 240,
  leftPad = 0,
  rightPad = 0,
  leftDigits = 0,
  rightDigits = 0,
}) => {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [width, setWidth] = useState(0);
  const hasRight = series.some((s) => s.axis === 'right');

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || width === 0) return;
    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    const x0 = MARGIN.side;
    const x1 = width - (hasRight ? MARGIN.side : 10);
    const y0 = MARGIN.top;
    const y1 = height - MARGIN.bottom;

    const range = (axis: 'left' | 'right', pad: number) => {
      let min = Infinity;
      let max = -Infinity;
      for (const s of series) {
        if ((s.axis ?? 'left') !== axis) continue;
        for (const row of data) {
          const v = row[s.key];
          if (v == null || Number.isNaN(v)) continue;
          if (v < min) min = v;
          if (v > max) max = v;
        }
      }
      if (!Number.isFinite(min)) return null;
      min -= pad;
      max += pad;
      if (max - min < 1e-6) { min -= 1; max += 1; }
      return { min, max };
    };

    const left = range('left', leftPad);
    const right = hasRight ? range('right', rightPad) : null;

    ctx.font = '10px ui-monospace, SFMono-Regular, Menlo, monospace';
    ctx.lineWidth = 1;

    // Horizontal grid + axis labels
    const rows = 4;
    for (let i = 0; i <= rows; i++) {
      const y = y0 + ((y1 - y0) * i) / rows;
      ctx.strokeStyle = GRID;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(x0, y);
      ctx.lineTo(x1, y);
      ctx.stroke();
      ctx.setLineDash([]);
      const frac = 1 - i / rows;
      if (left) {
        ctx.fillStyle = series.find((s) => (s.axis ?? 'left') === 'left')?.color ?? AXIS_TEXT;
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText((left.min + (left.max - left.min) * frac).toFixed(leftDigits), x0 - 4, y);
      }
      if (right) {
        ctx.fillStyle = series.find((s) => s.axis === 'right')?.color ?? AXIS_TEXT;
        ctx.textAlign = 'left';
        ctx.fillText((right.min + (right.max - right.min) * frac).toFixed(rightDigits), x1 + 4, y);
      }
    }

    if (data.length < 2) return;
    const tMin = data[0][xKey];
    const tMax = data[data.length - 1][xKey];
    const tSpan = Math.max(1e-6, tMax - tMin);
    const px = (t: number) => x0 + ((t - tMin) / tSpan) * (x1 - x0);

    // Time labels
    ctx.fillStyle = AXIS_TEXT;
    ctx.textBaseline = 'top';
    [0, 0.5, 1].forEach((f, i) => {
      ctx.textAlign = i === 0 ? 'left' : i === 1 ? 'center' : 'right';
      ctx.fillText(`${(tMin + tSpan * f).toFixed(1)}s`, x0 + (x1 - x0) * f, y1 + 4);
    });

    ctx.save();
    ctx.beginPath();
    ctx.rect(x0, y0, x1 - x0, y1 - y0);
    ctx.clip();
    for (const s of series) {
      const r = s.axis === 'right' ? right : left;
      if (!r) continue;
      const py = (v: number) => y1 - ((v - r.min) / (r.max - r.min)) * (y1 - y0);
      ctx.strokeStyle = s.color;
      ctx.lineWidth = s.width ?? 1.75;
      ctx.setLineDash(s.dashed ? [5, 4] : []);
      ctx.beginPath();
      let started = false;
      for (const row of data) {
        const v = row[s.key];
        if (v == null || Number.isNaN(v)) { started = false; continue; }
        const X = px(row[xKey]);
        const Y = py(v);
        if (started) ctx.lineTo(X, Y); else { ctx.moveTo(X, Y); started = true; }
      }
      ctx.stroke();
    }
    ctx.restore();
  }, [data, series, xKey, width, height, hasRight, leftPad, rightPad, leftDigits, rightDigits]);

  return (
    <div ref={wrapRef} className="w-full">
      <canvas ref={canvasRef} style={{ width: '100%', height }} />
      <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mt-1 text-[11px] font-mono">
        {series.map((s) => (
          <span key={s.key} className="flex items-center gap-1.5" style={{ color: s.color }}>
            <span
              className="inline-block w-4"
              style={{ borderTop: `2px ${s.dashed ? 'dashed' : 'solid'} ${s.color}` }}
            />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
};
