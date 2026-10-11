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
    pre_preview?: string;
    post_preview?: string;
    diff_preview?: string;
    mask_preview?: string;
  };
  warnings_and_uncertainties: string[];
  legal_attributions: string[];
}

export interface FacilityDetail {
  osm_id: number | string;
  name: string;
  facility_type: string;
  coordinates: [number, number];
  exposure_status: 'DIRECTLY_INTERSECTING' | 'BUFFER_ZONE_30M' | 'SAFE_ELEVATED';
  distance_to_flood_m: number;
  beds?: string;
  emergency?: string;
}

export type ProvenanceType = 
  | 'REAL_SATELLITE_DERIVED'
  | 'VERIFIED_HISTORICAL_OSM'
  | 'CURRENT_OSM_PREVIEW'
  | 'SYNTHETIC_TEST_FIXTURE'
  | 'UNAVAILABLE'
  | 'REAL_DATA_ANALYSIS'
  | 'HISTORICAL_SNAPSHOT_UNAVAILABLE';

export interface InfrastructureExposureSummary {
  analysis_id: string;
  created_at: string;
  status: string;
  provenance: ProvenanceType;
  is_synthetic: boolean;
  data_notice: string;
  osm_source: string;
  osm_snapshot_date: string;
  osm_attribution: string;
  aoi_bbox: number[];
  total_infrastructure_assessed: number;
  valid_geometry_count: number;
  invalid_geometry_count: number;
  exposed_buildings_count: number | null;
  exposed_building_area_sqm: number | null;
  exposed_building_area_sqkm: number | null;
  exposed_road_length_km: number | null;
  exposed_bridges_count: number | null;
  critical_facilities_assessed: number;
  critical_facilities_intersecting: number | null;
  critical_facilities_in_buffer: number | null;
  critical_facilities_details: FacilityDetail[];
  settlements_intersecting_count?: number;
  blocker_reason?: string | null;
  limitations_and_uncertainties: string[];
}

export interface InfrastructureExposure extends InfrastructureExposureSummary {}

export interface SettlementDetail {
  name: string;
  osm_id?: number | string;
  status: 'NEWLY_DISCONNECTED' | 'ALREADY_DISCONNECTED' | 'DETOURED' | 'UNCHANGED' | 'SNAP_FAILED' | 'UNAVAILABLE';
  isolation_cause: string;
  coordinates: [number, number] | null;
  nearest_hub: string | null;
  snapped_distance_m?: number | null;
  baseline_distance_km: number | null;
  baseline_travel_time_minutes: number | null;
  post_flood_distance_km: number | null;
  post_flood_travel_time_minutes: number | null;
  detour_distance_km: number | null;
  detour_travel_time_minutes: number | null;
  hub_connections?: Record<string, any>;
}

export interface HubDetail {
  name: string;
  status: 'SNAPPED' | 'SNAP_FAILED' | 'UNAVAILABLE';
  nearest_node?: string | null;
  distance_m?: number | null;
  coordinates?: [number, number] | null;
  reason?: string;
}

export interface ConnectivitySummary {
  analysis_id: string;
  status: string;
  provenance: string;
  is_synthetic: boolean;
  data_notice: string;
  flood_analysis_id: string;
  flood_provenance: string;
  infrastructure_provenance: string;
  osm_snapshot_date: string;
  osm_attribution: string;
  graph_construction_settings: {
    projected_crs: string;
    snapping_tolerance_m: number;
    max_settlement_snap_distance_m: number;
    elevation_separation_handled: boolean;
    nodes_count: number;
    edges_count: number;
    connected_components_count: number;
    total_road_length_km: number;
    invalid_geometries_count: number;
    roads_omitted_count: number;
  };
  closure_parameters: {
    road_closure_method: string;
    closed_edges_count: number;
    closed_bridges_count: number;
    closure_description: string;
  };
  speed_assumptions: {
    speeds_kmh: Record<string, number>;
    notice: string;
  };
  summary_counts: {
    settlements_evaluated: number;
    settlements_matched_and_snapped: number;
    newly_disconnected: number;
    already_disconnected_at_baseline: number;
    detoured: number;
    route_unchanged: number;
    unavailable: number;
    snap_failed: number;
  };
  settlement_details: SettlementDetail[];
  regional_hubs: Record<string, HubDetail>;
  output_files: {
    summary_json: string;
    routes_geojson: string;
    closed_roads_geojson: string;
  };
  limitations_and_uncertainties: string[];
}

export interface SettlementConnectivity extends ConnectivitySummary {}

export interface SituationReport {
  report_id: string;
  title: string;
  analysis_id: string;
  generated_at: string;
  language: 'en' | 'ne';
  generation_method: string;
  provenance: string;
  is_synthetic: boolean;
  data_notice: string;
  study_area: string;
  bbox: number[];
  event_date: string;
  disclaimer: string;
  sections: {
    executive_summary: string;
    flood_extent_and_coverage: string;
    infrastructure_exposure: string;
    settlement_connectivity_and_isolation: string;
    confidence_and_data_limitations: string;
    recommended_next_steps: string;
    data_attributions: string;
  };
  summary_metrics: {
    candidate_flood_area_sqkm: number | null;
    permanent_water_area_sqkm: number | null;
    exposed_buildings_count: number | null;
    exposed_road_length_km: number | null;
    exposed_bridges_count: number | null;
    critical_facilities_intersecting: number | null;
    settlements_evaluated: number | null;
    newly_disconnected_count: number | null;
    already_disconnected_count: number | null;
    detoured_count: number | null;
  };
}

export interface ReportStatusResponse {
  analysis_id: string;
  input_readiness: {
    flood_data: boolean;
    infrastructure_data: boolean;
    connectivity_data: boolean;
    all_inputs_ready: boolean;
  };
  reports_available: {
    en: boolean;
    ne: boolean;
  };
  download_links: {
    markdown_en: string;
    markdown_ne: string;
    pdf_en: string;
    pdf_ne: string;
  };
}
