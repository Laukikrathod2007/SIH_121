import React, { useEffect, useRef, useState } from 'react';

interface LiveValueProps {
  value: React.ReactNode;
  className?: string;
}

// Briefly flashes when its value actually changes, so a real incoming
// telemetry tick reads as "live" instead of sitting static like plain text.
// Compares by rendered string, so it only flashes on a genuine change, not
// every re-render.
export const LiveValue: React.FC<LiveValueProps> = ({ value, className = '' }) => {
  const [flash, setFlash] = useState(false);
  const prev = useRef<string | null>(null);

  useEffect(() => {
    const current = String(value);
    if (prev.current !== null && prev.current !== current) {
      setFlash(true);
      const t = setTimeout(() => setFlash(false), 450);
      prev.current = current;
      return () => clearTimeout(t);
    }
    prev.current = current;
    return undefined;
  }, [value]);

  return (
    <span
      className={`inline-block transition-all duration-300 ${flash ? 'text-cyan-300' : ''} ${className}`}
      style={flash ? { textShadow: '0 0 8px rgba(6,182,212,0.8)' } : undefined}
    >
      {value}
    </span>
  );
};
