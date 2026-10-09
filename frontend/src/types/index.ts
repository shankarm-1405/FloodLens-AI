export type PageId =
  | 'overview'
  | 'flood-analysis'
  | 'infrastructure'
  | 'connectivity'
  | 'ai-report'
  | 'methodology'
  | 'limitations';

export interface BoundingBox {
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'offline';
  timestamp: string;
  service: string;
  demo_mode: boolean;
  geospatial_stack: {
    rasterio?: { available: boolean; version?: string };
    shapely?: { available: boolean; version?: string };
    geopandas?: { available: boolean; version?: string };
    networkx?: { available: boolean; version?: string };
  };
  study_case: {
    region: string;
    default_bbox: number[];
    default_event_date: string;
    osm_snapshot_date: string;
  };
}

export interface ConfigStatus {
  demo_mode: boolean;
  cdse_configured: boolean;
  cdse_auth_type: string;
  osm_snapshot_date: string;
  osm_overpass_endpoint: string;
  llm_grounding_configured: boolean;
  llm_provider: string;
  default_aoi_bbox: number[];
  default_event_date: string;
}

export interface S1Acquisition {
  id: string;
  name: string;
  platform: string;
  instrument: string;
  product_type: string;
  acquisition_date: string;
  orbit_pass: string;
  relative_orbit: number | null;
  polarization: string;
  timing_relation: 'PRE_EVENT' | 'POST_EVENT';
  days_from_event: number;
  footprint_wkt?: string;
  is_demo_fixture?: boolean;
}

export interface CompatiblePair {
  pre_event_scene: S1Acquisition;
  post_event_scene: S1Acquisition;
  compatibility_score: number;
  compatibility_level: 'OPTIMAL' | 'SUBOPTIMAL' | 'INCOMPATIBLE';
  explanation: string;
  detailed_criteria: string[];
  temporal_separation_days: number;
  label?: string;
}

export interface S2Acquisition {
  id: string;
  name: string;
  platform: string;
  instrument: string;
  product_type: string;
  acquisition_date: string;
  cloud_cover_percentage: number;
  recommendation: string;
  footprint_wkt?: string;
  is_demo_fixture?: boolean;
}

export interface SatelliteSearchResult {
  mode: 'REAL_DATA_MODE' | 'DEMONSTRATION_MODE';
  is_demo_fixture: boolean;
  disclaimer?: string;
  query_parameters: {
    bbox: number[];
    event_date: string;
    window_days: number;
  };
  sentinel1: {
    total_found: number;
    pre_event_acquisitions: S1Acquisition[];
    post_event_acquisitions: S1Acquisition[];
    compatible_pairs: CompatiblePair[];
    best_compatible_pair?: CompatiblePair | null;
  };
  sentinel2?: {
    total_found: number;
    acquisitions: S2Acquisition[];
  };
  provenance: {
    source: string;
    catalogue_endpoint?: string;
    legal_attribution: string;
  };
  errors?: string[];
}

export interface CredentialsStatus {
  configured: boolean;
  token_active: boolean;
  auth_method: string;
  guidance: {
    registration_portal: string;
    instructions: string;
  };
}

export interface FloodAnalysisResult {
  analysis_id: string;
  created_at: string;
  status: 'COMPLETED' | 'PROCESSING' | 'FAILED';
  is_demo_fixture: boolean;
  data_notice: string;
  area_of_interest: {
    bbox: number[];
    region: string;
  };
  source_acquisitions: {
    pre_event: S1Acquisition;
    post_event: S1Acquisition;
  };
  parameters: {
    threshold_db: number;
    min_water_backscatter_db: number;
    slope_threshold_deg: number;
    filter_kernel_size: number;
    min_polygon_pixels: number;
    target_crs: string;
  };
  pixel_counts: {
    total_pixels: number;
    valid_pixels: number;
    nodata_pixels: number;
    unaffected_land_pixels: number;
    candidate_flood_pixels: number;
    permanent_water_pixels: number;
    terrain_shadow_pixels: number;
  };
  area_statistics: {
    pixel_area_sqm: number;
    candidate_flood_area_sqkm: number;
    permanent_water_area_sqkm: number;
    terrain_masked_area_sqkm: number;
    total_analyzed_area_sqkm: number;
    valid_coverage_ratio: number;
  };
  raster_metadata: {
    dimensions: number[];
    crs: string;
    geotransform: number[];
    geotiff_file: string;
    geojson_file: string;
  };
  warnings_and_uncertainties: string[];
  legal_attributions: string[];
}

export interface InfrastructureExposure {
  analysis_id: string;
  osm_snapshot_reference: string;
  query_timestamp: string;
  exposed_buildings_count: number;
  exposed_road_length_km: number;
  exposed_bridges_count: number;
  buffer_zone_buildings_count: number;
  critical_facilities_exposed: {
    name: string;
    type: 'hospital' | 'clinic' | 'school' | 'substation';
    coordinates: [number, number];
    distance_to_water_m: number;
  }[];
  is_demo_fixture: boolean;
}

export interface SettlementConnectivity {
  analysis_id: string;
  target_hub: string;
  total_settlements_evaluated: number;
  isolated_settlements_count: number;
  penalized_route_count: number;
  settlement_details: {
    name: string;
    pre_event_travel_dist_km: number;
    post_event_status: 'Connected' | 'Isolated' | 'Detoured';
    post_event_travel_dist_km: number | null;
    isolated_reason?: string;
  }[];
  is_demo_fixture: boolean;
}

export interface SituationReport {
  analysis_id: string;
  generated_at: string;
  language: 'en' | 'ne';
  is_demo_fixture: boolean;
  llm_grounded: boolean;
  title: string;
  executive_summary: string;
  estimated_flood_extent: string;
  infrastructure_impact: string;
  settlement_isolation: string;
  key_uncertainties_and_limitations: string;
  provenance_and_citations: string;
  disclaimer: string;
}
