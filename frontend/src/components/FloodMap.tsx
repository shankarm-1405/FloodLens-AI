import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { 
  Layers, 
  MapPin, 
  RotateCcw, 
  Eye, 
  EyeOff, 
  Sliders, 
  Image as ImageIcon,
  Info,
  Maximize2
} from 'lucide-react';
import type { FloodAnalysisResult } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

interface FloodMapProps {
  bbox: number[]; // [minLon, minLat, maxLon, maxLat]
  analysisResult: FloodAnalysisResult | null;
  className?: string;
}

type RasterViewMode = 'none' | 'pre' | 'post' | 'diff' | 'mask';

export const FloodMap: React.FC<FloodMapProps> = ({
  bbox,
  analysisResult,
  className = 'h-[500px]'
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  
  // Layer refs
  const aoiLayerRef = useRef<L.Rectangle | null>(null);
  const geojsonLayerRef = useRef<L.GeoJSON | null>(null);
  const rasterOverlayRef = useRef<L.ImageOverlay | null>(null);

  // UI state
  const [showAoi, setShowAoi] = useState(true);
  const [showVectors, setShowVectors] = useState(true);
  const [rasterMode, setRasterMode] = useState<RasterViewMode>('none');
  const [rasterOpacity, setRasterOpacity] = useState(0.85);
  const [basemapStyle, setBasemapStyle] = useState<'dark' | 'osm' | 'imagery'>('dark');
  const [geoJsonLoading, setGeoJsonLoading] = useState(false);
  const [vectorFeatureCount, setVectorFeatureCount] = useState<number | null>(null);

  // Basemap tile layers
  const tileLayerRef = useRef<L.TileLayer | null>(null);

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

    // Custom zoom control in bottom-right
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Initial tile layer (CartoDB Dark Matter)
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

    // Invalidate size on mount after layout stabilizes
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
    let attr = '&copy; CARTO &copy; OpenStreetMap';

    if (basemapStyle === 'osm') {
      url = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
      attr = '&copy; OpenStreetMap contributors';
    } else if (basemapStyle === 'imagery') {
      url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
      attr = '&copy; Esri, Maxar, Earthstar Geographics';
    }

    tileLayerRef.current = L.tileLayer(url, {
      attribution: attr,
      maxZoom: 19
    }).addTo(mapInstanceRef.current);
  }, [basemapStyle]);

  // 3. Update AOI Rectangle
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    if (aoiLayerRef.current) {
      aoiLayerRef.current.remove();
      aoiLayerRef.current = null;
    }

    if (showAoi) {
      const rect = L.rectangle(bounds, {
        color: '#38bdf8',
        weight: 2,
        dashArray: '6, 6',
        fillColor: '#0284c7',
        fillOpacity: 0.04,
      });

      rect.bindTooltip('Trishuli River Corridor AOI Boundary', {
        permanent: false,
        direction: 'top',
        className: 'bg-slate-900 text-cyan-300 font-mono text-[11px] border border-cyan-800'
      });

      rect.addTo(mapInstanceRef.current);
      aoiLayerRef.current = rect;
    }
  }, [bbox, showAoi]);

  // 4. Load & Render Flood Vector GeoJSON Layer
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    if (geojsonLayerRef.current) {
      geojsonLayerRef.current.remove();
      geojsonLayerRef.current = null;
      setVectorFeatureCount(null);
    }

    if (!analysisResult || !showVectors) return;

    const geojsonUrl = `${API_BASE}${analysisResult.raster_metadata.geojson_file}`;
    setGeoJsonLoading(true);

    fetch(geojsonUrl)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (!mapInstanceRef.current) return;
        setVectorFeatureCount(data.features ? data.features.length : 0);

        const geoLayer = L.geoJSON(data, {
          style: (_feature) => ({
            color: '#22d3ee',
            weight: 1.5,
            fillColor: '#06b6d4',
            fillOpacity: 0.65,
          }),
          onEachFeature: (feature, layer) => {
            const props = feature.properties || {};
            layer.bindPopup(`
              <div class="p-1 space-y-1 font-sans text-xs">
                <div class="flex items-center space-x-1.5 font-bold text-cyan-300">
                  <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
                  <span>${props.class || 'CANDIDATE FLOOD'}</span>
                </div>
                <div class="text-[11px] text-slate-300">
                  ${props.description || 'Specular radar amplitude drop detected'}
                </div>
                <div class="font-mono text-[10px] text-slate-400 pt-1 border-t border-slate-700 space-y-0.5">
                  <div>Sensor: <strong class="text-white">${props.sensor || 'Sentinel-1 C-SAR'}</strong></div>
                  <div>Method: <strong class="text-white">${props.detection_method || 'Log-Ratio'}</strong></div>
                </div>
              </div>
            `);

            layer.on({
              mouseover: (e) => {
                const target = e.target;
                target.setStyle({
                  weight: 3,
                  color: '#ffffff',
                  fillOpacity: 0.85
                });
              },
              mouseout: (e) => {
                geoLayer.resetStyle(e.target);
              }
            });
          }
        });

        geoLayer.addTo(mapInstanceRef.current);
        geojsonLayerRef.current = geoLayer;

        // Auto-fit to features if available
        if (data.features && data.features.length > 0) {
          const geoBounds = geoLayer.getBounds();
          if (geoBounds.isValid()) {
            mapInstanceRef.current.fitBounds(geoBounds, { padding: [30, 30] });
          }
        }
      })
      .catch((err) => {
        console.warn('Failed to load flood GeoJSON layer:', err);
      })
      .finally(() => {
        setGeoJsonLoading(false);
      });
  }, [analysisResult, showVectors]);

  // 5. Render Raster Image Overlays (Pre, Post, Diff, Mask previews)
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    if (rasterOverlayRef.current) {
      rasterOverlayRef.current.remove();
      rasterOverlayRef.current = null;
    }

    if (!analysisResult || rasterMode === 'none') return;

    let previewUrl: string | undefined;
    if (rasterMode === 'pre') {
      previewUrl = analysisResult.raster_metadata.pre_preview;
    } else if (rasterMode === 'post') {
      previewUrl = analysisResult.raster_metadata.post_preview;
    } else if (rasterMode === 'diff') {
      previewUrl = analysisResult.raster_metadata.diff_preview;
    } else if (rasterMode === 'mask') {
      previewUrl = analysisResult.raster_metadata.mask_preview;
    }

    if (!previewUrl) return;

    const fullUrl = `${API_BASE}${previewUrl}`;
    const overlay = L.imageOverlay(fullUrl, bounds, {
      opacity: rasterOpacity,
      interactive: false,
    });

    overlay.addTo(mapInstanceRef.current);
    rasterOverlayRef.current = overlay;

    // If vectors are active, bring vectors to front
    if (geojsonLayerRef.current) {
      geojsonLayerRef.current.bringToFront();
    }
  }, [analysisResult, rasterMode, rasterOpacity, bbox]);

  const handleResetView = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.fitBounds(bounds, { padding: [25, 25] });
    }
  };

  return (
    <div className="relative rounded-2xl overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl">
      {/* Top Controls Bar */}
      <div className="px-4 py-2.5 bg-slate-900/95 border-b border-slate-800 backdrop-blur-md flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center space-x-2">
          <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-white font-semibold">Trishuli River Spatial Viewport</span>
          <span className="text-slate-500 hidden sm:inline">|</span>
          <span className="text-slate-400 text-[11px] hidden sm:inline">EPSG:4326 • 10m Ground Resolution</span>
        </div>

        <div className="flex items-center space-x-2">
          {/* Basemap Switcher */}
          <div className="flex rounded-lg bg-slate-950 p-0.5 border border-slate-800 text-[11px]">
            <button
              onClick={() => setBasemapStyle('dark')}
              className={`px-2 py-1 rounded transition-all cursor-pointer ${
                basemapStyle === 'dark' ? 'bg-cyan-900/80 text-cyan-200 font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Dark
            </button>
            <button
              onClick={() => setBasemapStyle('osm')}
              className={`px-2 py-1 rounded transition-all cursor-pointer ${
                basemapStyle === 'osm' ? 'bg-cyan-900/80 text-cyan-200 font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              OSM
            </button>
            <button
              onClick={() => setBasemapStyle('imagery')}
              className={`px-2 py-1 rounded transition-all cursor-pointer ${
                basemapStyle === 'imagery' ? 'bg-cyan-900/80 text-cyan-200 font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Satellite
            </button>
          </div>

          <button
            onClick={handleResetView}
            title="Reset to AOI Extent"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-all cursor-pointer border border-slate-700"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Map Canvas */}
      <div ref={mapContainerRef} className={`w-full ${className} z-0`} />

      {/* Loading overlay for GeoJSON */}
      {geoJsonLoading && (
        <div className="absolute inset-0 bg-slate-950/40 backdrop-blur-[1px] flex items-center justify-center z-10 pointer-events-none">
          <div className="bg-slate-900/90 border border-slate-800 px-4 py-2 rounded-xl text-xs font-mono text-cyan-300 flex items-center space-x-2 shadow-xl">
            <span className="w-3.5 h-3.5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            <span>Rendering Candidate Flood Polygons...</span>
          </div>
        </div>
      )}

      {/* Bottom Floating Control Panel & Legend */}
      <div className="absolute bottom-4 left-4 z-20 max-w-sm w-full space-y-2 pointer-events-auto">
        {/* Raster Layer & Before/After Imagery Selector */}
        {analysisResult && (
          <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 backdrop-blur-md shadow-xl text-xs space-y-2">
            <div className="flex items-center justify-between font-mono text-slate-300">
              <span className="flex items-center space-x-1.5 font-bold text-white text-[11px] uppercase">
                <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
                <span>SAR Amplitude & Difference</span>
              </span>
              <span className="text-[10px] text-slate-400">Before / After</span>
            </div>

            <div className="grid grid-cols-4 gap-1 text-[10px] font-mono">
              <button
                onClick={() => setRasterMode(rasterMode === 'pre' ? 'none' : 'pre')}
                className={`py-1 px-1.5 rounded text-center transition-all cursor-pointer ${
                  rasterMode === 'pre' 
                    ? 'bg-sky-600 text-white font-bold' 
                    : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                Pre-SAR
              </button>
              <button
                onClick={() => setRasterMode(rasterMode === 'post' ? 'none' : 'post')}
                className={`py-1 px-1.5 rounded text-center transition-all cursor-pointer ${
                  rasterMode === 'post' 
                    ? 'bg-sky-600 text-white font-bold' 
                    : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                Post-SAR
              </button>
              <button
                onClick={() => setRasterMode(rasterMode === 'diff' ? 'none' : 'diff')}
                className={`py-1 px-1.5 rounded text-center transition-all cursor-pointer ${
                  rasterMode === 'diff' 
                    ? 'bg-cyan-600 text-white font-bold' 
                    : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                Δ Ratio
              </button>
              <button
                onClick={() => setRasterMode(rasterMode === 'mask' ? 'none' : 'mask')}
                className={`py-1 px-1.5 rounded text-center transition-all cursor-pointer ${
                  rasterMode === 'mask' 
                    ? 'bg-emerald-600 text-white font-bold' 
                    : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                Mask
              </button>
            </div>

            {rasterMode !== 'none' && (
              <div className="pt-1 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                <span className="text-slate-400">Opacity: {Math.round(rasterOpacity * 100)}%</span>
                <input
                  type="range"
                  min="0.2"
                  max="1.0"
                  step="0.05"
                  value={rasterOpacity}
                  onChange={(e) => setRasterOpacity(parseFloat(e.target.value))}
                  className="w-24 accent-cyan-500 cursor-pointer"
                />
              </div>
            )}
          </div>
        )}

        {/* Legend Card */}
        <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 backdrop-blur-md shadow-xl text-xs space-y-2">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-300 font-bold uppercase">
            <span>Map Layers & Legend</span>
            {vectorFeatureCount !== null && (
              <span className="text-[10px] text-cyan-400 lowercase font-normal">
                {vectorFeatureCount} flood polygons
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] font-sans">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showVectors}
                onChange={(e) => setShowVectors(e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0"
              />
              <span className="flex items-center space-x-1.5">
                <span className="w-3 h-3 rounded bg-cyan-400/80 border border-cyan-300 shrink-0" />
                <span className="text-slate-200">Candidate Flood</span>
              </span>
            </label>

            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showAoi}
                onChange={(e) => setShowAoi(e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-sky-500 focus:ring-0"
              />
              <span className="flex items-center space-x-1.5">
                <span className="w-3 h-3 rounded border-2 border-dashed border-sky-400 shrink-0" />
                <span className="text-slate-200">AOI Perimeter</span>
              </span>
            </label>

            <div className="flex items-center space-x-1.5 opacity-90">
              <span className="w-3 h-3 rounded bg-blue-600 border border-blue-400 shrink-0" />
              <span className="text-slate-300 text-[10.5px]">Permanent Water</span>
            </div>

            <div className="flex items-center space-x-1.5 opacity-90">
              <span className="w-3 h-3 rounded bg-amber-700 border border-amber-500 shrink-0" />
              <span className="text-slate-300 text-[10.5px]">DEM Slope &gt; 15°</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
