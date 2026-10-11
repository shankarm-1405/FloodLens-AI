import React, { useState, useEffect } from 'react';
import { 
  GitFork, 
  MapPin, 
  Hospital, 
  AlertTriangle, 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  Play,
  Download,
  Info,
  Clock,
  Navigation,
  RefreshCw,
  Sliders,
  Layers,
  ChevronDown,
  ExternalLink
} from 'lucide-react';
import type { SystemHealth, ConnectivitySummary, SettlementDetail } from '../types';
import { 
  fetchConnectivityStatus, 
  fetchConnectivitySummary, 
  triggerConnectivityAnalysis 
} from '../services/api';
import { ConnectivityMap } from '../components/ConnectivityMap';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

interface ConnectivityPageProps {
  health: SystemHealth | null;
}

export const ConnectivityPage: React.FC<ConnectivityPageProps> = ({ health }) => {
  const [analysisId, setAnalysisId] = useState<string>('e2e-trishuli-aug2026');
  const [selectedHub, setSelectedHub] = useState<string>('Bidur');
  const [closureMethod, setClosureMethod] = useState<string>('complete_severance');
  const [snappingTolerance, setSnappingTolerance] = useState<number>(50.0);
  
  const [summary, setSummary] = useState<ConnectivitySummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load existing analysis summary on mount or analysisId change
  const loadConnectivityData = async (targetId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const statusRes = await fetchConnectivityStatus(targetId);
      if (statusRes.outputs_ready) {
        const fullSummary = await fetchConnectivitySummary(targetId);
        setSummary(fullSummary);
      } else {
        setSummary(null);
      }
    } catch (err: any) {
      console.warn("Could not load initial connectivity status:", err);
      setSummary(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (analysisId) {
      loadConnectivityData(analysisId);
    }
  }, [analysisId]);

  // Handle re-running / executing analysis
  const handleRunAnalysis = async () => {
    if (!analysisId) return;
    setIsExecuting(true);
    setError(null);
    try {
      const res = await triggerConnectivityAnalysis({
        analysis_id: analysisId,
        closure_method: closureMethod,
        snapping_tolerance_m: snappingTolerance,
        allow_fallback_fixture: true
      });
      setSummary(res);
    } catch (err: any) {
      setError(err.message || 'Failed to execute settlement connectivity analysis.');
    } finally {
      setIsExecuting(false);
    }
  };

  const counts = summary?.summary_counts;
  const graphSettings = summary?.graph_construction_settings;
  const aoiBbox = health?.study_case?.default_bbox || [85.05, 27.75, 85.25, 27.95];

  // Helper badge for settlement status
  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'NEWLY_DISCONNECTED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono bg-rose-950/80 text-rose-300 border border-rose-800">
            <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
            <span>Newly Cut-Off</span>
          </span>
        );
      case 'ALREADY_DISCONNECTED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono bg-slate-800 text-slate-300 border border-slate-700">
            <AlertTriangle className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span>Baseline Disconnected</span>
          </span>
        );
      case 'DETOURED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono bg-amber-950/80 text-amber-300 border border-amber-800">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>Alternative Detour</span>
          </span>
        );
      case 'UNCHANGED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Connected</span>
          </span>
        );
      case 'UNAVAILABLE':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono bg-purple-950/80 text-purple-300 border border-purple-800">
            <Info className="w-3.5 h-3.5 text-purple-400 shrink-0" />
            <span>Unavailable in OSM</span>
          </span>
        );
      case 'SNAP_FAILED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-mono bg-orange-950/80 text-orange-300 border border-orange-800">
            <AlertTriangle className="w-3.5 h-3.5 text-orange-400 shrink-0" />
            <span>Snap Failed (&gt; threshold)</span>
          </span>
        );
      default:
        return <span className="font-mono text-slate-400">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2.5">
            <GitFork className="w-7 h-7 text-amber-400" />
            <span>Settlement Road Disconnection & Isolation Analysis</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-3xl">
            Phase 5: Metric NetworkX graph modeling post-flood accessibility from mountain communities to regional lifeline hubs in the Trishuli River Basin.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs font-mono bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-slate-300">
            CRS: EPSG:32645 (UTM 45N)
          </span>
        </div>
      </div>

      {/* Provenance & Caveat Banner */}
      {summary?.is_synthetic && (
        <div className="rounded-xl bg-amber-950/40 border border-amber-800/80 p-4 text-xs text-amber-200 flex items-start space-x-3 shadow-lg">
          <ShieldAlert className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <div className="font-bold text-amber-300 flex items-center space-x-2">
              <span className="bg-amber-900/60 border border-amber-700/80 px-2 py-0.5 rounded font-mono text-[11px]">
                SYNTHETIC_TEST_FIXTURE
              </span>
              <span>DEMONSTRATION SCENARIO — NOT CONFIRMED REAL-WORLD DISCONNECTION</span>
            </div>
            <p className="text-slate-300 leading-relaxed text-[11px]">
              This connectivity assessment is evaluated against a synthetic demonstration flood mask and verified pre-event OSM baseline fixture (2026-07-27). 
              Spatial intersection flags <strong>potential road network disruption</strong>; it does not constitute empirical verification of structural road collapse, 
              landslides, or impassability. Unmapped pedestrian footpaths and emergency air evacuation corridors are not captured in vehicular graph routing.
            </p>
          </div>
        </div>
      )}

      {summary?.provenance === 'UNAVAILABLE' && (
        <div className="rounded-xl bg-rose-950/40 border border-rose-800/80 p-4 text-xs text-rose-200 flex items-start space-x-3 shadow-lg">
          <ShieldAlert className="w-5 h-5 text-rose-400 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <div className="font-bold text-rose-300 flex items-center space-x-2">
              <span className="bg-rose-900/60 border border-rose-700/80 px-2 py-0.5 rounded font-mono text-[11px]">
                PROVENANCE: UNAVAILABLE
              </span>
              <span>INPUTS UNAVAILABLE — ANALYSIS HALTED</span>
            </div>
            <p className="text-slate-300 leading-relaxed text-[11px]">
              Upstream flood raster or pre-event historical road baseline is unavailable. Connectivity metrics are not fabricated.
            </p>
          </div>
        </div>
      )}

      {!summary?.is_synthetic && summary && summary.provenance !== 'UNAVAILABLE' && (
        <div className="rounded-xl bg-emerald-950/40 border border-emerald-800/80 p-4 text-xs text-emerald-200 flex items-start space-x-3 shadow-lg">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <div className="font-bold text-emerald-300 flex items-center space-x-2">
              <span className="bg-emerald-900/60 border border-emerald-700/80 px-2 py-0.5 rounded font-mono text-[11px]">
                {summary.provenance}
              </span>
              <span>VERIFIED SATELLITE & ROAD CONNECTIVITY ASSESSMENT</span>
            </div>
            <p className="text-slate-300 leading-relaxed text-[11px]">
              Analysis computed from real satellite inundation and verified OpenStreetMap highway networks.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-xl bg-rose-950/60 border border-rose-800 p-4 text-xs text-rose-200 flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
          <div>
            <span className="font-bold">Analysis Execution Error:</span>
            <p className="mt-0.5 text-rose-300">{error}</p>
          </div>
        </div>
      )}

      {/* Configuration & Parameter Controls */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Flood Analysis ID Selector */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-2">
          <label className="block text-xs font-semibold text-slate-200 flex items-center space-x-1.5">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>Flood Analysis Input</span>
          </label>
          <input
            type="text"
            value={analysisId}
            onChange={(e) => setAnalysisId(e.target.value)}
            placeholder="e.g. e2e-trishuli-aug2026"
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-500"
          />
          <p className="text-[11px] text-slate-400">Validated SAR flood analysis identifier.</p>
        </div>

        {/* Target Destination Hub */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-2">
          <label className="block text-xs font-semibold text-slate-200 flex items-center space-x-1.5">
            <Hospital className="w-3.5 h-3.5 text-rose-400" />
            <span>Primary Regional Hub</span>
          </label>
          <select
            value={selectedHub}
            onChange={(e) => setSelectedHub(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-cyan-500 font-sans"
          >
            <option value="Bidur">Bidur (District Center & Relief Depot)</option>
            <option value="Trishuli Bazaar">Trishuli Bazaar (Upper Valley Hub)</option>
          </select>
          <p className="text-[11px] text-slate-400">Regional destination for routing evaluation.</p>
        </div>

        {/* Closure Simulation Rule */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-2">
          <label className="block text-xs font-semibold text-slate-200 flex items-center space-x-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span>Closure Severance Rule</span>
          </label>
          <select
            value={closureMethod}
            onChange={(e) => setClosureMethod(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-cyan-500 font-sans"
          >
            <option value="complete_severance">Complete Severance (All flooded roads & bridges closed)</option>
            <option value="bridge_severance_only">Bridge Severance Only (Only mapped river bridges closed)</option>
          </select>
          <p className="text-[11px] text-slate-400">Specifies edge removal logic in the road graph.</p>
        </div>

        {/* Action Button */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-200">Recompute Network Routing</span>
            <p className="text-[11px] text-slate-400 mt-1">Executes Dijkstra shortest path queries on metric road graph.</p>
          </div>
          <button
            onClick={handleRunAnalysis}
            disabled={isExecuting || !analysisId}
            className="w-full py-2 px-3 rounded-lg bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white font-medium text-xs flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-md disabled:opacity-50"
          >
            {isExecuting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            <span>{isExecuting ? 'Computing Routes...' : 'Run Connectivity Analysis'}</span>
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="rounded-xl bg-slate-900 border border-slate-800 p-3.5 space-y-1">
            <div className="text-[11px] text-slate-400 font-medium">Evaluated</div>
            <div className="text-2xl font-bold text-white font-mono">{counts?.settlements_evaluated ?? 0}</div>
            <div className="text-[10px] text-slate-500">Target settlements</div>
          </div>

          <div className="rounded-xl bg-slate-900 border border-rose-900/60 p-3.5 space-y-1 bg-rose-950/20">
            <div className="text-[11px] text-rose-300 font-medium">Newly Cut-Off</div>
            <div className="text-2xl font-bold text-rose-400 font-mono">{counts?.newly_disconnected ?? 0}</div>
            <div className="text-[10px] text-rose-400/80">Lost road access</div>
          </div>

          <div className="rounded-xl bg-slate-900 border border-amber-900/60 p-3.5 space-y-1 bg-amber-950/20">
            <div className="text-[11px] text-amber-300 font-medium">Detoured</div>
            <div className="text-2xl font-bold text-amber-400 font-mono">{counts?.detoured ?? 0}</div>
            <div className="text-[10px] text-amber-400/80">Alternative route found</div>
          </div>

          <div className="rounded-xl bg-slate-900 border border-slate-800 p-3.5 space-y-1">
            <div className="text-[11px] text-slate-400 font-medium">Baseline Cut-Off</div>
            <div className="text-2xl font-bold text-slate-300 font-mono">{counts?.already_disconnected_at_baseline ?? 0}</div>
            <div className="text-[10px] text-slate-500">Isolated prior to flood</div>
          </div>

          <div className="rounded-xl bg-slate-900 border border-slate-800 p-3.5 space-y-1">
            <div className="text-[11px] text-slate-400 font-medium">Closed Edges</div>
            <div className="text-2xl font-bold text-rose-300 font-mono">{summary.closure_parameters.closed_edges_count}</div>
            <div className="text-[10px] text-slate-500">{summary.closure_parameters.closed_bridges_count} bridges severed</div>
          </div>

          <div className="rounded-xl bg-slate-900 border border-slate-800 p-3.5 space-y-1">
            <div className="text-[11px] text-slate-400 font-medium">Missing / Unmatched</div>
            <div className="text-2xl font-bold text-purple-400 font-mono">{(counts?.unavailable ?? 0) + (counts?.snap_failed ?? 0)}</div>
            <div className="text-[10px] text-slate-500">{counts?.unavailable ?? 0} missing, {counts?.snap_failed ?? 0} failed snap</div>
          </div>
        </div>
      )}

      {/* Interactive Map Component */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center space-x-2">
            <Navigation className="w-4 h-4 text-cyan-400" />
            <span>Interactive Road-Network Routing & Disconnection Map</span>
          </h2>
          <span className="text-xs text-slate-400 font-mono">
            Analysis ID: <strong className="text-cyan-300">{analysisId}</strong>
          </span>
        </div>
        <ConnectivityMap
          bbox={aoiBbox}
          analysisId={analysisId}
          summary={summary}
          className="h-[520px]"
        />
      </div>

      {/* Settlement Connectivity Table */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 p-5 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-sm font-bold text-white flex items-center space-x-2">
              <MapPin className="w-4 h-4 text-cyan-400" />
              <span>Settlement Accessibility & Route Status</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Detailed post-disaster route changes and bottleneck causes modeled to regional lifeline hubs.
            </p>
          </div>
          <div className="flex items-center space-x-2 text-xs">
            <span className="font-mono text-slate-400">
              Evaluated to: <strong className="text-cyan-300">{selectedHub}</strong>
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-sans">
            <thead className="bg-slate-950 text-slate-400 font-mono text-[11px] uppercase border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Settlement</th>
                <th className="py-2.5 px-3">Baseline Route</th>
                <th className="py-2.5 px-3">Post-Flood Status</th>
                <th className="py-2.5 px-3">Post-Flood Route</th>
                <th className="py-2.5 px-3">Detour Delta</th>
                <th className="py-2.5 px-3">Bottleneck / Isolation Cause</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-slate-300">
              {summary && summary.settlement_details && summary.settlement_details.length > 0 ? (
                summary.settlement_details.map((s, idx) => {
                  const hubConn = s.hub_connections?.[selectedHub] || {};
                  const baseDist = hubConn.baseline_distance_km ?? s.baseline_distance_km;
                  const baseTime = hubConn.baseline_travel_time_minutes ?? s.baseline_travel_time_minutes;
                  const postDist = hubConn.post_distance_km ?? s.post_flood_distance_km;
                  const postTime = hubConn.post_travel_time_minutes ?? s.post_flood_travel_time_minutes;
                  const detourKm = hubConn.detour_distance_km ?? s.detour_distance_km;
                  const detourMin = hubConn.detour_travel_time_minutes ?? s.detour_travel_time_minutes;

                  return (
                    <tr key={idx} className="hover:bg-slate-850/60 transition-colors">
                      <td className="py-3 px-3">
                        <div className="font-medium text-white text-sm">{s.name}</div>
                        {s.osm_id && (
                          <div className="text-[10px] text-slate-500 font-mono">OSM ID: {s.osm_id}</div>
                        )}
                        {s.snapped_distance_m !== undefined && s.snapped_distance_m !== null && (
                          <div className="text-[10px] text-cyan-400/80 font-mono">Snap dist: {s.snapped_distance_m}m</div>
                        )}
                      </td>
                      <td className="py-3 px-3 font-mono">
                        {baseDist !== null ? (
                          <div>
                            <span className="text-slate-200">{baseDist} km</span>
                            <div className="text-[10px] text-slate-400">{baseTime} min (est.)</div>
                          </div>
                        ) : (
                          <span className="text-slate-500 italic">No direct path</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        {renderStatusBadge(s.status)}
                      </td>
                      <td className="py-3 px-3 font-mono">
                        {postDist !== null ? (
                          <div>
                            <span className={detourKm ? 'text-amber-300 font-bold' : 'text-slate-200'}>
                              {postDist} km
                            </span>
                            <div className="text-[10px] text-slate-400">{postTime} min (est.)</div>
                          </div>
                        ) : (
                          <span className="text-rose-400 font-bold">&infin; (Cut-Off)</span>
                        )}
                      </td>
                      <td className="py-3 px-3 font-mono">
                        {detourKm !== null && detourKm > 0 ? (
                          <span className="text-amber-400 font-bold">
                            +{detourKm.toFixed(2)} km (+{detourMin} min)
                          </span>
                        ) : (
                          <span className="text-slate-500">&mdash;</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-slate-300 max-w-xs text-[11px] leading-relaxed">
                        {s.isolation_cause}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500 italic">
                    {isLoading ? 'Loading connectivity summary...' : 'No connectivity analysis executed yet. Click "Run Connectivity Analysis" above.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Graph Statistics & Snapping Quality Notice */}
      {graphSettings && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-3">
            <h3 className="text-xs font-bold text-slate-200 flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              <span>Network Graph Construction Parameters</span>
            </h3>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 block text-[10px]">Projected CRS:</span>
                <span className="text-slate-200">{graphSettings.projected_crs}</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 block text-[10px]">Snapping Tolerance:</span>
                <span className="text-slate-200">{graphSettings.snapping_tolerance_m} meters</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 block text-[10px]">Total Road Length:</span>
                <span className="text-cyan-300 font-bold">{graphSettings.total_road_length_km} km</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 block text-[10px]">Network Components:</span>
                <span className="text-slate-200">{graphSettings.connected_components_count}</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 block text-[10px]">Graph Nodes:</span>
                <span className="text-slate-200">{graphSettings.nodes_count}</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 block text-[10px]">Graph Edges:</span>
                <span className="text-slate-200">{graphSettings.edges_count}</span>
              </div>
            </div>
          </div>

          <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-3">
            <h3 className="text-xs font-bold text-slate-200 flex items-center space-x-2">
              <Clock className="w-4 h-4 text-amber-400" />
              <span>Documented Travel Speed Assumptions</span>
            </h3>
            <p className="text-[11px] text-slate-400">
              Speeds are modeled estimates based on Nepal rural/mountain road design classifications (DoR Nepal / IRC guidelines). 
              These reflect theoretical unimpeded transit times, not real-time GPS probe measurements.
            </p>
            <div className="grid grid-cols-3 gap-2 text-xs font-mono">
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 text-[10px] block">Primary (H02):</span>
                <span className="text-amber-300">50 km/h</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 text-[10px] block">Secondary Feeder:</span>
                <span className="text-amber-300">40 km/h</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 text-[10px] block">Tertiary / Valley:</span>
                <span className="text-amber-300">30 km/h</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 text-[10px] block">Residential:</span>
                <span className="text-amber-300">25 km/h</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 text-[10px] block">Track / Service:</span>
                <span className="text-amber-300">15-20 km/h</span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800">
                <span className="text-slate-400 text-[10px] block">Footbridge / Trail:</span>
                <span className="text-amber-300">5 km/h</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Download Output Files Section */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-xs font-bold text-white flex items-center space-x-1.5">
            <Download className="w-4 h-4 text-cyan-400" />
            <span>Export Connectivity Analysis Artifacts</span>
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Download vector routes, closed edge geometries, and structured JSON summaries.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <a
            href={`${API_BASE}/api/connectivity/download/${encodeURIComponent(analysisId)}/summary`}
            download
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center space-x-1.5 border border-slate-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span>Summary JSON</span>
          </a>
          <a
            href={`${API_BASE}/api/connectivity/download/${encodeURIComponent(analysisId)}/routes`}
            download
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center space-x-1.5 border border-slate-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span>Routes GeoJSON</span>
          </a>
          <a
            href={`${API_BASE}/api/connectivity/download/${encodeURIComponent(analysisId)}/closed_roads`}
            download
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center space-x-1.5 border border-slate-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-rose-400" />
            <span>Closed Roads GeoJSON</span>
          </a>
        </div>
      </div>
    </div>
  );
};
