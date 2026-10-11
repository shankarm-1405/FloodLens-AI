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

const validPages: PageId[] = [
  'overview',
  'flood-analysis',
  'infrastructure',
  'connectivity',
  'ai-report',
  'methodology',
  'limitations'
];

const getInitialPage = (): PageId => {
  if (typeof window === 'undefined') return 'overview';
  const hash = window.location.hash.replace('#', '') as PageId;
  if (validPages.includes(hash)) return hash;
  const params = new URLSearchParams(window.location.search);
  const pageParam = params.get('page') as PageId;
  if (validPages.includes(pageParam)) return pageParam;
  return 'overview';
};

export function App() {
  const [currentPage, setCurrentPage] = useState<PageId>(getInitialPage);
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    const handleHashChange = () => {
      setCurrentPage(getInitialPage());
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handlePageChange = (page: PageId) => {
    setCurrentPage(page);
    window.location.hash = page;
  };

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
        return <OverviewPage onNavigate={handlePageChange} health={health} />;
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
        return <OverviewPage onNavigate={handlePageChange} health={health} />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-cyan-500 selection:text-slate-950 font-sans">
      <Navbar
        currentPage={currentPage}
        onPageChange={handlePageChange}
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
