import React from 'react';
import { 
  BookOpen, 
  Radar, 
  Satellite, 
  Mountain, 
  GitFork
} from 'lucide-react';

export const MethodologyPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold text-white flex items-center space-x-2">
          <BookOpen className="w-6 h-6 text-cyan-400" />
          <span>Scientific Methodology & Data Pipeline</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Detailed remote-sensing, geospatial algebra, and topological graph network algorithms implemented in FloodLens AI.
        </p>
      </div>

      {/* Grid of Methodology Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Module 1: Sentinel-1 SAR Change Detection */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center space-x-3 text-cyan-400 font-mono text-sm font-semibold">
            <Radar className="w-5 h-5" />
            <span>1. Sentinel-1 SAR Inundation Detection</span>
          </div>
          <div className="text-xs text-slate-300 space-y-2 leading-relaxed">
            <p>
              Synthetic Aperture Radar (C-SAR, 5.405 GHz) pierces through monsoonal cloud decks. 
              Smooth standing water causes specular reflection away from the satellite antenna, resulting in a distinct decrease in backscatter coefficient (σ°).
            </p>
            <ul className="list-disc list-inside space-y-1 text-slate-400 font-mono text-[11px]">
              <li><strong>Orbit Matching:</strong> Acquisitions must share the same track (Track 121) and pass direction (Descending) to preserve incidence angle geometry.</li>
              <li><strong>Polarization:</strong> Dual-polarization VV + VH utilized. VV is primary for water-land contrast; VH assists in double-bounce urban rejection.</li>
              <li><strong>Log-Ratio Algebra:</strong> Difference raster computed as <code>Δσ° = 10 · log10(σ°_post / σ°_pre)</code>.</li>
              <li><strong>Adaptive Threshold:</strong> Otsu bimodal segmentation combined with minimum difference thresholds (nominally -3.2 dB).</li>
            </ul>
          </div>
        </div>

        {/* Module 2: Copernicus DEM Terrain Masking */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center space-x-3 text-indigo-400 font-mono text-sm font-semibold">
            <Mountain className="w-5 h-5" />
            <span>2. Topographic Shadow & Layover Mask</span>
          </div>
          <div className="text-xs text-slate-300 space-y-2 leading-relaxed">
            <p>
              In extreme Himalayan relief such as the Trishuli gorge, radar shadowing produces very low backscatter that mimics water bodies, 
              while layover foreshortens steep valley walls.
            </p>
            <ul className="list-disc list-inside space-y-1 text-slate-400 font-mono text-[11px]">
              <li><strong>Elevation Source:</strong> Copernicus WorldDEM-30 (30m spatial resolution).</li>
              <li><strong>Slope Masking:</strong> Pixel slopes &gt; 15° are masked out because water cannot accumulate on steep mountain inclines.</li>
              <li><strong>Permanent Water Baselines:</strong> Global Surface Water (GSW) / pre-event river channels are subtracted to isolate candidate floodwater from normal river flow.</li>
            </ul>
          </div>
        </div>

        {/* Module 3: Sentinel-2 Optical Cross-Check */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center space-x-3 text-emerald-400 font-mono text-sm font-semibold">
            <Satellite className="w-5 h-5" />
            <span>3. Optical Sentinel-2 MSI Cross-Check</span>
          </div>
          <div className="text-xs text-slate-300 space-y-2 leading-relaxed">
            <p>
              When cloud cover permits (&lt; 20%), multispectral imagery provides independent validation via the Modified Normalized Difference Water Index (MNDWI):
            </p>
            <div className="p-2.5 rounded bg-slate-950 border border-slate-800 font-mono text-[11px] text-cyan-300">
              MNDWI = (Green [B3] - SWIR1 [B11]) / (Green [B3] + SWIR1 [B11])
            </div>
            <p className="text-slate-400 text-[11px]">
              During monsoon conditions (e.g. August 2026 with 68% cloud cover over Trishuli), the system automatically flags optical data as restricted and relies on SAR.
            </p>
          </div>
        </div>

        {/* Module 4: Road Network Isolation Routing */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center space-x-3 text-amber-400 font-mono text-sm font-semibold">
            <GitFork className="w-5 h-5" />
            <span>4. NetworkX Road Graph Severance Modeling</span>
          </div>
          <div className="text-xs text-slate-300 space-y-2 leading-relaxed">
            <p>
              Pre-event OpenStreetMap road networks are converted into a directed graph <code>G = (V, E)</code> with travel time and distance edge weights.
            </p>
            <ul className="list-disc list-inside space-y-1 text-slate-400 font-mono text-[11px]">
              <li><strong>Historical Snapshot:</strong> Fixed to <strong>2026-07-27</strong> to prevent post-disaster edits from contaminating pre-flood baseline.</li>
              <li><strong>Severance Simulation:</strong> Road segments intersecting the candidate flood mask have their edges either severed (weight = ∞) or heavily penalized.</li>
              <li><strong>Reachability Metric:</strong> Dijkstra shortest path computed from every settlement node to the nearest hospital and administrative hub.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
