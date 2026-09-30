import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { NwisProvider } from './state/nwis';
import { Shell } from './ui/Shell';
import { LiveWellView } from './views/LiveWellView';
import { MapView } from './views/MapView';
import { WellView } from './views/WellView';
import { CorrelationView } from './views/CorrelationView';
import { AskView } from './views/AskView';
import { AlertsView } from './views/AlertsView';
import { DocumentsView } from './views/DocumentsView';
import { SensorsView } from './views/SensorsView';

export const App: React.FC = () => (
  <NwisProvider>
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<LiveWellView />} />
          <Route path="/map" element={<MapView />} />
          <Route path="/wells/:wellId" element={<WellView />} />
          <Route path="/correlation" element={<CorrelationView />} />
          <Route path="/ask" element={<AskView />} />
          <Route path="/alerts" element={<AlertsView />} />
          <Route path="/documents" element={<DocumentsView />} />
          <Route path="/sensors" element={<SensorsView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  </NwisProvider>
);

export default App;
