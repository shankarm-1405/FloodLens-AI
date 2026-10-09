import React from 'react';
import type { PageId, SystemHealth } from '../types';
import { 
  Radar, 
  Building2, 
  GitFork, 
  FileText, 
  ArrowRight, 
  MapPin, 
  CheckCircle2,
  Mountain,
  Satellite
} from 'lucide-react';

interface OverviewPageProps {
  onNavigate: (page: PageId) => void;
  health: SystemHealth | null;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ onNavigate, health: _health }) => {
  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-850 to-slate-900 border border-slate-800 p-6 sm:p-10 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-800/80 text-cyan-300 text-xs font-mono">
            <Satellite className="w-3.5 h-3.5" />
            <span>Track B: Multimodal Satellite Earth Observation</span>
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white">
            Operational Rapid Flood Damage & Settlement Isolation Mapping
          </h1>
          <p className="text-base sm:text-lg text-slate-300 leading-relaxed font-normal">
            FloodLens AI integrates pre- and post-event Sentinel-1 Synthetic Aperture Radar (SAR), 
            Sentinel-2 optical validation, and OpenStreetMap historical graphs to detect inundated terrain, 
            quantify infrastructure exposure, and identify disconnected settlements in complex topography.
          </p>

          <div className="flex flex-wrap gap-3 pt-2">
            <button
              onClick={() => onNavigate('flood-analysis')}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-sky-600 to-cyan-500 hover:from-sky-500 hover:to-cyan-400 text-white font-medium text-sm transition-all shadow-lg shadow-cyan-500/25 cursor-pointer"
            >
              <span>Launch Flood Analysis</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => onNavigate('ai-report')}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-medium text-sm transition-all cursor-pointer"
            >
              <FileText className="w-4 h-4 text-cyan-400" />
              <span>Generate Situation Report</span>
            </button>
          </div>
        </div>
      </section>

      {/* Case Study Callout */}
      <section className="rounded-xl bg-slate-900/90 border border-slate-800 p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start space-x-3">
            <div className="p-2.5 rounded-lg bg-sky-950 border border-sky-800/70 text-sky-400 mt-0.5">
              <Mountain className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-sm font-semibold text-white">Primary Benchmark Case Study</span>
                <span className="px-2 py-0.5 text-[10px] font-mono bg-sky-950 text-sky-300 rounded border border-sky-800">
                  Nepal Monsoonal Surge
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1">
                <strong>Trishuli River Corridor (Bagmati / Gandaki Province)</strong>: Flash flooding and debris flow along steep riverine valleys.
                OSM baseline snapshot anchored to <strong>July 27, 2026</strong>; satellite monitoring centered around <strong>August 2026</strong>.
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3 text-xs font-mono text-slate-400 bg-slate-950/80 px-3 py-2 rounded-lg border border-slate-800">
            <div className="flex items-center space-x-1.5">
              <MapPin className="w-3.5 h-3.5 text-cyan-400" />
              <span>BBox: [85.05, 27.75, 85.25, 27.95]</span>
            </div>
          </div>
        </div>
      </section>

      {/* Workflow Step Cards */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">Multimodal Pipeline Modules</h2>
          <span className="text-xs text-slate-400 font-mono">End-to-End Analysis Workflow</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Step 1 */}
          <div 
            onClick={() => onNavigate('flood-analysis')}
            className="group cursor-pointer rounded-xl bg-slate-900/80 hover:bg-slate-850 border border-slate-800 hover:border-cyan-500/50 p-5 transition-all shadow-md hover:shadow-cyan-500/10 space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-cyan-950/80 text-cyan-400 border border-cyan-800/80">
                <Radar className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-mono text-slate-400 group-hover:text-cyan-400">Step 01</span>
            </div>
            <div>
              <h3 className="font-semibold text-white group-hover:text-cyan-300 text-sm">SAR Flood Extent</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Sentinel-1 C-band SAR amplitude log-ratio change detection with Otsu thresholding and DEM terrain shadow masking.
              </p>
            </div>
          </div>

          {/* Step 2 */}
          <div 
            onClick={() => onNavigate('infrastructure')}
            className="group cursor-pointer rounded-xl bg-slate-900/80 hover:bg-slate-850 border border-slate-800 hover:border-cyan-500/50 p-5 transition-all shadow-md hover:shadow-cyan-500/10 space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-indigo-950/80 text-indigo-400 border border-indigo-800/80">
                <Building2 className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-mono text-slate-400 group-hover:text-cyan-400">Step 02</span>
            </div>
            <div>
              <h3 className="font-semibold text-white group-hover:text-cyan-300 text-sm">Infrastructure Exposure</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Intersection of pre-event OSM buildings, roadways, and bridge assets against candidate flood extent.
              </p>
            </div>
          </div>

          {/* Step 3 */}
          <div 
            onClick={() => onNavigate('connectivity')}
            className="group cursor-pointer rounded-xl bg-slate-900/80 hover:bg-slate-850 border border-slate-800 hover:border-cyan-500/50 p-5 transition-all shadow-md hover:shadow-cyan-500/10 space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-amber-950/80 text-amber-400 border border-amber-800/80">
                <GitFork className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-mono text-slate-400 group-hover:text-cyan-400">Step 03</span>
            </div>
            <div>
              <h3 className="font-semibold text-white group-hover:text-cyan-300 text-sm">Cut-Off Settlements</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Graph network routing model isolating remote villages losing vehicular connectivity to district hospitals and towns.
              </p>
            </div>
          </div>

          {/* Step 4 */}
          <div 
            onClick={() => onNavigate('ai-report')}
            className="group cursor-pointer rounded-xl bg-slate-900/80 hover:bg-slate-850 border border-slate-800 hover:border-cyan-500/50 p-5 transition-all shadow-md hover:shadow-cyan-500/10 space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-emerald-950/80 text-emerald-400 border border-emerald-800/80">
                <FileText className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-mono text-slate-400 group-hover:text-cyan-400">Step 04</span>
            </div>
            <div>
              <h3 className="font-semibold text-white group-hover:text-cyan-300 text-sm">Bilingual Situation Report</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Grounded English & Nepali disaster response synthesis strictly referencing backend calculated figures.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Provenance & Scientific Rigor Card */}
      <section className="rounded-xl bg-slate-900/80 border border-slate-800 p-6 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-cyan-400 font-mono">
          Scientific Principles & Hackathon Guardrails
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300 leading-relaxed">
          <div className="flex items-start space-x-3 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
            <div>
              <span className="font-semibold text-slate-100">Separation of Candidate Mask from Ground Truth:</span>
              <p className="mt-1 text-slate-400">
                Radar returns reflect specular surface reflection. All output masks are labeled as candidate flood estimates, 
                accounting for radar shadow, monsoonal wet soil, and layover distortions in Himalayan terrain.
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
            <div>
              <span className="font-semibold text-slate-100">Strict Pre-Event OSM Baseline Integrity:</span>
              <p className="mt-1 text-slate-400">
                Infrastructure graphs are pinned to the July 27, 2026 historical snapshot. Post-disaster OSM edits and EMSR927 maps 
                are strictly excluded from analysis inputs to prevent target leakage.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
