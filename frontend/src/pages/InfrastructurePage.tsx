import React from 'react';
import { 
  Building2, 
  AlertTriangle, 
  ShieldCheck, 
  Route, 
  HeartPulse, 
  Layers, 
  Info
} from 'lucide-react';
import type { SystemHealth } from '../types';

interface InfrastructurePageProps {
  health: SystemHealth | null;
}

export const InfrastructurePage: React.FC<InfrastructurePageProps> = ({ health }) => {
  const osmDate = health?.study_case?.osm_snapshot_date || '2026-07-27';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2">
            <Building2 className="w-6 h-6 text-indigo-400" />
            <span>Infrastructure Exposure Assessment</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Pre-event OpenStreetMap building footprints, road corridors, bridges, and healthcare centers intersecting candidate flood extent.
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs font-mono bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-slate-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>OSM Baseline Snapshot: {osmDate}</span>
        </div>
      </div>

      {/* Critical Scientific Note */}
      <div className="rounded-xl bg-slate-900/90 border border-indigo-900/40 p-4 text-xs text-indigo-200/90 flex items-start space-x-3">
        <Info className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
        <div className="space-y-1">
          <span className="font-semibold text-white">Scientific Distinction of Exposure vs Damage:</span>
          <p className="text-slate-300 leading-relaxed">
            Spatial intersection indicates potential water inundation at or around the ground footprint. 
            An intersecting building or road is reported as <strong>potentially exposed</strong>, not confirmed destroyed. 
            Structural vulnerability, elevation above ground level, and foundation type dictate actual damage.
          </p>
        </div>
      </div>

      {/* Exposure Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-1">
          <div className="flex justify-between items-center text-[11px] font-mono text-slate-400 uppercase">
            <span>Intersecting Buildings</span>
            <Building2 className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">142</div>
          <p className="text-[11px] text-slate-400">Within candidate flood perimeter</p>
        </div>

        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-1">
          <div className="flex justify-between items-center text-[11px] font-mono text-slate-400 uppercase">
            <span>Buffer Zone Buildings (30m)</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-indigo-300">89</div>
          <p className="text-[11px] text-slate-400">Near estimated flood margin</p>
        </div>

        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-1">
          <div className="flex justify-between items-center text-[11px] font-mono text-slate-400 uppercase">
            <span>Intersecting Roadways</span>
            <Route className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-300">18.4 km</div>
          <p className="text-[11px] text-slate-400">Trishuli Highway & feeder roads</p>
        </div>

        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-1">
          <div className="flex justify-between items-center text-[11px] font-mono text-slate-400 uppercase">
            <span>Exposed Bridges</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-300">4</div>
          <p className="text-[11px] text-slate-400">Trishuli & Tadi Khola river crossings</p>
        </div>
      </div>

      {/* Critical Healthcare & Emergency Facilities Table */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center space-x-2">
            <HeartPulse className="w-4 h-4 text-rose-400" />
            <span>Healthcare Facilities & Emergency Services Proximity</span>
          </h2>
          <span className="text-xs font-mono text-slate-400">Coordinate Reference: EPSG:4326</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-sans">
            <thead className="bg-slate-950 text-slate-400 font-mono text-[11px] uppercase border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Facility Name</th>
                <th className="py-2.5 px-3">Type</th>
                <th className="py-2.5 px-3">Location</th>
                <th className="py-2.5 px-3">Exposure Status</th>
                <th className="py-2.5 px-3">Dist. to Inundation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              <tr className="hover:bg-slate-850">
                <td className="py-2.5 px-3 font-medium text-white">Trishuli Hospital</td>
                <td className="py-2.5 px-3">District Hospital</td>
                <td className="py-2.5 px-3 font-mono text-[11px]">Bidur (27.91°N, 85.16°E)</td>
                <td className="py-2.5 px-3">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                    Safe (Elevated Terrace)
                  </span>
                </td>
                <td className="py-2.5 px-3 font-mono text-emerald-400">185 m</td>
              </tr>
              <tr className="hover:bg-slate-850">
                <td className="py-2.5 px-3 font-medium text-white">Battar Health Post</td>
                <td className="py-2.5 px-3">Community Health Post</td>
                <td className="py-2.5 px-3 font-mono text-[11px]">Battar Bazaar (27.88°N, 85.16°E)</td>
                <td className="py-2.5 px-3">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-950 text-amber-300 border border-amber-800">
                    Buffer Zone (30m)
                  </span>
                </td>
                <td className="py-2.5 px-3 font-mono text-amber-400">24 m</td>
              </tr>
              <tr className="hover:bg-slate-850">
                <td className="py-2.5 px-3 font-medium text-white">Devighat Sub-Health Clinic</td>
                <td className="py-2.5 px-3">Sub-Health Post</td>
                <td className="py-2.5 px-3 font-mono text-[11px]">Devighat Confluence (27.86°N, 85.14°E)</td>
                <td className="py-2.5 px-3">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950 text-rose-300 border border-rose-800">
                    Candidate Inundated
                  </span>
                </td>
                <td className="py-2.5 px-3 font-mono text-rose-400">0 m (Intersects)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
