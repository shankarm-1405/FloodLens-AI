import React from 'react';
import type { PageId, SystemHealth } from '../types';
import { 
  Radar, 
  Building2, 
  GitFork, 
  FileText, 
  BookOpen, 
  ShieldAlert, 
  Activity,
  Satellite
} from 'lucide-react';

interface NavbarProps {
  currentPage: PageId;
  onPageChange: (page: PageId) => void;
  health: SystemHealth | null;
}

export const Navbar: React.FC<NavbarProps> = ({ currentPage, onPageChange, health }) => {
  const isHealthy = health?.status === 'healthy';
  const isOffline = health?.status === 'offline';
  const isDemo = health?.demo_mode ?? true;

  const navItems: { id: PageId; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'flood-analysis', label: 'Flood Analysis', icon: Radar },
    { id: 'infrastructure', label: 'Infrastructure', icon: Building2 },
    { id: 'connectivity', label: 'Connectivity', icon: GitFork },
    { id: 'ai-report', label: 'Situation Report', icon: FileText },
    { id: 'methodology', label: 'Methodology', icon: BookOpen },
    { id: 'limitations', label: 'Limitations & Validation', icon: ShieldAlert },
  ];

  return (
    <header className="sticky top-0 z-50 bg-slate-900/95 backdrop-blur-md border-b border-slate-800 text-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onPageChange('overview')}>
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-sky-600 via-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Satellite className="h-6 w-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight text-white font-sans">FloodLens<span className="text-cyan-400">AI</span></span>
                <span className="text-[10px] font-mono uppercase bg-slate-800 text-cyan-300 border border-cyan-800/60 px-1.5 py-0.5 rounded">
                  Track B
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono hidden sm:block">Sentinel SAR & Optical Damage Mapping</p>
            </div>
          </div>

          <nav className="hidden lg:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  id={`nav-${item.id}`}
                  onClick={() => onPageChange(item.id)}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    active
                      ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-sm'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/70 border border-transparent'
                  }`}
                >
                  <Icon className={`h-4 w-4 ${active ? 'text-cyan-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="flex items-center space-x-2">
            <div
              className={`px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold uppercase tracking-wider border ${
                isDemo
                  ? 'bg-amber-950/60 text-amber-300 border-amber-700/60'
                  : 'bg-emerald-950/60 text-emerald-300 border-emerald-700/60'
              }`}
              title={isDemo ? 'Running in offline fixture mode' : 'Connected to live Copernicus CDSE'}
            >
              {isDemo ? 'Demo Mode' : 'Live Data'}
            </div>

            <div
              className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono border ${
                isOffline
                  ? 'bg-rose-950/60 text-rose-300 border-rose-800/60'
                  : isHealthy
                  ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                  : 'bg-amber-950/60 text-amber-300 border-amber-800/60'
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  isOffline
                    ? 'bg-rose-500 animate-ping'
                    : isHealthy
                    ? 'bg-emerald-400'
                    : 'bg-amber-400'
                }`}
              />
              <span className="hidden sm:inline">
                {isOffline ? 'Backend Offline' : isHealthy ? 'Engine Active' : 'Degraded'}
              </span>
            </div>
          </div>
        </div>

        <div className="lg:hidden flex items-center space-x-1 overflow-x-auto py-2 border-t border-slate-800/80">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onPageChange(item.id)}
                className={`flex items-center space-x-1 px-2.5 py-1 rounded text-xs whitespace-nowrap ${
                  active ? 'bg-cyan-500/20 text-cyan-300 font-medium' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
