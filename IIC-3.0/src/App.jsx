import React from 'react';
import { Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import AppLayout from './components/AppLayout';
import AnalysisPage from './pages/AnalysisPage';
import HistoryPage from './pages/HistoryPage';
import ReportPage from './pages/ReportPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route element={<AppLayout />}>
        <Route path="/analyze/:caseId" element={<AnalysisPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/report/:caseId" element={<ReportPage />} />
      </Route>
    </Routes>
  );
}

export default App;
