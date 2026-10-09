import { useState, useEffect } from 'react';
import type { PageId, SystemHealth } from './types';
import { checkBackendHealth } from './services/api';
import { Navbar } from './components/Navbar';
import { StatusBanner } from './components/StatusBanner';
import { Footer } from './components/Footer';

import { OverviewPage } from './pages/OverviewPage';
import { FloodAnalysisPage } from './pages/FloodAnalysisPage';
import { InfrastructurePage } from './pages/InfrastructurePage';
import { ConnectivityPage } from './pages/ConnectivityPage';
import { ReportPage } from './pages/ReportPage';
import { MethodologyPage } from './pages/MethodologyPage';
import { LimitationsPage } from './pages/LimitationsPage';

export function App() {
  const [currentPage, setCurrentPage] = useState<PageId>('overview');
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    checkBackendHealth().then(setHealth);

    const interval = setInterval(() => {
      checkBackendHealth().then(setHealth);
    }, 15000);

    return () => clearInterval(interval);
  }, []);

  const renderActivePage = () => {
    switch (currentPage) {
      case 'overview':
        return <OverviewPage onNavigate={setCurrentPage} health={health} />;
      case 'flood-analysis':
        return <FloodAnalysisPage health={health} />;
      case 'infrastructure':
        return <InfrastructurePage health={health} />;
      case 'connectivity':
        return <ConnectivityPage health={health} />;
      case 'ai-report':
        return <ReportPage health={health} />;
      case 'methodology':
        return <MethodologyPage />;
      case 'limitations':
        return <LimitationsPage />;
      default:
        return <OverviewPage onNavigate={setCurrentPage} health={health} />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-cyan-500 selection:text-slate-950 font-sans">
      <Navbar
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        health={health}
      />

      <StatusBanner health={health} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderActivePage()}
      </main>

      <Footer />
    </div>
  );
}

export default App;
