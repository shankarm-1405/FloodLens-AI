import React from 'react';
import { AlertTriangle, Database, Info, Layers } from 'lucide-react';
import type { SystemHealth } from '../types';

interface StatusBannerProps {
  health: SystemHealth | null;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({ health }) => {
  const isDemo = health?.demo_mode ?? true;

  return (
    <aside aria-label="Operational status notification" className="w-full bg-slate-900 border-b border-slate-800">
      {isDemo ? (
        <div className="bg-gradient-to-r from-amber-950/80 via-amber-900/50 to-amber-950/80 border-b border-amber-600/40 px-4 py-2 text-xs text-amber-200">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
            <div className="flex items-center space-x-2 font-mono">
              <span className="inline-flex items-center px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40 animate-pulse">
                <AlertTriangle className="w-3.5 h-3.5 mr-1" />
                DEMONSTRATION DATA — NOT REAL FLOOD ANALYSIS
              </span>
              <span className="hidden md:inline text-amber-300/80">
                Operating in illustrative fixture mode for workflow evaluation. Not an authoritative flood assessment.
              </span>
            </div>
            <div className="flex items-center space-x-3 text-[11px] font-mono text-amber-400/90">
              <span>Study Case: Trishuli River Corridor, Nepal</span>
              <span className="text-amber-500/40">|</span>
              <span>Event Date: August 2026</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-emerald-950/60 border-b border-emerald-700/40 px-4 py-2 text-xs text-emerald-200">
          <div className="max-w-7xl mx-auto flex items-center justify-between font-mono">
            <div className="flex items-center space-x-2">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              <span className="font-semibold text-emerald-300">REAL DATA MODE:</span>
              <span>Connected to Copernicus Data Space Ecosystem & OpenStreetMap Historical Snapshot (2026-07-27).</span>
            </div>
            <div className="text-[11px] text-emerald-400/80">
              Target: Trishuli Corridor (85.05E, 27.75N)
            </div>
          </div>
        </div>
      )}

      {/* Geospatial stack indicator mini-bar */}
      <div className="max-w-7xl mx-auto px-4 py-1.5 flex flex-wrap items-center justify-between text-[11px] text-slate-400 font-mono">
        <div className="flex items-center space-x-4">
          <span className="flex items-center space-x-1">
            <Layers className="w-3 h-3 text-cyan-400" />
            <span className="text-slate-300">Geospatial Backend:</span>
          </span>
          <span className="space-x-2 text-slate-400">
            <span className={health?.geospatial_stack?.rasterio?.available ? 'text-emerald-400' : 'text-rose-400'}>
              rasterio {health?.geospatial_stack?.rasterio?.available ? '✓' : '✗'}
            </span>
            <span>•</span>
            <span className={health?.geospatial_stack?.shapely?.available ? 'text-emerald-400' : 'text-rose-400'}>
              shapely {health?.geospatial_stack?.shapely?.available ? '✓' : '✗'}
            </span>
            <span>•</span>
            <span className={health?.geospatial_stack?.geopandas?.available ? 'text-emerald-400' : 'text-rose-400'}>
              geopandas {health?.geospatial_stack?.geopandas?.available ? '✓' : '✗'}
            </span>
            <span>•</span>
            <span className={health?.geospatial_stack?.networkx?.available ? 'text-emerald-400' : 'text-rose-400'}>
              networkx {health?.geospatial_stack?.networkx?.available ? '✓' : '✗'}
            </span>
          </span>
        </div>
        <div className="flex items-center space-x-2 text-slate-400">
          <Info className="w-3 h-3 text-slate-400" />
          <span>OSM Baseline Snapshot: {health?.study_case?.osm_snapshot_date || '2026-07-27'}</span>
        </div>
      </div>
    </aside>
  );
};
