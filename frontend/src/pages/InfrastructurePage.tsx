import React, { useState, useEffect } from 'react';
import { 
  Building2, 
  AlertTriangle, 
  ShieldCheck, 
  Route, 
  HeartPulse, 
  Layers, 
  Info,
  Download,
  Play,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  FileJson
} from 'lucide-react';
import type { SystemHealth, InfrastructureExposureSummary } from '../types';
import { InfrastructureMap } from '../components/InfrastructureMap';
import { 
  triggerInfrastructureAnalysis, 
  fetchInfrastructureSummary, 
  fetchInfrastructureStatus 
} from '../services/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

interface InfrastructurePageProps {
  health: SystemHealth | null;
}

export const InfrastructurePage: React.FC<InfrastructurePageProps> = ({ health }) => {
  const defaultSnapshotDate = health?.study_case?.osm_snapshot_date || '2026-07-27';
  const defaultBbox = health?.study_case?.default_bbox || [85.05, 27.75, 85.25, 27.95];

  // Retrieve last analysis ID if available, default to existing e2e fixture
  const [analysisId, setAnalysisId] = useState<string>(() => {
    return localStorage.getItem('floodlens_last_analysis_id') || 'e2e-trishuli-aug2026';
  });

  const [osmSource, setOsmSource] = useState<'historical' | 'current_preview'>('historical');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<InfrastructureExposureSummary | null>(null);

  // Auto-fetch summary if analysis output already exists on disk
  const loadExistingSummary = async (targetId: string) => {
    if (!targetId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      // Check status first
      const statusRes = await fetchInfrastructureStatus(targetId.trim());
      if (statusRes.outputs_ready) {
        const data = await fetchInfrastructureSummary(targetId.trim());
        setSummary(data);
      } else {
        // If not analyzed yet, run analysis automatically
        const data = await triggerInfrastructureAnalysis({
          analysis_id: targetId.trim(),
          osm_source: osmSource,
          allow_fallback_fixture: true
        });
        setSummary(data);
      }
    } catch (err: any) {
      // Try running analysis if status was 404 or not ready
      try {
        const data = await triggerInfrastructureAnalysis({
          analysis_id: targetId.trim(),
          osm_source: osmSource,
          allow_fallback_fixture: true
        });
        setSummary(data);
      } catch (runErr: any) {
        setError(runErr?.message || 'Could not load or run infrastructure exposure assessment.');
        setSummary(null);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExistingSummary(analysisId);
  }, []);

  const handleRunAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!analysisId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await triggerInfrastructureAnalysis({
        analysis_id: analysisId.trim(),
        osm_source: osmSource,
        allow_fallback_fixture: true
      });
      setSummary(data);
      localStorage.setItem('floodlens_last_analysis_id', analysisId.trim());
    } catch (err: any) {
      setError(err?.message || 'Exposure assessment execution failed.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'DIRECTLY_INTERSECTING':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-950/80 text-rose-300 border border-rose-800 flex items-center space-x-1">
            <AlertCircle className="w-3 h-3 text-rose-400" />
            <span>Directly Intersecting</span>
          </span>
        );
      case 'BUFFER_ZONE_30M':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-950/80 text-amber-300 border border-amber-800 flex items-center space-x-1">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            <span>Buffer Zone (≤30m)</span>
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800 flex items-center space-x-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            <span>Safe (Elevated)</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2">
            <Building2 className="w-6 h-6 text-indigo-400" />
            <span>Historical OSM Infrastructure Exposure Assessment</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Spatial overlay of pre-event OpenStreetMap building footprints, road corridors, bridges, and emergency healthcare facilities against Sentinel-1 candidate flood extents.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center space-x-1.5 text-xs font-mono bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-slate-300">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>OSM Snapshot: {summary?.osm_snapshot_date || defaultSnapshotDate}</span>
          </div>
          <div className="text-[11px] font-mono text-slate-400 bg-slate-900/60 border border-slate-800/80 px-2.5 py-1.5 rounded-lg">
            © OpenStreetMap contributors.
          </div>
        </div>
      </div>

      {/* Analysis Target Control Panel */}
      <div className="rounded-xl bg-slate-900/90 border border-slate-800 p-4 space-y-3">
        <form onSubmit={handleRunAnalysis} className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex flex-1 flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex-1">
              <label className="block text-[11px] font-mono text-slate-400 uppercase mb-1">
                Phase 3 Flood Analysis ID
              </label>
              <input
                type="text"
                value={analysisId}
                onChange={(e) => setAnalysisId(e.target.value)}
                placeholder="e.g. e2e-trishuli-aug2026"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="sm:w-64">
              <label className="block text-[11px] font-mono text-slate-400 uppercase mb-1">
                OSM Infrastructure Source
              </label>
              <select
                value={osmSource}
                onChange={(e) => setOsmSource(e.target.value as any)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="historical">Pre-Event Historical Baseline (27 July 2026)</option>
                <option value="current_preview">Current OSM Live Preview (Non-Historical)</option>
              </select>
            </div>
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={loading || !analysisId.trim()}
              className="w-full sm:w-auto px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium flex items-center justify-center space-x-2 transition-colors shadow-lg shadow-indigo-600/20"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Computing Exposure...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5" />
                  <span>Run Exposure Assessment</span>
                </>
              )}
            </button>
          </div>
        </form>

        {error && (
          <div className="rounded-lg bg-rose-950/40 border border-rose-800/60 p-3 text-xs text-rose-300 flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
            <div className="space-y-0.5">
              <span className="font-semibold text-rose-200">Analysis Execution Error:</span>
              <p>{error}</p>
            </div>
          </div>
        )}
      </div>

      {/* Provenance and Data Notice Banner */}
      {summary && (
        <div>
          {summary.provenance === 'SYNTHETIC_TEST_FIXTURE' && (
            <div className="rounded-xl bg-amber-950/30 border border-amber-800/60 p-4 text-xs text-amber-200 flex items-start space-x-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-amber-300 uppercase tracking-wide">
                    PROVENANCE: SYNTHETIC TEST FIXTURE
                  </span>
                  <span className="px-2 py-0.5 bg-amber-900/60 border border-amber-700/80 rounded text-[10px] font-mono">
                    DEMO SAR MASK
                  </span>
                </div>
                <p className="text-amber-200/90 leading-relaxed">
                  The Sentinel-1 water mask in this analysis is a synthetic demonstration fixture. 
                  Exposure figures below illustrate pipeline spatial verification and must <strong>not</strong> be reported as real-world Trishuli flood observations.
                </p>
              </div>
            </div>
          )}

          {summary.provenance === 'CURRENT_OSM_PREVIEW' && (
            <div className="rounded-xl bg-cyan-950/30 border border-cyan-800/60 p-4 text-xs text-cyan-200 flex items-start space-x-3">
              <Info className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-cyan-300 uppercase tracking-wide">
                    PROVENANCE: CURRENT OSM PREVIEW
                  </span>
                  <span className="px-2 py-0.5 bg-cyan-900/60 border border-cyan-700/80 rounded text-[10px] font-mono">
                    LIVE OVERPASS
                  </span>
                </div>
                <p className="text-cyan-200/90 leading-relaxed">
                  This analysis was run against current OpenStreetMap infrastructure rather than the pre-event historical baseline (27 July 2026). 
                  Recent construction or post-event edits may be present.
                </p>
              </div>
            </div>
          )}

          {(summary.provenance === 'REAL_DATA_ANALYSIS' || summary.provenance === 'VERIFIED_HISTORICAL_OSM' || summary.provenance === 'REAL_SATELLITE_DERIVED') && (
            <div className="rounded-xl bg-emerald-950/30 border border-emerald-800/60 p-4 text-xs text-emerald-200 flex items-start space-x-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-emerald-300 uppercase tracking-wide">
                    PROVENANCE: REAL SATELLITE & VERIFIED HISTORICAL OSM
                  </span>
                </div>
                <p className="text-emerald-200/90 leading-relaxed">
                  Analysis computed using validated pre- and post-event Sentinel-1 radar scenes and verified pre-event OpenStreetMap infrastructure.
                </p>
              </div>
            </div>
          )}

          {(summary.provenance === 'UNAVAILABLE' || summary.provenance === 'HISTORICAL_SNAPSHOT_UNAVAILABLE') && (
            <div className="rounded-xl bg-rose-950/40 border border-rose-800/80 p-4 text-xs text-rose-200 flex items-start space-x-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-rose-300 uppercase tracking-wide">
                    PROVENANCE: UNAVAILABLE
                  </span>
                </div>
                <p className="text-rose-200/90 leading-relaxed">
                  Required historical infrastructure baseline data could not be retrieved. Metric calculations are withheld as UNAVAILABLE rather than substituting fabricated zeros.
                </p>
              </div>
            </div>
          )}

          {summary.status === 'BLOCKED' && (
            <div className="rounded-xl bg-rose-950/40 border border-rose-800 p-4 text-xs text-rose-200 flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-bold text-rose-300 uppercase tracking-wide">
                  ANALYSIS BLOCKED: HISTORICAL DATA UNAVAILABLE
                </span>
                <p className="text-rose-200/90 leading-relaxed">
                  {summary.blocker_reason || 'Remote historical archive timed out. Exposure totals suppressed to avoid fabricating unverified data.'}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Critical Scientific Note on Terminology */}
      <div className="rounded-xl bg-slate-900/90 border border-indigo-900/40 p-4 text-xs text-indigo-200/90 flex items-start space-x-3">
        <Info className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
        <div className="space-y-1">
          <span className="font-semibold text-white">Scientific Distinction: Potentially Exposed vs Confirmed Damage</span>
          <p className="text-slate-300 leading-relaxed">
            Spatial intersection indicates potential water inundation at or around the ground footprint. 
            An intersecting building or road is reported as <strong>potentially exposed infrastructure</strong>, not confirmed destroyed. 
            Structural design, building elevation above ground level, and river embankment height dictate actual structural vulnerability.
          </p>
        </div>
      </div>

      {/* Exposure Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Buildings Metric */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-1">
          <div className="flex justify-between items-center text-[11px] font-mono text-slate-400 uppercase">
            <span>Potentially Exposed Buildings</span>
            <Building2 className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {summary?.exposed_buildings_count !== null && summary?.exposed_buildings_count !== undefined 
              ? summary.exposed_buildings_count 
              : '—'}
          </div>
          <p className="text-[11px] text-slate-400 font-mono">
            {summary?.exposed_building_area_sqm !== null && summary?.exposed_building_area_sqm !== undefined
              ? `${summary.exposed_building_area_sqm.toLocaleString()} m² footprint (${summary.exposed_building_area_sqkm} km²)`
              : 'Footprint area unavailable'}
          </p>
        </div>

        {/* Roadways Metric */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-1">
          <div className="flex justify-between items-center text-[11px] font-mono text-slate-400 uppercase">
            <span>Potentially Exposed Roads</span>
            <Route className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-300">
            {summary?.exposed_road_length_km !== null && summary?.exposed_road_length_km !== undefined 
              ? `${summary.exposed_road_length_km} km` 
              : '—'}
          </div>
          <p className="text-[11px] text-slate-400 font-mono">
            Clipped Trishuli Highway & feeder roads
          </p>
        </div>

        {/* Bridges Metric */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-1">
          <div className="flex justify-between items-center text-[11px] font-mono text-slate-400 uppercase">
            <span>Potentially Exposed Bridges</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-300">
            {summary?.exposed_bridges_count !== null && summary?.exposed_bridges_count !== undefined 
              ? summary.exposed_bridges_count 
              : '—'}
          </div>
          <p className="text-[11px] text-slate-400">
            Trishuli & Tadi Khola river crossings
          </p>
        </div>

        {/* Healthcare & Facilities Metric */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-1">
          <div className="flex justify-between items-center text-[11px] font-mono text-slate-400 uppercase">
            <span>Critical Facilities at Risk</span>
            <HeartPulse className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-300">
            {summary?.critical_facilities_intersecting !== null && summary?.critical_facilities_intersecting !== undefined
              ? `${summary.critical_facilities_intersecting + (summary.critical_facilities_in_buffer || 0)} / ${summary.critical_facilities_assessed}`
              : '—'}
          </div>
          <p className="text-[11px] text-slate-400 font-mono">
            {summary ? `${summary.critical_facilities_intersecting} intersecting, ${summary.critical_facilities_in_buffer} in 30m buffer` : 'Proximity evaluation'}
          </p>
        </div>
      </div>

      {/* Total Infrastructure Assessed Metadata Bar */}
      {summary && (
        <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 border border-slate-800/80 px-4 py-2.5 rounded-xl text-xs font-mono text-slate-400">
          <div className="flex items-center space-x-4">
            <span>Total Assessed: <strong className="text-white">{summary.total_infrastructure_assessed}</strong></span>
            <span>Valid Geometries: <strong className="text-emerald-400">{summary.valid_geometry_count}</strong></span>
            {summary.invalid_geometry_count > 0 && (
              <span>Repaired/Dropped: <strong className="text-amber-400">{summary.invalid_geometry_count}</strong></span>
            )}
          </div>
          <div className="flex items-center space-x-2 text-[11px]">
            <span>CRS: <strong className="text-cyan-400">EPSG:32645 (UTM 45N Metric)</strong></span>
          </div>
        </div>
      )}

      {/* Interactive Map */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center space-x-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span>Interactive Geospatial Exposure Map</span>
          </h2>
          <span className="text-xs font-mono text-slate-400">Trishuli River Corridor Bounding Box</span>
        </div>
        <InfrastructureMap
          bbox={summary?.aoi_bbox || defaultBbox}
          analysisId={analysisId}
          summary={summary}
          className="h-[520px]"
        />
      </div>

      {/* Critical Healthcare & Emergency Facilities Table */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-white flex items-center space-x-2">
              <HeartPulse className="w-4 h-4 text-rose-400" />
              <span>Critical Healthcare & Emergency Facilities Proximity</span>
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Automated geodesic proximity classification against candidate flood perimeters.
            </p>
          </div>
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
                <th className="py-2.5 px-3">Beds / Emergency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {summary?.critical_facilities_details && summary.critical_facilities_details.length > 0 ? (
                summary.critical_facilities_details.map((fac) => (
                  <tr key={String(fac.osm_id)} className="hover:bg-slate-850/50 transition-colors">
                    <td className="py-2.5 px-3 font-medium text-white">{fac.name}</td>
                    <td className="py-2.5 px-3 capitalize text-slate-300">{fac.facility_type}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">
                      {fac.coordinates[1].toFixed(4)}°N, {fac.coordinates[0].toFixed(4)}°E
                    </td>
                    <td className="py-2.5 px-3">
                      {getStatusBadge(fac.exposure_status)}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      {fac.distance_to_flood_m === 0 ? (
                        <span className="text-rose-400 font-bold">0.0 m (Intersects)</span>
                      ) : fac.distance_to_flood_m <= 30 ? (
                        <span className="text-amber-400 font-semibold">{fac.distance_to_flood_m} m</span>
                      ) : (
                        <span className="text-emerald-400">{fac.distance_to_flood_m} m</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 font-mono text-[11px]">
                      {fac.beds && fac.beds !== 'N/A' ? `${fac.beds} beds` : 'N/A'} 
                      {fac.emergency === 'yes' ? ' • Emergency: Yes' : ''}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-500 font-mono text-xs">
                    {loading ? 'Evaluating critical facilities...' : 'No critical facility data available for this analysis.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Export & Download Card */}
      {summary && (
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <Download className="w-4 h-4 text-cyan-400" />
              <span>Export Infrastructure Analysis Products</span>
            </h3>
            <span className="text-xs font-mono text-slate-400">Format: Standard GIS GeoJSON & JSON</span>
          </div>
          <div className="flex flex-wrap gap-3">
            <a
              href={`${API_BASE}/api/infrastructure/download/${encodeURIComponent(analysisId)}/geojson`}
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded-lg text-xs font-mono flex items-center space-x-2 border border-slate-700 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Exposed GeoJSON Layer</span>
            </a>
            <a
              href={`${API_BASE}/api/infrastructure/download/${encodeURIComponent(analysisId)}/summary`}
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded-lg text-xs font-mono flex items-center space-x-2 border border-slate-700 transition-colors"
            >
              <FileJson className="w-3.5 h-3.5" />
              <span>Download Exposure Summary JSON</span>
            </a>
          </div>
        </div>
      )}

      {/* Limitations and Uncertainties Box */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-3">
        <h3 className="text-xs font-bold text-white flex items-center space-x-2 uppercase tracking-wide">
          <HelpCircle className="w-4 h-4 text-amber-400" />
          <span>Operational Limitations & Scientific Uncertainties</span>
        </h3>
        <ul className="text-xs text-slate-400 space-y-1.5 list-disc list-inside leading-relaxed">
          {summary?.limitations_and_uncertainties ? (
            summary.limitations_and_uncertainties.map((lim, idx) => (
              <li key={idx}>{lim}</li>
            ))
          ) : (
            <>
              <li>Spatial intersection indicates potential water presence at ground footprint; does not prove structural collapse or internal inundation.</li>
              <li>OpenStreetMap building completeness varies in steep upper tributary valleys of Nuwakot District.</li>
              <li>Road centerline vectors do not incorporate vertical embankment clearance above river high-water marks.</li>
              <li>SAR radar shadow and geometric layover in Himalayan canyons may obscure floodwater against steep valley walls.</li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
};
