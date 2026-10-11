import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { 
  Layers, 
  MapPin, 
  RotateCcw, 
  Eye, 
  EyeOff, 
  Info,
  Building2,
  Route,
  AlertTriangle,
  HeartPulse
} from 'lucide-react';
import type { InfrastructureExposureSummary } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

interface InfrastructureMapProps {
  bbox: number[]; // [minLon, minLat, maxLon, maxLat]
  analysisId: string | null;
  summary: InfrastructureExposureSummary | null;
  className?: string;
}

export const InfrastructureMap: React.FC<InfrastructureMapProps> = ({
  bbox,
  analysisId,
  summary,
  className = 'h-[520px]'
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // Layer groups
  const aoiLayerRef = useRef<L.Rectangle | null>(null);
  const floodGeoJsonLayerRef = useRef<L.GeoJSON | null>(null);
  const baselineLayerRef = useRef<L.GeoJSON | null>(null);
  const exposedLayerRef = useRef<L.GeoJSON | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  // UI state
  const [showAoi, setShowAoi] = useState(true);
  const [showFlood, setShowFlood] = useState(true);
  const [showBaseline, setShowBaseline] = useState(true);
  const [showExposed, setShowExposed] = useState(true);
  const [basemapStyle, setBasemapStyle] = useState<'dark' | 'osm' | 'imagery'>('dark');
  const [loadingLayers, setLoadingLayers] = useState(false);
  const [layerError, setLayerError] = useState<string | null>(null);

  const [minLon, minLat, maxLon, maxLat] = bbox;
  const bounds = L.latLngBounds([minLat, minLon], [maxLat, maxLon]);

  // 1. Initialize Map
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
    mapInstanceRef.current = map;

    setTimeout(() => {
      map.invalidateSize();
      map.fitBounds(bounds, { padding: [25, 25] });
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

    const newLayer = L.tileLayer(url, { attribution, maxZoom: 19 }).addTo(mapInstanceRef.current);
    tileLayerRef.current = newLayer;
  }, [basemapStyle]);

  // 3. Render AOI Bounding Box
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    if (aoiLayerRef.current) {
      aoiLayerRef.current.remove();
      aoiLayerRef.current = null;
    }

    if (showAoi) {
      const aoiRect = L.rectangle(bounds, {
        color: '#06b6d4',
        weight: 1.5,
        dashArray: '5, 5',
        fill: false,
      }).addTo(mapInstanceRef.current);

      aoiRect.bindTooltip('Study Area AOI (Trishuli Corridor)', {
        sticky: true,
        className: 'bg-slate-900 text-cyan-400 border border-cyan-800 text-xs px-2 py-1 font-mono rounded'
      });

      aoiLayerRef.current = aoiRect;
    }
  }, [showAoi, minLon, minLat, maxLon, maxLat]);

  // 4. Load Vectors (Flood Extent, Baseline, and Exposed Infrastructure)
  useEffect(() => {
    if (!mapInstanceRef.current || !analysisId) return;

    const map = mapInstanceRef.current;
    let isCancelled = false;
    setLoadingLayers(true);
    setLayerError(null);

    // Clean up previous vector layers
    if (floodGeoJsonLayerRef.current) {
      floodGeoJsonLayerRef.current.remove();
      floodGeoJsonLayerRef.current = null;
    }
    if (baselineLayerRef.current) {
      baselineLayerRef.current.remove();
      baselineLayerRef.current = null;
    }
    if (exposedLayerRef.current) {
      exposedLayerRef.current.remove();
      exposedLayerRef.current = null;
    }

    async function loadAllLayers() {
      try {
        // Fetch Flood GeoJSON
        const floodRes = await fetch(`${API_BASE}/api/flood/download/${encodeURIComponent(analysisId!)}/geojson`);
        if (floodRes.ok && !isCancelled) {
          const floodData = await floodRes.json();
          const floodLayer = L.geoJSON(floodData, {
            style: {
              color: '#38bdf8',
              weight: 1.5,
              fillColor: '#0284c7',
              fillOpacity: 0.45,
            },
            onEachFeature: (feature, layer) => {
              layer.bindPopup(`
                <div class="font-sans text-xs space-y-1 p-1">
                  <div class="font-bold text-sky-400">Candidate Flood Extent</div>
                  <div class="text-slate-300">Sentinel-1 Amplitude Change Mask</div>
                  <div class="text-[11px] font-mono text-slate-400">Class: Inundated Land Surface</div>
                </div>
              `);
            }
          });
          floodGeoJsonLayerRef.current = floodLayer;
          if (showFlood) floodLayer.addTo(map);
        }

        // Fetch Baseline GeoJSON
        const baseRes = await fetch(`${API_BASE}/api/infrastructure/layers/${encodeURIComponent(analysisId!)}/baseline`);
        if (baseRes.ok && !isCancelled) {
          const baseData = await baseRes.json();
          const baseLayer = L.geoJSON(baseData, {
            style: (feature) => {
              const cat = feature?.properties?.category;
              if (cat === 'road') {
                return { color: '#64748b', weight: 1.5, opacity: 0.6 };
              }
              if (cat === 'building') {
                return { color: '#475569', weight: 1, fillColor: '#334155', fillOpacity: 0.3 };
              }
              if (cat === 'bridge') {
                return { color: '#8b5cf6', weight: 3, opacity: 0.7 };
              }
              return { color: '#64748b', weight: 1 };
            },
            pointToLayer: (feature, latlng) => {
              const cat = feature.properties?.category;
              if (cat === 'healthcare') {
                return L.circleMarker(latlng, {
                  radius: 5,
                  fillColor: '#10b981',
                  color: '#065f46',
                  weight: 1.5,
                  fillOpacity: 0.8
                });
              }
              return L.circleMarker(latlng, {
                radius: 4,
                fillColor: '#94a3b8',
                color: '#475569',
                weight: 1,
                fillOpacity: 0.7
              });
            },
            onEachFeature: (feature, layer) => {
              const props = feature.properties || {};
              const cat = props.category || 'Infrastructure';
              const name = props.name || `OSM ${props.osm_type || ''}/${props.osm_id || ''}`;
              layer.bindTooltip(`Baseline: ${name} (${cat})`, {
                sticky: true,
                className: 'bg-slate-900 text-slate-300 border border-slate-700 text-xs px-2 py-1 rounded'
              });
            }
          });
          baselineLayerRef.current = baseLayer;
          if (showBaseline) baseLayer.addTo(map);
        }

        // Fetch Exposed GeoJSON
        const expRes = await fetch(`${API_BASE}/api/infrastructure/layers/${encodeURIComponent(analysisId!)}/exposed`);
        if (expRes.ok && !isCancelled) {
          const expData = await expRes.json();
          const expLayer = L.geoJSON(expData, {
            style: (feature) => {
              const p = feature?.properties || {};
              if (p.exposure_type === 'road') {
                return { color: '#f59e0b', weight: 3.5, opacity: 0.9 };
              }
              if (p.exposure_type === 'building') {
                return { color: '#f43f5e', weight: 1.5, fillColor: '#e11d48', fillOpacity: 0.65 };
              }
              if (p.exposure_type === 'bridge') {
                return { color: '#ef4444', weight: 4.5, opacity: 1.0 };
              }
              return { color: '#f43f5e', weight: 2 };
            },
            pointToLayer: (feature, latlng) => {
              const p = feature.properties || {};
              let fillColor = '#10b981';
              let borderColor = '#059669';

              if (p.exposure_status === 'DIRECTLY_INTERSECTING') {
                fillColor = '#f43f5e';
                borderColor = '#be123c';
              } else if (p.exposure_status === 'BUFFER_ZONE_30M') {
                fillColor = '#f59e0b';
                borderColor = '#d97706';
              }

              return L.circleMarker(latlng, {
                radius: 7,
                fillColor,
                color: borderColor,
                weight: 2,
                fillOpacity: 0.95
              });
            },
            onEachFeature: (feature, layer) => {
              const p = feature.properties || {};
              const name = p.name || `OSM ${p.osm_id || ''}`;
              const type = p.exposure_type || p.category || 'Infrastructure';
              const status = p.exposure_status || (p.potentially_exposed ? 'Potentially Exposed' : 'Assessed');
              const dist = p.distance_to_flood_m !== undefined ? `${p.distance_to_flood_m} m` : 'Intersecting';

              layer.bindPopup(`
                <div class="font-sans text-xs space-y-1.5 p-1 min-w-[180px]">
                  <div class="font-bold text-rose-400 border-b border-slate-700 pb-1">${name}</div>
                  <div class="flex justify-between text-slate-300">
                    <span class="text-slate-400">Category:</span>
                    <span class="font-medium capitalize">${type}</span>
                  </div>
                  <div class="flex justify-between text-slate-300">
                    <span class="text-slate-400">Status:</span>
                    <span class="font-mono text-[11px] font-bold ${
                      status === 'DIRECTLY_INTERSECTING' ? 'text-rose-400' :
                      status === 'BUFFER_ZONE_30M' ? 'text-amber-400' : 'text-emerald-400'
                    }">${status}</span>
                  </div>
                  <div class="flex justify-between text-slate-300">
                    <span class="text-slate-400">Dist to Flood:</span>
                    <span class="font-mono text-[11px] text-cyan-300">${dist}</span>
                  </div>
                  <div class="text-[10px] text-slate-500 pt-1 border-t border-slate-800">
                    © OpenStreetMap contributors.
                  </div>
                </div>
              `);
            }
          });
          exposedLayerRef.current = expLayer;
          if (showExposed) expLayer.addTo(map);
        }

      } catch (err: any) {
        if (!isCancelled) {
          setLayerError(err?.message || 'Failed to load vector layers');
        }
      } finally {
        if (!isCancelled) {
          setLoadingLayers(false);
        }
      }
    }

    loadAllLayers();

    return () => {
      isCancelled = true;
    };
  }, [analysisId]);

  // Toggle Visibility Effects
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    if (floodGeoJsonLayerRef.current) {
      if (showFlood) mapInstanceRef.current.addLayer(floodGeoJsonLayerRef.current);
      else mapInstanceRef.current.removeLayer(floodGeoJsonLayerRef.current);
    }
  }, [showFlood]);

  useEffect(() => {
    if (!mapInstanceRef.current) return;
    if (baselineLayerRef.current) {
      if (showBaseline) mapInstanceRef.current.addLayer(baselineLayerRef.current);
      else mapInstanceRef.current.removeLayer(baselineLayerRef.current);
    }
  }, [showBaseline]);

  useEffect(() => {
    if (!mapInstanceRef.current) return;
    if (exposedLayerRef.current) {
      if (showExposed) mapInstanceRef.current.addLayer(exposedLayerRef.current);
      else mapInstanceRef.current.removeLayer(exposedLayerRef.current);
    }
  }, [showExposed]);

  const handleResetView = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.fitBounds(bounds, { padding: [25, 25] });
    }
  };

  return (
    <div className="relative rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-2xl">
      {/* Map Control Bar Top */}
      <div className="absolute top-3 left-3 z-[1000] flex flex-wrap items-center gap-2 bg-slate-900/95 backdrop-blur-md border border-slate-800 px-3 py-1.5 rounded-xl shadow-lg text-xs">
        <span className="font-semibold text-white flex items-center space-x-1.5">
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>Layers:</span>
        </span>

        {/* Exposed Layer Toggle */}
        <button
          onClick={() => setShowExposed(!showExposed)}
          className={`px-2.5 py-1 rounded-lg font-mono text-[11px] flex items-center space-x-1 transition-colors ${
            showExposed 
              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' 
              : 'bg-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          {showExposed ? <Eye className="w-3 h-3 text-rose-400" /> : <EyeOff className="w-3 h-3" />}
          <span>Exposed Features</span>
        </button>

        {/* Flood Extent Toggle */}
        <button
          onClick={() => setShowFlood(!showFlood)}
          className={`px-2.5 py-1 rounded-lg font-mono text-[11px] flex items-center space-x-1 transition-colors ${
            showFlood 
              ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40' 
              : 'bg-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          {showFlood ? <Eye className="w-3 h-3 text-sky-400" /> : <EyeOff className="w-3 h-3" />}
          <span>Flood Extent</span>
        </button>

        {/* Baseline Layer Toggle */}
        <button
          onClick={() => setShowBaseline(!showBaseline)}
          className={`px-2.5 py-1 rounded-lg font-mono text-[11px] flex items-center space-x-1 transition-colors ${
            showBaseline 
              ? 'bg-slate-700/60 text-slate-200 border border-slate-600' 
              : 'bg-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          {showBaseline ? <Eye className="w-3 h-3 text-slate-300" /> : <EyeOff className="w-3 h-3" />}
          <span>Baseline OSM</span>
        </button>

        {/* AOI Toggle */}
        <button
          onClick={() => setShowAoi(!showAoi)}
          className={`px-2 py-1 rounded-lg font-mono text-[11px] flex items-center space-x-1 transition-colors ${
            showAoi ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'bg-slate-800 text-slate-400'
          }`}
        >
          <MapPin className="w-3 h-3 text-cyan-400" />
          <span>AOI</span>
        </button>

        {/* Reset View */}
        <button
          onClick={handleResetView}
          className="p-1 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition-colors"
          title="Reset map view to Trishuli AOI"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Basemap Switcher Top Right */}
      <div className="absolute top-3 right-3 z-[1000] flex items-center space-x-1 bg-slate-900/95 backdrop-blur-md border border-slate-800 p-1 rounded-xl shadow-lg text-[11px]">
        {(['dark', 'osm', 'imagery'] as const).map((style) => (
          <button
            key={style}
            onClick={() => setBasemapStyle(style)}
            className={`px-2 py-1 rounded-lg capitalize font-mono transition-colors ${
              basemapStyle === style
                ? 'bg-indigo-600 text-white font-medium'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {style}
          </button>
        ))}
      </div>

      {/* Main Map Canvas */}
      <div ref={mapContainerRef} className={`w-full ${className} z-0`} />

      {/* Loading Overlay */}
      {loadingLayers && (
        <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm z-[1001] flex items-center justify-center">
          <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-4 py-2 rounded-xl text-xs text-slate-300 font-mono">
            <span className="w-3 h-3 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span>Loading infrastructure vectors...</span>
          </div>
        </div>
      )}

      {/* Bottom Map Legend */}
      <div className="absolute bottom-3 left-3 z-[1000] bg-slate-900/95 backdrop-blur-md border border-slate-800 p-3 rounded-xl shadow-xl text-[11px] text-slate-300 max-w-sm pointer-events-auto space-y-2">
        <div className="font-bold text-white flex items-center justify-between border-b border-slate-800 pb-1">
          <span>Map Legend</span>
          <span className="text-[10px] font-mono text-slate-400">© OpenStreetMap contributors.</span>
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[10px]">
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-sky-500/50 border border-sky-400 shrink-0" />
            <span>Candidate Flood Extent</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-rose-500/70 border border-rose-400 shrink-0" />
            <span>Exposed Building</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-4 h-1 bg-amber-500 rounded shrink-0" />
            <span>Exposed Road (km)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-4 h-1 bg-rose-500 rounded shrink-0" />
            <span>Exposed Bridge</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 border border-rose-300 shrink-0" />
            <span>Facility Intersecting</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 border border-amber-300 shrink-0" />
            <span>Buffer Zone (30m)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
