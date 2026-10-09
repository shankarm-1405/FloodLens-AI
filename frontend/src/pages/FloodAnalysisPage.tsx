import React, { useState, useEffect } from 'react';
import { 
  Radar, 
  Sliders, 
  MapPin, 
  Calendar, 
  Satellite, 
  Play,
  Search,
  CheckCircle2,
  AlertTriangle,
  Cloud,
  Download,
  KeyRound,
  FileCheck2,
  Mountain,
  Layers,
  Sparkles,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import type { 
  SystemHealth, 
  SatelliteSearchResult, 
  CompatiblePair, 
  CredentialsStatus,
  FloodAnalysisResult 
} from '../types';
import { 
  searchSatelliteAcquisitions, 
  fetchCredentialsStatus,
  checkDownloadReadiness,
  triggerFloodAnalysis 
} from '../services/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

interface FloodAnalysisPageProps {
  health: SystemHealth | null;
}

export const FloodAnalysisPage: React.FC<FloodAnalysisPageProps> = ({ health }) => {
  // Query parameters
  const [eventDate, setEventDate] = useState('2026-08-04');
  const [windowDays, setWindowDays] = useState(15);
  const [thresholdDb, setThresholdDb] = useState(-3.2);
  const [minWaterDb, setMinWaterDb] = useState(-14.0);
  const [slopeThreshold, setSlopeThreshold] = useState(15.0);
  const [minLon, setMinLon] = useState(85.05);
  const [minLat, setMinLat] = useState(27.75);
  const [maxLon, setMaxLon] = useState(85.25);
  const [maxLat, setMaxLat] = useState(27.95);
  const [includeOptical, setIncludeOptical] = useState(true);
  const [forceLiveSearch, setForceLiveSearch] = useState(false);

  // Search & Retrieval state
  const [isSearching, setIsSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<SatelliteSearchResult | null>(null);
  const [selectedPair, setSelectedPair] = useState<CompatiblePair | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Credentials & Download state
  const [credentialsStatus, setCredentialsStatus] = useState<CredentialsStatus | null>(null);
  const [downloadModalOpen, setDownloadModalOpen] = useState(false);
  const [downloadChecking, setDownloadChecking] = useState(false);
  const [downloadResult, setDownloadResult] = useState<any | null>(null);

  // SAR Inundation Execution State
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<FloodAnalysisResult | null>(null);

  // Load credentials status on mount
  useEffect(() => {
    fetchCredentialsStatus().then(setCredentialsStatus);
  }, []);

  const handleExecuteSearch = async () => {
    setIsSearching(true);
    setSearchError(null);
    try {
      const res = await searchSatelliteAcquisitions({
        bbox: [minLon, minLat, maxLon, maxLat],
        event_date: eventDate,
        window_days: windowDays,
        include_optical: includeOptical,
        force_live: forceLiveSearch,
      });
      setSearchResult(res);
      if (res.sentinel1.best_compatible_pair) {
        setSelectedPair(res.sentinel1.best_compatible_pair);
      } else if (res.sentinel1.compatible_pairs.length > 0) {
        setSelectedPair(res.sentinel1.compatible_pairs[0]);
      } else {
        setSelectedPair(null);
      }
    } catch (err: any) {
      setSearchError(err.message || 'Error querying satellite catalog');
    } finally {
      setIsSearching(false);
    }
  };

  const handleCheckDownload = async (productId: string) => {
    setDownloadChecking(true);
    try {
      const res = await checkDownloadReadiness(productId);
      setDownloadResult(res);
      setDownloadModalOpen(true);
    } catch (err: any) {
      setDownloadResult({
        status: 'ERROR',
        message: err.message,
        downloaded: false
      });
      setDownloadModalOpen(true);
    } finally {
      setDownloadChecking(false);
    }
  };

  const handleRunAnalysis = async () => {
    if (!selectedPair) return;
    setIsProcessing(true);
    setProcessingError(null);
    try {
      const result = await triggerFloodAnalysis({
        pre_scene: selectedPair.pre_event_scene,
        post_scene: selectedPair.post_event_scene,
        bbox: [minLon, minLat, maxLon, maxLat],
        parameters: {
          threshold_db: thresholdDb,
          min_water_backscatter_db: minWaterDb,
          slope_threshold_deg: slopeThreshold,
          filter_kernel_size: 3,
          min_polygon_pixels: 5,
        },
        is_demo: searchResult?.is_demo_fixture ?? health?.demo_mode ?? true,
      });
      setAnalysisResult(result);
    } catch (err: any) {
      setProcessingError(err.message || 'SAR Inundation processing failed');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2">
            <Radar className="w-6 h-6 text-cyan-400" />
            <span>Sentinel-1 SAR Inundation Extraction Workspace</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Bi-temporal amplitude change detection, DEM terrain shadow masking, and georeferenced raster/vector generation.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {credentialsStatus?.configured ? (
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-mono bg-emerald-950/80 border border-emerald-800 text-emerald-300">
              <KeyRound className="w-3.5 h-3.5" />
              <span>CDSE Auth: Configured</span>
            </span>
          ) : (
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-mono bg-amber-950/80 border border-amber-800 text-amber-300">
              <KeyRound className="w-3.5 h-3.5" />
              <span>CDSE Auth: Metadata Only</span>
            </span>
          )}
        </div>
      </div>

      {/* Main Grid: Discovery & Controls on Left, Results & Map on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Parameters & Satellite Search (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          {/* AOI & Dates Card */}
          <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-cyan-400 font-mono flex items-center space-x-2">
              <MapPin className="w-4 h-4" />
              <span>1. Geographic Area & Flood Anchor</span>
            </h2>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Preset Study Area</label>
                <select 
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-sans"
                  defaultValue="trishuli"
                  onChange={(e) => {
                    if (e.target.value === 'trishuli') {
                      setMinLon(85.05); setMinLat(27.75); setMaxLon(85.25); setMaxLat(27.95);
                    }
                  }}
                >
                  <option value="trishuli">Trishuli Corridor, Nepal [85.05E, 27.75N to 85.25E, 27.95N]</option>
                  <option value="custom">Custom Geographic Bounding Box</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] text-slate-400">Min Lon (West)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={minLon}
                    onChange={(e) => setMinLon(parseFloat(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-slate-400">Min Lat (South)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={minLat}
                    onChange={(e) => setMinLat(parseFloat(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-slate-400">Max Lon (East)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={maxLon}
                    onChange={(e) => setMaxLon(parseFloat(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-slate-400">Max Lat (North)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={maxLat}
                    onChange={(e) => setMaxLat(parseFloat(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 text-xs font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Flood Event Date</label>
                  <input
                    type="date"
                    value={eventDate}
                    onChange={(e) => setEventDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Search Window (± Days)</label>
                  <input
                    type="number"
                    min="2"
                    max="45"
                    value={windowDays}
                    onChange={(e) => setWindowDays(parseInt(e.target.value) || 15)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs font-mono"
                  />
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800 space-y-2">
                <label className="flex items-center space-x-2 cursor-pointer text-slate-300">
                  <input
                    type="checkbox"
                    checked={includeOptical}
                    onChange={(e) => setIncludeOptical(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0"
                  />
                  <span>Discover Sentinel-2 Optical Scenes (Cloud Check)</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer text-slate-300">
                  <input
                    type="checkbox"
                    checked={forceLiveSearch}
                    onChange={(e) => setForceLiveSearch(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-700 text-emerald-500 focus:ring-0"
                  />
                  <span>Force Live Copernicus CDSE Query (Bypass Demo Cache)</span>
                </label>
              </div>

              <button
                id="search-satellite-btn"
                onClick={handleExecuteSearch}
                disabled={isSearching}
                className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-sky-600 to-cyan-500 hover:from-sky-500 hover:to-cyan-400 text-white font-medium text-xs flex items-center justify-center space-x-2 transition-all shadow-md cursor-pointer disabled:opacity-50"
              >
                {isSearching ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Searching Copernicus Catalog...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    <span>Search Satellite Acquisitions</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Search Error Notice */}
          {searchError && (
            <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-xs text-rose-200 flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{searchError}</span>
            </div>
          )}

          {/* Processing Error Notice */}
          {processingError && (
            <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-xs text-rose-200 flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{processingError}</span>
            </div>
          )}

          {/* SAR Change Detection Parameters Card */}
          <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-cyan-400 font-mono flex items-center space-x-2">
              <Sliders className="w-4 h-4" />
              <span>2. Scientific Threshold Parameters</span>
            </h2>

            <div className="space-y-3 text-xs">
              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>Log-Ratio Difference Threshold (Δσ°)</span>
                  <span className="font-mono text-cyan-400 font-bold">{thresholdDb} dB</span>
                </div>
                <input
                  type="range"
                  min="-6.0"
                  max="-1.0"
                  step="0.1"
                  value={thresholdDb}
                  onChange={(e) => setThresholdDb(parseFloat(e.target.value))}
                  className="w-full accent-cyan-500 cursor-pointer"
                />
                <span className="text-[10px] text-slate-400">
                  Strict (-4.0 dB) to Sensitive (-2.5 dB)
                </span>
              </div>

              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>Max Post-Event Water Backscatter</span>
                  <span className="font-mono text-cyan-400 font-bold">{minWaterDb} dB</span>
                </div>
                <input
                  type="range"
                  min="-20.0"
                  max="-10.0"
                  step="0.5"
                  value={minWaterDb}
                  onChange={(e) => setMinWaterDb(parseFloat(e.target.value))}
                  className="w-full accent-cyan-500 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>DEM Slope Shadow Cutoff</span>
                  <span className="font-mono text-cyan-400 font-bold">{slopeThreshold}°</span>
                </div>
                <input
                  type="range"
                  min="8.0"
                  max="30.0"
                  step="1.0"
                  value={slopeThreshold}
                  onChange={(e) => setSlopeThreshold(parseFloat(e.target.value))}
                  className="w-full accent-cyan-500 cursor-pointer"
                />
                <span className="text-[10px] text-slate-400">
                  Slopes &gt; {slopeThreshold}° excluded to eliminate mountain radar shadows.
                </span>
              </div>

              <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                <span className="text-slate-200 font-medium block">Active Product Pair for Execution:</span>
                {selectedPair ? (
                  <div className="space-y-0.5 text-slate-300 font-mono text-[10.5px]">
                    <div>Compatibility: <strong className={selectedPair.compatibility_level === 'OPTIMAL' ? 'text-emerald-400' : 'text-amber-400'}>{selectedPair.compatibility_level}</strong></div>
                    <div>Pre: {selectedPair.pre_event_scene.acquisition_date.split('T')[0]} ({selectedPair.pre_event_scene.orbit_pass}, Track {selectedPair.pre_event_scene.relative_orbit})</div>
                    <div>Post: {selectedPair.post_event_scene.acquisition_date.split('T')[0]} ({selectedPair.post_event_scene.orbit_pass}, Track {selectedPair.post_event_scene.relative_orbit})</div>
                  </div>
                ) : (
                  <span className="italic text-slate-500">Run search to select a compatible satellite pair.</span>
                )}
              </div>

              <button
                id="run-flood-analysis-btn"
                onClick={handleRunAnalysis}
                disabled={isProcessing || !selectedPair}
                className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 to-sky-600 hover:from-cyan-500 hover:to-sky-500 text-white font-medium text-xs flex items-center justify-center space-x-2 shadow-lg shadow-cyan-600/20 cursor-pointer disabled:opacity-50"
              >
                {isProcessing ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Executing Inundation Extraction Engine...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>Generate Flood Extent Raster & Vectors</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Catalog Discovery Results & Extent Output (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          {/* Analysis Result Output Banner if generated */}
          {analysisResult && (
            <div className="rounded-2xl bg-gradient-to-br from-slate-900 to-slate-850 border border-cyan-500/50 p-5 space-y-4 shadow-2xl">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <span className="text-sm font-bold text-white">Flood Extent Analysis Completed</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-950 text-cyan-300 border border-cyan-800">
                    ID: {analysisResult.analysis_id}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                    analysisResult.is_demo_fixture 
                      ? 'bg-amber-950 text-amber-300 border border-amber-800' 
                      : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  }`}>
                    {analysisResult.is_demo_fixture ? 'DEMO FIXTURE' : 'REAL SATELLITE DERIVED'}
                  </span>
                </div>
              </div>

              {/* Exact Computed Area Metric Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Candidate Flood</span>
                  <div className="text-xl font-bold font-mono text-cyan-300 mt-1">
                    {analysisResult.area_statistics.candidate_flood_area_sqkm} km²
                  </div>
                  <span className="text-[10.5px] text-slate-500">Inundated pixels</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Permanent Water</span>
                  <div className="text-xl font-bold font-mono text-blue-400 mt-1">
                    {analysisResult.area_statistics.permanent_water_area_sqkm} km²
                  </div>
                  <span className="text-[10.5px] text-slate-500">Normal riverbeds</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Terrain Masked</span>
                  <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                    {analysisResult.area_statistics.terrain_masked_area_sqkm} km²
                  </div>
                  <span className="text-[10.5px] text-slate-500">DEM slope &gt; {slopeThreshold}°</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Valid Coverage</span>
                  <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                    {Math.round(analysisResult.area_statistics.valid_coverage_ratio * 100)}%
                  </div>
                  <span className="text-[10.5px] text-slate-500">Analyzed sensor grid</span>
                </div>
              </div>

              {/* Download Buttons for Generated Files */}
              <div className="flex flex-wrap gap-2 pt-1 border-t border-slate-800">
                <a
                  href={`${API_BASE}${analysisResult.raster_metadata.geotiff_file}`}
                  download
                  className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-mono flex items-center space-x-1.5 transition-all shadow-sm"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Georeferenced GeoTIFF</span>
                </a>

                <a
                  href={`${API_BASE}${analysisResult.raster_metadata.geojson_file}`}
                  download
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono flex items-center space-x-1.5 transition-all border border-slate-700"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download GeoJSON Layer</span>
                </a>
              </div>

              {/* Scientific Warnings from Analysis */}
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                <span className="font-semibold text-slate-300 block">Uncertainty & Caveats:</span>
                <ul className="list-disc list-inside space-y-0.5 text-slate-400">
                  {analysisResult.warnings_and_uncertainties.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Catalog Search Results Section */}
          {searchResult && (
            <div className="space-y-4">
              {/* Provenance & Mode Banner */}
              <div className={`p-3 rounded-xl border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${
                searchResult.is_demo_fixture 
                  ? 'bg-amber-950/70 border-amber-800 text-amber-200 font-mono'
                  : 'bg-emerald-950/70 border-emerald-800 text-emerald-200'
              }`}>
                <div className="flex items-center space-x-2">
                  <Satellite className="w-4 h-4 text-cyan-400 shrink-0" />
                  <span>
                    <strong>{searchResult.mode}:</strong> {searchResult.provenance.source}
                  </span>
                </div>
                {searchResult.is_demo_fixture && (
                  <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-600/40 text-[10px]">
                    DEMO FIXTURE DATA
                  </span>
                )}
              </div>

              {/* Compatible Pairs & Geometry Analysis */}
              <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-white font-mono flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Sentinel-1 Viewing Geometry Compatibility ({searchResult.sentinel1.compatible_pairs.length} Pairs)</span>
                  </h3>
                  <span className="text-[11px] font-mono text-slate-400">Prioritizes Identical Track & Pass</span>
                </div>

                <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                  {searchResult.sentinel1.compatible_pairs.length === 0 ? (
                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-400">
                      No compatible pre- and post-event Sentinel-1 pair found within the selected ±{windowDays} day window.
                      Try widening the search window.
                    </div>
                  ) : (
                    searchResult.sentinel1.compatible_pairs.map((pair, idx) => {
                      const isSelected = selectedPair?.pre_event_scene.id === pair.pre_event_scene.id && 
                                         selectedPair?.post_event_scene.id === pair.post_event_scene.id;
                      return (
                        <div
                          key={idx}
                          onClick={() => setSelectedPair(pair)}
                          className={`p-3 rounded-xl border transition-all cursor-pointer space-y-2 ${
                            isSelected
                              ? 'bg-cyan-950/40 border-cyan-500 shadow-md shadow-cyan-500/10'
                              : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center space-x-2">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                                pair.compatibility_level === 'OPTIMAL'
                                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                  : pair.compatibility_level === 'SUBOPTIMAL'
                                  ? 'bg-amber-950 text-amber-300 border border-amber-800'
                                  : 'bg-rose-950 text-rose-300 border border-rose-800'
                              }`}>
                                {pair.compatibility_level} ({Math.round(pair.compatibility_score * 100)}%)
                              </span>
                              <span className="text-xs font-semibold text-white">
                                {pair.pre_event_scene.acquisition_date.split('T')[0]} → {pair.post_event_scene.acquisition_date.split('T')[0]}
                              </span>
                            </div>

                            <div className="flex items-center space-x-2">
                              <span className="text-[11px] font-mono text-slate-400">
                                Δ {pair.temporal_separation_days} days
                              </span>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleCheckDownload(pair.post_event_scene.id);
                                }}
                                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-mono flex items-center space-x-1"
                              >
                                <Download className="w-3 h-3 text-cyan-400" />
                                <span>Check CDSE</span>
                              </button>
                            </div>
                          </div>

                          <p className="text-xs text-slate-300 leading-relaxed font-sans">
                            {pair.explanation}
                          </p>

                          <div className="flex flex-wrap gap-2 text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-900">
                            {pair.detailed_criteria.map((crit, cIdx) => (
                              <span key={cIdx} className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
                                • {crit}
                              </span>
                            ))}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Sentinel-2 Optical Evidence Card */}
              {searchResult.sentinel2 && (
                <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-white font-mono flex items-center space-x-2">
                      <Cloud className="w-4 h-4 text-sky-400" />
                      <span>Sentinel-2 Optical Cross-Verification ({searchResult.sentinel2.total_found} Scenes)</span>
                    </h3>
                    <span className="text-[11px] font-mono text-slate-400">MNDWI Water Index Validation</span>
                  </div>

                  <div className="space-y-2">
                    {searchResult.sentinel2.acquisitions.map((s2, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1">
                        <div className="flex justify-between items-center">
                          <span className="font-semibold text-white font-mono">{s2.name.split('_')[0]}_{s2.name.split('_')[1]}</span>
                          <span className="text-slate-400 font-mono text-[11px]">{s2.acquisition_date.split('T')[0]}</span>
                        </div>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-400">Cloud Cover: <strong className={s2.cloud_cover_percentage > 50 ? 'text-amber-400' : 'text-emerald-400'}>{s2.cloud_cover_percentage}%</strong></span>
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                            s2.cloud_cover_percentage < 20 
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' 
                              : 'bg-amber-950 text-amber-300 border border-amber-800'
                          }`}>
                            {s2.recommendation.split('(')[0].trim()}
                          </span>
                        </div>
                        <p className="text-[10.5px] text-slate-400 italic">
                          {s2.recommendation}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Interactive Spatial Canvas */}
          <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
            <div className="px-4 py-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between text-xs font-mono">
              <div className="flex items-center space-x-2">
                <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
                <span className="text-slate-200 font-semibold">Trishuli Spatial Viewport</span>
              </div>
              <span className="text-slate-400 text-[11px]">EPSG:4326 • 10m Ground Resolution</span>
            </div>

            <div className="relative w-full h-[320px] bg-slate-950 flex items-center justify-center overflow-hidden">
              <div className="absolute inset-0 opacity-40 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px]" />
              <div className="relative z-10 text-center space-y-2 bg-slate-900/90 p-5 rounded-xl border border-slate-800 max-w-sm backdrop-blur-md">
                <Radar className="w-8 h-8 text-cyan-400 mx-auto" />
                <h4 className="text-xs font-semibold text-white">
                  {analysisResult 
                    ? `Candidate Flood Mask: ${analysisResult.area_statistics.candidate_flood_area_sqkm} km²` 
                    : 'Spatial View Ready'}
                </h4>
                <p className="text-[11px] text-slate-400">
                  {selectedPair 
                    ? `Pre: ${selectedPair.pre_event_scene.acquisition_date.split('T')[0]} vs Post: ${selectedPair.post_event_scene.acquisition_date.split('T')[0]}`
                    : 'Search satellite catalog to configure pre/post pair'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Download Readiness Modal */}
      {downloadModalOpen && downloadResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-white font-semibold text-sm">
                <KeyRound className="w-4 h-4 text-cyan-400" />
                <span>Copernicus Data Access Status</span>
              </div>
              <button 
                onClick={() => setDownloadModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800"
              >
                ✕ Close
              </button>
            </div>

            <div className="space-y-3 text-xs leading-relaxed text-slate-300">
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono space-y-1">
                <div className="text-slate-400">Product UUID: <span className="text-white">{downloadResult.product_id}</span></div>
                <div className="text-slate-400">Status: <strong className={downloadResult.status === 'AUTHORIZED' ? 'text-emerald-400' : 'text-amber-400'}>{downloadResult.status}</strong></div>
                <div className="text-slate-400">Downloaded: <span className="text-slate-200">{downloadResult.downloaded ? 'Yes (Cached)' : 'No'}</span></div>
              </div>

              <p className="text-slate-300">
                {downloadResult.message}
              </p>

              {downloadResult.setup_guide && (
                <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-[11px] space-y-2">
                  <span className="font-semibold text-cyan-300 block">How to configure live downloads:</span>
                  <p className="text-slate-400">
                    Register a free Copernicus Data Space account at <a href={downloadResult.setup_guide.registration_portal || downloadResult.setup_guide.registration_url || 'https://dataspace.copernicus.eu/'} target="_blank" rel="noreferrer" className="text-cyan-400 underline">{downloadResult.setup_guide.registration_portal || downloadResult.setup_guide.registration_url || 'https://dataspace.copernicus.eu/'}</a> and populate your credentials in your <code>.env</code> file:
                  </p>
                  <pre className="bg-slate-900 p-2 rounded text-slate-200 font-mono text-[10px] overflow-x-auto">
CDSE_USERNAME=your_username
CDSE_PASSWORD=your_password
                  </pre>
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setDownloadModalOpen(false)}
                className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs cursor-pointer"
              >
                Understood
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
