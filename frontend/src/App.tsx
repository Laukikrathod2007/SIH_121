import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';

// Code-split pages: each module loads on demand, dropping initial bundle size
const DashboardPage = lazy(() => import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })));
const CommandCenterPage = lazy(() => import('./pages/CommandCenterPage').then((m) => ({ default: m.CommandCenterPage })));
const LiveDrillingPage = lazy(() => import('./pages/LiveDrillingPage').then((m) => ({ default: m.LiveDrillingPage })));
const NearbyWellsPage = lazy(() => import('./pages/NearbyWellsPage').then((m) => ({ default: m.NearbyWellsPage })));
const NwisMapPage = lazy(() => import('./pages/NwisMapPage').then((m) => ({ default: m.NwisMapPage })));
const GeologicalCorrelationPage = lazy(() => import('./pages/GeologicalCorrelationPage').then((m) => ({ default: m.GeologicalCorrelationPage })));
const RiskPredictionPage = lazy(() => import('./pages/RiskPredictionPage').then((m) => ({ default: m.RiskPredictionPage })));
const AlertsAdvisoryPage = lazy(() => import('./pages/AlertsAdvisoryPage').then((m) => ({ default: m.AlertsAdvisoryPage })));
const HistoricalIntelligencePage = lazy(() => import('./pages/HistoricalIntelligencePage').then((m) => ({ default: m.HistoricalIntelligencePage })));
const CopilotPage = lazy(() => import('./pages/CopilotPage').then((m) => ({ default: m.CopilotPage })));
const DocumentIngestionPage = lazy(() => import('./pages/DocumentIngestionPage').then((m) => ({ default: m.DocumentIngestionPage })));
const SimulatorPage = lazy(() => import('./pages/SimulatorPage').then((m) => ({ default: m.SimulatorPage })));
const ReportsAnalyticsPage = lazy(() => import('./pages/ReportsAnalyticsPage').then((m) => ({ default: m.ReportsAnalyticsPage })));
const SystemStatusPage = lazy(() => import('./pages/SystemStatusPage').then((m) => ({ default: m.SystemStatusPage })));
const DocsPage = lazy(() => import('./docs/DocsPage').then((m) => ({ default: m.DocsPage })));

const GlobeMapPage = lazy(() =>
  import('./pages/GlobeMapPage').then((m) => ({ default: m.GlobeMapPage }))
);

const FilmPage = lazy(() => import('./film/FilmPage'));
const StoryPage = lazy(() => import('./story/StoryPage'));

const PageLoading: React.FC = () => (
  <div className="h-full w-full flex flex-col items-center justify-center p-8 text-slate-400">
    <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-4" />
    <span className="font-mono text-xs tracking-wider text-slate-500">INITIALIZING MODULE INTERFACE...</span>
  </div>
);

// "/" is the product story (see App below). Everything the app itself does
// lives under /app.
const RoutedContent: React.FC = () => {
  const location = useLocation();
  return (
    <main key={location.pathname} className="flex-1 overflow-y-auto bg-grid-scada page-transition">
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/app" element={<DashboardPage />} />
          <Route path="/app/command-center" element={<CommandCenterPage />} />
          <Route path="/app/drilling" element={<LiveDrillingPage />} />
          <Route path="/app/wells" element={<NearbyWellsPage />} />
          <Route path="/app/offset-map" element={<NwisMapPage />} />
          <Route path="/app/globe" element={<GlobeMapPage />} />
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
      </Suspense>
    </main>
  );
};

const MainAppLayout: React.FC = () => {
  const location = useLocation();
  const isDocs = location.pathname.startsWith('/docs');

  if (isDocs) {
    return (
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/docs" element={<DocsPage />} />
          <Route path="/docs/:slug" element={<DocsPage />} />
          <Route path="*" element={<Navigate to="/docs" replace />} />
        </Routes>
      </Suspense>
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
