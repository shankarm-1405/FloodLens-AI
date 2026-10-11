import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { 
  Layers, 
  MapPin, 
  RotateCcw, 
  Eye, 
  EyeOff, 
  AlertTriangle,
  GitFork,
  ShieldAlert,
  Navigation
} from 'lucide-react';
import type { ConnectivitySummary } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

interface ConnectivityMapProps {
  bbox: number[]; // [minLon, minLat, maxLon, maxLat]
  analysisId: string | null;
  summary: ConnectivitySummary | null;
  className?: string;
}

export const ConnectivityMap: React.FC<ConnectivityMapProps> = ({
  bbox,
  analysisId,
  summary,
  className = 'h-[540px]'
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // Layer refs
  const aoiLayerRef = useRef<L.Rectangle | null>(null);
  const floodGeoJsonLayerRef = useRef<L.GeoJSON | null>(null);
  const baselineRoutesLayerRef = useRef<L.GeoJSON | null>(null);
  const postRoutesLayerRef = useRef<L.GeoJSON | null>(null);
  const closedRoadsLayerRef = useRef<L.GeoJSON | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  // Visibility toggles
  const [showAoi, setShowAoi] = useState(true);
  const [showFlood, setShowFlood] = useState(true);
  const [showBaselineRoutes, setShowBaselineRoutes] = useState(true);
  const [showPostRoutes, setShowPostRoutes] = useState(true);
  const [showClosedRoads, setShowClosedRoads] = useState(true);
  const [showMarkers, setShowMarkers] = useState(true);
  const [basemapStyle, setBasemapStyle] = useState<'dark' | 'osm' | 'imagery'>('dark');
  const [loadingLayers, setLoadingLayers] = useState(false);
  const [layerError, setLayerError] = useState<string | null>(null);

  const [minLon, minLat, maxLon, maxLat] = bbox;
  const bounds = L.latLngBounds([minLat, minLon], [maxLat, maxLon]);

  // 1. Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [(minLat + maxLat) / 2, (minLon + maxLon) / 2],
      zoom: 11,
      minZoom: 6,
      maxZoom: 18,
      zoomControl: false,
    });

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const tileLayer = L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        subdomains: 'abcd',
        maxZoom: 19
      }
    ).addTo(map);

    tileLayerRef.current = tileLayer;
    markersLayerRef.current = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;

    setTimeout(() => {
      map.invalidateSize();
      map.fitBounds(bounds, { padding: [30, 30] });
    }, 150);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // 2. Basemap Style Switcher
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    if (tileLayerRef.current) {
      tileLayerRef.current.remove();
    }

    let url = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
    let attribution = '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

    if (basemapStyle === 'osm') {
      url = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
      attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
    } else if (basemapStyle === 'imagery') {
      url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
      attribution = 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community';
    }

    const newTileLayer = L.tileLayer(url, { attribution, maxZoom: 19 }).addTo(mapInstanceRef.current);
    tileLayerRef.current = newTileLayer;
  }, [basemapStyle]);

  // 3. AOI Bounding Box Layer
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    if (aoiLayerRef.current) {
      aoiLayerRef.current.remove();
      aoiLayerRef.current = null;
    }

    if (showAoi) {
      const rect = L.rectangle(bounds, {
        color: '#06b6d4',
        weight: 1.5,
        dashArray: '4, 4',
        fill: false,
        interactive: false
      }).addTo(mapInstanceRef.current);
      aoiLayerRef.current = rect;
    }
  }, [showAoi, bbox]);

  // 4. Fetch and Render Vector Layers
  useEffect(() => {
    if (!mapInstanceRef.current || !analysisId) return;

    const map = mapInstanceRef.current;
    setLoadingLayers(true);
    setLayerError(null);

    // Clean up old layers
    if (floodGeoJsonLayerRef.current) floodGeoJsonLayerRef.current.remove();
    if (baselineRoutesLayerRef.current) baselineRoutesLayerRef.current.remove();
    if (postRoutesLayerRef.current) postRoutesLayerRef.current.remove();
    if (closedRoadsLayerRef.current) closedRoadsLayerRef.current.remove();
    if (markersLayerRef.current) markersLayerRef.current.clearLayers();

    // A. Fetch Flood Mask Layer
    fetch(`${API_BASE}/api/flood/download/${encodeURIComponent(analysisId)}/geojson`)
      .then(res => res.ok ? res.json() : null)
      .then(floodData => {
        if (!floodData || !mapInstanceRef.current) return;
        const floodLayer = L.geoJSON(floodData, {
          style: {
            color: '#0284c7',
            weight: 1.5,
            fillColor: '#38bdf8',
            fillOpacity: 0.45
          },
          onEachFeature: (feature, layer) => {
            const props = feature.properties || {};
            layer.bindPopup(`
              <div class="font-sans text-xs space-y-1 p-1">
                <div class="font-bold text-sky-400">Candidate Flood Polygon</div>
                <div class="text-slate-300">Class: ${props.classification || 'Surface Water Inundation'}</div>
                <div class="text-[11px] text-slate-400 font-mono">Area: ${props.area_sqkm ? props.area_sqkm.toFixed(4) + ' km²' : 'N/A'}</div>
              </div>
            `);
          }
        });
        floodGeoJsonLayerRef.current = floodLayer;
        if (showFlood) floodLayer.addTo(map);
      })
      .catch(() => {});

    // B. Fetch Connectivity Routes and Markers
    fetch(`${API_BASE}/api/connectivity/layers/${encodeURIComponent(analysisId)}/routes`)
      .then(res => {
        if (!res.ok) throw new Error(`Routes layer HTTP ${res.status}`);
        return res.json();
      })
      .then(routesData => {
        if (!routesData || !mapInstanceRef.current) return;

        const baselineFeatures: any[] = [];
        const postFeatures: any[] = [];
        const closedFeatures: any[] = [];
        const settlementMarkers: any[] = [];
        const hubMarkers: any[] = [];

        for (const feat of routesData.features || []) {
          const type = feat.properties?.type;
          if (type === 'baseline_route') baselineFeatures.push(feat);
          else if (type === 'post_flood_route') postFeatures.push(feat);
          else if (type === 'simulated_closed_edge') closedFeatures.push(feat);
          else if (type === 'settlement_marker') settlementMarkers.push(feat);
          else if (type === 'regional_hub_marker') hubMarkers.push(feat);
        }

        // 1. Baseline routes layer (Cyan solid line)
        const baselineLayer = L.geoJSON({ type: 'FeatureCollection', features: baselineFeatures } as any, {
          style: {
            color: '#06b6d4',
            weight: 3.5,
            opacity: 0.85
          },
          onEachFeature: (feature, layer) => {
            const p = feature.properties || {};
            layer.bindPopup(`
              <div class="font-sans text-xs space-y-1 p-1 text-slate-200">
                <div class="font-bold text-cyan-400 flex items-center space-x-1">
                  <span>Pre-Event Baseline Route</span>
                </div>
                <div>${p.settlement} &rarr; ${p.hub}</div>
                <div class="font-mono text-cyan-300">Distance: ${p.distance_km} km</div>
                <div class="font-mono text-slate-400 text-[11px]">Est. Time: ${p.travel_time_minutes} min (assumed speeds)</div>
              </div>
            `);
          }
        });
        baselineRoutesLayerRef.current = baselineLayer;
        if (showBaselineRoutes) baselineLayer.addTo(map);

        // 2. Post-flood routes layer (Amber dashed line)
        const postLayer = L.geoJSON({ type: 'FeatureCollection', features: postFeatures } as any, {
          style: {
            color: '#f59e0b',
            weight: 3.5,
            dashArray: '8, 6',
            opacity: 0.95
          },
          onEachFeature: (feature, layer) => {
            const p = feature.properties || {};
            layer.bindPopup(`
              <div class="font-sans text-xs space-y-1 p-1 text-slate-200">
                <div class="font-bold text-amber-400 flex items-center space-x-1">
                  <span>${p.is_detour ? 'Post-Flood Detour Route' : 'Post-Flood Traversable Route'}</span>
                </div>
                <div>${p.settlement} &rarr; ${p.hub}</div>
                <div class="font-mono text-amber-300">Distance: ${p.distance_km} km</div>
                <div class="font-mono text-slate-400 text-[11px]">Est. Time: ${p.travel_time_minutes} min</div>
              </div>
            `);
          }
        });
        postRoutesLayerRef.current = postLayer;
        if (showPostRoutes) postLayer.addTo(map);

        // 3. Simulated closed roads & bridges (Red bold dashed line)
        const closedLayer = L.geoJSON({ type: 'FeatureCollection', features: closedFeatures } as any, {
          style: {
            color: '#ef4444',
            weight: 4.5,
            dashArray: '6, 6',
            opacity: 0.95
          },
          onEachFeature: (feature, layer) => {
            const p = feature.properties || {};
            layer.bindPopup(`
              <div class="font-sans text-xs space-y-1 p-1 text-slate-200">
                <div class="font-bold text-rose-400 flex items-center space-x-1">
                  <span>Simulated Road Closure</span>
                </div>
                <div><strong>${p.name || 'Unnamed Segment'}</strong></div>
                <div class="text-[11px] text-slate-300">OSM ID: ${p.osm_id} • Type: ${p.highway || 'road'}${p.is_bridge ? ' (Bridge)' : ''}</div>
                <div class="font-mono text-slate-400 text-[11px]">Segment Length: ${p.length_km} km</div>
                <div class="text-[10px] text-rose-300 mt-1">${p.closure_reason || 'Intersects candidate flood polygon'}</div>
              </div>
            `);
          }
        });
        closedRoadsLayerRef.current = closedLayer;
        if (showClosedRoads) closedLayer.addTo(map);

        // 4. Markers for settlements and hubs
        if (markersLayerRef.current) {
          markersLayerRef.current.clearLayers();

          // Hub markers
          for (const hub of hubMarkers) {
            const coords = hub.geometry?.coordinates;
            if (!coords) continue;
            const marker = L.circleMarker([coords[1], coords[0]], {
              radius: 9,
              color: '#818cf8',
              fillColor: '#6366f1',
              fillOpacity: 0.95,
              weight: 2
            }).bindPopup(`
              <div class="font-sans text-xs space-y-1 p-1 text-slate-200">
                <div class="font-bold text-indigo-400">Regional Lifeline Hub</div>
                <div class="text-sm font-semibold text-white">${hub.properties?.name}</div>
                <div class="text-[11px] text-slate-400 font-mono">Status: ${hub.properties?.status || 'SNAPPED'}</div>
              </div>
            `);
            markersLayerRef.current.addLayer(marker);
          }

          // Settlement markers
          for (const s of settlementMarkers) {
            const coords = s.geometry?.coordinates;
            if (!coords) continue;
            const status = s.properties?.status;
            let color = '#10b981';
            let fillColor = '#059669';

            if (status === 'NEWLY_DISCONNECTED') {
              color = '#f43f5e';
              fillColor = '#e11d48';
            } else if (status === 'ALREADY_DISCONNECTED') {
              color = '#94a3b8';
              fillColor = '#64748b';
            } else if (status === 'DETOURED') {
              color = '#f59e0b';
              fillColor = '#d97706';
            } else if (status === 'SNAP_FAILED') {
              color = '#c084fc';
              fillColor = '#a855f7';
            }

            const marker = L.circleMarker([coords[1], coords[0]], {
              radius: 7,
              color: color,
              fillColor: fillColor,
              fillOpacity: 0.9,
              weight: 2
            }).bindPopup(`
              <div class="font-sans text-xs space-y-1 p-1 text-slate-200">
                <div class="font-bold text-white text-sm">${s.properties?.name}</div>
                <div class="font-mono text-[11px]">
                  Status: <span class="font-bold" style="color: ${color}">${status}</span>
                </div>
                <div class="text-slate-300 text-[11px]">${s.properties?.isolation_cause || ''}</div>
                ${s.properties?.baseline_distance_km !== null ? `<div class="text-slate-400 font-mono text-[11px]">Baseline Dist: ${s.properties?.baseline_distance_km} km</div>` : ''}
                ${s.properties?.post_distance_km !== null ? `<div class="text-slate-400 font-mono text-[11px]">Post-Flood Dist: ${s.properties?.post_distance_km} km</div>` : ''}
                ${s.properties?.detour_km ? `<div class="text-amber-300 font-mono text-[11px]">Detour: +${s.properties?.detour_km} km</div>` : ''}
              </div>
            `);
            markersLayerRef.current.addLayer(marker);
          }
        }

        setLoadingLayers(false);
      })
      .catch(err => {
        setLayerError(err.message || 'Failed to load route network layers');
        setLoadingLayers(false);
      });

  }, [analysisId]);

  // Synchronize layer visibility
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    if (floodGeoJsonLayerRef.current) {
      if (showFlood) floodGeoJsonLayerRef.current.addTo(map);
      else floodGeoJsonLayerRef.current.remove();
    }
    if (baselineRoutesLayerRef.current) {
      if (showBaselineRoutes) baselineRoutesLayerRef.current.addTo(map);
      else baselineRoutesLayerRef.current.remove();
    }
    if (postRoutesLayerRef.current) {
      if (showPostRoutes) postRoutesLayerRef.current.addTo(map);
      else postRoutesLayerRef.current.remove();
    }
    if (closedRoadsLayerRef.current) {
      if (showClosedRoads) closedRoadsLayerRef.current.addTo(map);
      else closedRoadsLayerRef.current.remove();
    }
    if (markersLayerRef.current) {
      if (showMarkers) markersLayerRef.current.addTo(map);
      else markersLayerRef.current.remove();
    }
  }, [showFlood, showBaselineRoutes, showPostRoutes, showClosedRoads, showMarkers]);

  const handleResetView = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.fitBounds(bounds, { padding: [30, 30] });
    }
  };

  return (
    <div className={`relative rounded-xl overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl flex flex-col ${className}`}>
      {/* Top Map Toolbar */}
      <div className="absolute top-3 left-3 z-[1000] flex flex-wrap items-center gap-2">
        {/* Basemap Selector */}
        <div className="bg-slate-900/95 backdrop-blur-md border border-slate-700/80 rounded-lg p-1 flex items-center shadow-lg">
          <button
            onClick={() => setBasemapStyle('dark')}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
              basemapStyle === 'dark' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-white'
            }`}
          >
            Dark Carto
          </button>
          <button
            onClick={() => setBasemapStyle('osm')}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
              basemapStyle === 'osm' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-white'
            }`}
          >
            OpenStreetMap
          </button>
          <button
            onClick={() => setBasemapStyle('imagery')}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
              basemapStyle === 'imagery' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-white'
            }`}
          >
            Satellite
          </button>
        </div>

        {/* Reset View Button */}
        <button
          onClick={handleResetView}
          className="bg-slate-900/95 backdrop-blur-md border border-slate-700/80 hover:bg-slate-800 text-slate-300 hover:text-white px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center space-x-1.5 shadow-lg transition-colors cursor-pointer"
          title="Reset to AOI Extent"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset View</span>
        </button>
      </div>

      {/* Layer Toggle Floating Panel (Top-Right) */}
      <div className="absolute top-3 right-3 z-[1000] bg-slate-900/95 backdrop-blur-md border border-slate-700/80 rounded-xl p-3 shadow-2xl max-w-xs space-y-2.5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
          <span className="text-xs font-bold text-slate-200 flex items-center space-x-1.5">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>Network Layers</span>
          </span>
          {loadingLayers && <span className="text-[10px] text-cyan-400 animate-pulse font-mono">Loading...</span>}
        </div>

        <div className="space-y-1.5 text-xs">
          <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
            <span className="flex items-center space-x-2">
              <span className="w-3 h-0.5 bg-cyan-400 inline-block rounded"></span>
              <span>Baseline Routes</span>
            </span>
            <input
              type="checkbox"
              checked={showBaselineRoutes}
              onChange={e => setShowBaselineRoutes(e.target.checked)}
              className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0 cursor-pointer"
            />
          </label>

          <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
            <span className="flex items-center space-x-2">
              <span className="w-3 h-0.5 bg-amber-400 border-b border-dashed border-amber-400 inline-block"></span>
              <span>Post-Flood Detours</span>
            </span>
            <input
              type="checkbox"
              checked={showPostRoutes}
              onChange={e => setShowPostRoutes(e.target.checked)}
              className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0 cursor-pointer"
            />
          </label>

          <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
            <span className="flex items-center space-x-2">
              <span className="w-3 h-1 bg-rose-500 border-b-2 border-dashed border-rose-500 inline-block"></span>
              <span>Simulated Closed Roads</span>
            </span>
            <input
              type="checkbox"
              checked={showClosedRoads}
              onChange={e => setShowClosedRoads(e.target.checked)}
              className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0 cursor-pointer"
            />
          </label>

          <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
            <span className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 bg-sky-500/50 border border-sky-400 rounded-sm inline-block"></span>
              <span>Flood Inundation Mask</span>
            </span>
            <input
              type="checkbox"
              checked={showFlood}
              onChange={e => setShowFlood(e.target.checked)}
              className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0 cursor-pointer"
            />
          </label>

          <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
            <span className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
              <span>Settlements & Hubs</span>
            </span>
            <input
              type="checkbox"
              checked={showMarkers}
              onChange={e => setShowMarkers(e.target.checked)}
              className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0 cursor-pointer"
            />
          </label>
        </div>
      </div>

      {/* Interactive Map DOM Container */}
      <div ref={mapContainerRef} className="flex-1 w-full h-full z-0" />

      {/* Bottom Map Legend Bar */}
      <div className="bg-slate-900 border-t border-slate-800 p-2.5 px-4 text-xs flex flex-wrap items-center justify-between gap-3 text-slate-400 font-sans z-10">
        <div className="flex flex-wrap items-center gap-4">
          <span className="font-semibold text-slate-200">Legend:</span>
          
          <span className="flex items-center space-x-1.5">
            <span className="w-4 h-1 bg-cyan-400 inline-block rounded"></span>
            <span className="text-slate-300">Baseline Route</span>
          </span>

          <span className="flex items-center space-x-1.5">
            <span className="w-4 h-1 border-b-2 border-dashed border-amber-400 inline-block"></span>
            <span className="text-slate-300">Post-Flood Detour</span>
          </span>

          <span className="flex items-center space-x-1.5">
            <span className="w-4 h-1.5 bg-rose-500 inline-block rounded"></span>
            <span className="text-slate-300">Closed Road / Bridge</span>
          </span>

          <span className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span>
            <span className="text-slate-300">Newly Disconnected</span>
          </span>

          <span className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block"></span>
            <span className="text-slate-300">Detoured</span>
          </span>

          <span className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-500 inline-block"></span>
            <span className="text-slate-300">Baseline Disconnected</span>
          </span>

          <span className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 border border-indigo-300 inline-block"></span>
            <span className="text-slate-300">Regional Hub</span>
          </span>
        </div>

        <div className="font-mono text-[11px] text-slate-500">
          CRS: EPSG:32645 Metric &bull; Dijkstra Shortest Path
        </div>
      </div>
    </div>
  );
};
