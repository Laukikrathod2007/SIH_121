import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { DashboardPage } from './pages/DashboardPage';
import { LiveDrillingPage } from './pages/LiveDrillingPage';
import { NearbyWellsPage } from './pages/NearbyWellsPage';
import { GeologicalCorrelationPage } from './pages/GeologicalCorrelationPage';
import { RiskPredictionPage } from './pages/RiskPredictionPage';
import { AlertsAdvisoryPage } from './pages/AlertsAdvisoryPage';
import { HistoricalIntelligencePage } from './pages/HistoricalIntelligencePage';
import { CopilotPage } from './pages/CopilotPage';
import { DocumentIngestionPage } from './pages/DocumentIngestionPage';
import { SimulatorPage } from './pages/SimulatorPage';
import { ReportsAnalyticsPage } from './pages/ReportsAnalyticsPage';
import { SystemStatusPage } from './pages/SystemStatusPage';

const RoutedContent: React.FC = () => {
  const location = useLocation();
  return (
    <main key={location.pathname} className="flex-1 overflow-y-auto bg-grid-scada page-transition">
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/drilling" element={<LiveDrillingPage />} />
        <Route path="/wells" element={<NearbyWellsPage />} />
        <Route path="/correlation" element={<GeologicalCorrelationPage />} />
        <Route path="/risk" element={<RiskPredictionPage />} />
        <Route path="/alerts" element={<AlertsAdvisoryPage />} />
        <Route path="/knowledge" element={<HistoricalIntelligencePage />} />
        <Route path="/copilot" element={<CopilotPage />} />
        <Route path="/documents" element={<DocumentIngestionPage />} />
        <Route path="/simulator" element={<SimulatorPage />} />
        <Route path="/reports" element={<ReportsAnalyticsPage />} />
        <Route path="/status" element={<SystemStatusPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </main>
  );
};

export const App: React.FC = () => {
  return (
    <AppProvider>
      <BrowserRouter>
        <div className="flex h-screen w-screen overflow-hidden bg-[#0b0e14] text-slate-100 font-sans">
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
      </BrowserRouter>
    </AppProvider>
  );
};

export default App;
