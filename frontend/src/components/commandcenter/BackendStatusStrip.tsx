import React, { useEffect, useState } from 'react';
import { api } from '../../services/api';

// Genuinely live backend status -- unlike DashboardPage's equivalent
// strip, which hardcodes green for modules 01/02 regardless of actual
// health (found while building this). Polls the real health endpoints
// directly rather than reusing that pattern.
export const BackendStatusStrip: React.FC = () => {
  const [m01Up, setM01Up] = useState<boolean | null>(null);
  const [m02Up, setM02Up] = useState<boolean | null>(null);
  const [m03Up, setM03Up] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      // getSimStatus() hits module 04's real, auth-gated /api/v3/physics/status
      // -- used here purely as a liveness probe (module 04/05 have no
      // dedicated /api/v3 health route of their own; their public /health is
      // outside the versioned prefix the m03 client is pinned to). A fulfilled
      // call means the server is up and the configured API key is correct;
      // it says nothing about whether the predictive ML models are fitted
      // (see SystemStatusPage/health payload for that distinction).
      const [m01, m02, m03] = await Promise.allSettled([
        api.getHealthM01(),
        api.getHealthM02(),
        api.getSimStatus(),
      ]);
      if (cancelled) return;
      setM01Up(m01.status === 'fulfilled' && m01.value.status === 'healthy');
      setM02Up(m02.status === 'fulfilled' && m02.value.status === 'healthy');
      setM03Up(m03.status === 'fulfilled');
    };
    check();
    const interval = setInterval(check, 15000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  const Dot = ({ ok }: { ok: boolean | null }) => (
    <span className={`w-2 h-2 rounded-full ${ok === null ? 'bg-slate-600' : ok ? 'bg-emerald-400' : 'bg-rose-400'}`} />
  );

  return (
    <div className="scada-panel px-3 py-1.5 flex items-center gap-4 text-[10px] font-mono text-slate-300 overflow-x-auto">
      <span className="text-slate-500 uppercase tracking-widest shrink-0">Backend:</span>
      <span className="flex items-center gap-1.5"><Dot ok={m01Up} /> Module 01 · Document Intelligence (8001)</span>
      <span className="flex items-center gap-1.5"><Dot ok={m02Up} /> Module 02 · NWIS Backend (8002)</span>
      <span className="flex items-center gap-1.5"><Dot ok={m03Up} /> Module 04/05 · Physics + Predictive (8003)</span>
    </div>
  );
};
