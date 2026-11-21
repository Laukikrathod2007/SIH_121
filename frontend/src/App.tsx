import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { DashboardPage } from './pages/DashboardPage';
import { CommandCenterPage } from './pages/CommandCenterPage';
import { LiveDrillingPage } from './pages/LiveDrillingPage';
import { NearbyWellsPage } from './pages/NearbyWellsPage';
import { NwisMapPage } from './pages/NwisMapPage';
import { GeologicalCorrelationPage } from './pages/GeologicalCorrelationPage';
import { RiskPredictionPage } from './pages/RiskPredictionPage';
import { AlertsAdvisoryPage } from './pages/AlertsAdvisoryPage';
import { HistoricalIntelligencePage } from './pages/HistoricalIntelligencePage';
import { CopilotPage } from './pages/CopilotPage';
import { DocumentIngestionPage } from './pages/DocumentIngestionPage';
import { SimulatorPage } from './pages/SimulatorPage';
import { ReportsAnalyticsPage } from './pages/ReportsAnalyticsPage';
import { SystemStatusPage } from './pages/SystemStatusPage';

import { DocsPage } from './docs/DocsPage';

// Lazy-loaded: pulls in three.js + @react-three/fiber (~800kB, same cost as
// WellInspector3DModal), only needed when the user actually opens the 3D
// globe, not on initial load of every page in the app.
const GlobeMapPage = lazy(() =>
  import('./pages/GlobeMapPage').then((m) => ({ default: m.GlobeMapPage }))
);

// The cinematic ("The Well Remembers"). Full-screen, outside the app
// shell, and lazy so none of its code is loaded by the dashboard.
const FilmPage = lazy(() => import('./film/FilmPage'));

// The phased product story (calm, ~66 s): the landing-page candidate.
const StoryPage = lazy(() => import('./story/StoryPage'));

// "/" is the product story (see App below). Everything the app itself does
// lives under /app.
const RoutedContent: React.FC = () => {
  const location = useLocation();
  return (
    <main key={location.pathname} className="flex-1 overflow-y-auto bg-grid-scada page-transition">
      <Routes>
        <Route path="/app" element={<DashboardPage />} />
        <Route path="/app/command-center" element={<CommandCenterPage />} />
        <Route path="/app/drilling" element={<LiveDrillingPage />} />
        <Route path="/app/wells" element={<NearbyWellsPage />} />
        <Route path="/app/offset-map" element={<NwisMapPage />} />
        <Route
          path="/app/globe"
          element={
            <Suspense
              fallback={
                <div className="h-full flex items-center justify-center text-slate-500 font-mono text-xs">
                  Loading 3D globe...
                </div>
              }
            >
              <GlobeMapPage />
            </Suspense>
          }
        />
        <Route path="/app/correlation" element={<GeologicalCorrelationPage />} />
        <Route path="/app/risk" element={<RiskPredictionPage />} />
        <Route path="/app/alerts" element={<AlertsAdvisoryPage />} />
        <Route path="/app/knowledge" element={<HistoricalIntelligencePage />} />
        <Route path="/app/copilot" element={<CopilotPage />} />
        <Route path="/app/documents" element={<DocumentIngestionPage />} />
        <Route path="/app/simulator" element={<SimulatorPage />} />
        <Route path="/app/reports" element={<ReportsAnalyticsPage />} />
        <Route path="/app/status" element={<SystemStatusPage />} />
        <Route path="/app/docs" element={<Navigate to="/docs" replace />} />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </main>
  );
};

const MainAppLayout: React.FC = () => {
  const location = useLocation();
  const isDocs = location.pathname.startsWith('/docs');

  if (isDocs) {
    return (
      <Routes>
        <Route path="/docs" element={<DocsPage />} />
        <Route path="/docs/:slug" element={<DocsPage />} />
        <Route path="*" element={<Navigate to="/docs" replace />} />
      </Routes>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg-main)] text-slate-100 font-sans">
      {/* Left Navigation Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 h-screen overflow-hidden">
        {/* Top Operational Bar */}
        <Header />

        {/* Routed View Surface */}
        <RoutedContent />
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* The film runs without the app shell (no sidebar, header, or the
            AppProvider's telemetry WebSocket and polling). */}
        <Route
          path="/film"
          element={
            <Suspense fallback={<div className="fixed inset-0 bg-black" />}>
              <FilmPage />
            </Suspense>
          }
        />
        {/* The product story is the landing page ("/"); /story stays as an alias. */}
        <Route
          path="/"
          element={
            <Suspense fallback={<div className="fixed inset-0" style={{ background: '#0a0e13' }} />}>
              <StoryPage />
            </Suspense>
          }
        />
        <Route
          path="/story"
          element={
            <Suspense fallback={<div className="fixed inset-0" style={{ background: '#0a0e13' }} />}>
              <StoryPage />
            </Suspense>
          }
        />
        {/* Everything else: the app and the docs, inside the AppProvider. */}
        <Route
          path="*"
          element={
            <AppProvider>
              <MainAppLayout />
            </AppProvider>
          }
        />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
