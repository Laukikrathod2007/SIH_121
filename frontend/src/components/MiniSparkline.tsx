import React from 'react';

interface MiniSparklineProps {
  data: number[];
  color?: string;
  width?: number;
  height?: number;
}

// A real sparkline driven by actual telemetry history (the same
// telemetryHistory the full StripChart on Live Drilling reads from) -- not
// a decorative fake wiggle. Renders nothing informative if there's no
// history yet rather than fabricating a shape.
export const MiniSparkline: React.FC<MiniSparklineProps> = ({ data, color = '#06b6d4', width = 72, height = 24 }) => {
  if (data.length < 2) {
    return <svg width={width} height={height} />;
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);
  const points = data
    .map((v, i) => `${(i * step).toFixed(1)},${(height - ((v - min) / range) * height).toFixed(1)}`)
    .join(' ');
  const last = data[data.length - 1];
  const lastY = height - ((last - min) / range) * height;

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" opacity={0.85} />
      <circle cx={width} cy={lastY} r={2.5} fill={color} />
    </svg>
  );
};
