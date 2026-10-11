"""
Historical OpenStreetMap Infrastructure Exposure Analysis Module
FloodLens AI - Phase 4: Trishuli River Corridor, Nepal

Performs spatial intersection and proximity analysis between Sentinel-1 flood candidate
polygons and pre-event OpenStreetMap infrastructure (buildings, roads, bridges, facilities).
Strictly adheres to:
1. Historical baseline date anchoring (2026-07-27T00:00:00Z)
2. Geodesic/projected UTM Zone 45N metric calculations (EPSG:32645)
3. Non-duplication of OSM IDs and split segments
4. Terminology: 'potentially exposed infrastructure' (not confirmed damage)
5. Provenance tracking (REAL_DATA_ANALYSIS vs SYNTHETIC_TEST_FIXTURE vs CURRENT_OSM_PREVIEW)
6. Mandatory attribution: © OpenStreetMap contributors.
"""

import os
import re
import json
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import requests
import geopandas as gpd
import shapely
from shapely.geometry import shape, mapping, Point, Polygon, MultiPolygon, LineString, MultiLineString
from shapely.validation import make_valid
import pyproj

from app.config import settings, OUTPUTS_DIR, CACHE_DIR
from app.fixtures.osm_trishuli_fixture import (
    HISTORICAL_TRISHULI_OSM_FIXTURE,
    OSM_SNAPSHOT_TIMESTAMP,
    OSM_ATTRIBUTION
)

# Cache directory dedicated to OSM data
OSM_CACHE_DIR = CACHE_DIR / "osm"
OSM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Projected CRS for Nepal (UTM Zone 45N in meters)
PROJECTED_CRS_NEPAL = "EPSG:32645"
GEOGRAPHIC_CRS = "EPSG:4326"


class InfrastructureError(Exception):
    """Base exception for infrastructure and exposure analysis errors."""
    pass


class HistoricalSnapshotUnavailableError(InfrastructureError):
    """Raised when the required historical OSM snapshot is unreachable or unavailable."""
    pass


class MissingFloodAnalysisError(InfrastructureError):
    """Raised when the specified flood analysis output does not exist or is invalid."""
    pass


class InvalidGeometryError(InfrastructureError):
    """Raised when infrastructure geometries are unrecoverable or invalid."""
    pass


def validate_analysis_id(analysis_id: str) -> str:
    """
    Sanitizes and enforces safe format for analysis IDs, preventing directory traversal.
    """
    if not re.match(r"^[a-zA-Z0-9_\-]+$", analysis_id):
        raise InfrastructureError("Invalid analysis ID: must contain only alphanumeric characters, dashes, and underscores.")
    resolved = (OUTPUTS_DIR / analysis_id).resolve()
    try:
        resolved.relative_to(OUTPUTS_DIR.resolve())
    except ValueError:
        raise InfrastructureError("Path traversal attempt detected in analysis ID.")
    return analysis_id


class OSMInfrastructureClient:
    """
    Client for retrieving, clipping, validating, and caching OpenStreetMap infrastructure.
    Supports historical snapshots (ohsome / Overpass attic) and live previews.
    """

    def __init__(self):
        self.attribution = OSM_ATTRIBUTION
        self.default_snapshot_date = settings.OSM_SNAPSHOT_DATE or "2026-07-27"
        self.overpass_url = settings.OSM_OVERPASS_ENDPOINT
        self.ohsome_url = "https://api.ohsome.org/v1"

    def validate_aoi_bbox(self, bbox: List[float]) -> None:
        """Validates bounding box coordinates [min_lon, min_lat, max_lon, max_lat]."""
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            raise ValueError("Bounding box must be a list of 4 coordinates [min_lon, min_lat, max_lon, max_lat]")
        min_lon, min_lat, max_lon, max_lat = bbox
        if not (-180.0 <= min_lon < max_lon <= 180.0):
            raise ValueError(f"Invalid longitude span [{min_lon}, {max_lon}]")
        if not (-90.0 <= min_lat < max_lat <= 90.0):
            raise ValueError(f"Invalid latitude span [{min_lat}, {max_lat}]")

    def clip_geojson_to_bbox(self, geojson_data: Dict[str, Any], bbox: List[float]) -> Dict[str, Any]:
        """
        Spatially filters GeoJSON features strictly within or intersecting the AOI bounding box.
        """
        self.validate_aoi_bbox(bbox)
        min_lon, min_lat, max_lon, max_lat = bbox
        aoi_poly = shapely.geometry.box(min_lon, min_lat, max_lon, max_lat)

        clipped_features = []
        for feat in geojson_data.get("features", []):
            geom_dict = feat.get("geometry")
            if not geom_dict:
                continue
            try:
                geom = shape(geom_dict)
                if geom.intersects(aoi_poly):
                    clipped_features.append(feat)
            except Exception:
                continue

        result = dict(geojson_data)
        result["features"] = clipped_features
        if "metadata" in result:
            result["metadata"]["clipped_bbox"] = bbox
            result["metadata"]["feature_count_total"] = len(clipped_features)
        return result

    def validate_and_clean_geometries(self, features: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int, int, int]:
        """
        Validates and cleans feature geometries using shapely.validation.make_valid.
        Returns: (cleaned_features, valid_count, repaired_count, invalid_dropped_count)
        """
        cleaned = []
        valid_cnt = 0
        repaired_cnt = 0
        dropped_cnt = 0

        for f in features:
            geom_dict = f.get("geometry")
            if not geom_dict:
                dropped_cnt += 1
                continue
            try:
                geom = shape(geom_dict)
                if geom.is_empty:
                    dropped_cnt += 1
                    continue
                if geom.is_valid:
                    valid_cnt += 1
                    cleaned.append(f)
                else:
                    fixed_geom = make_valid(geom)
                    if fixed_geom.is_empty:
                        dropped_cnt += 1
                    else:
                        f_copy = dict(f)
                        f_copy["geometry"] = mapping(fixed_geom)
                        repaired_cnt += 1
                        cleaned.append(f_copy)
            except Exception:
                dropped_cnt += 1

        return cleaned, valid_cnt, repaired_cnt, dropped_cnt

    def fetch_historical_infrastructure(
        self,
        bbox: Optional[List[float]] = None,
        snapshot_date: Optional[str] = None,
        force_live: bool = False,
        allow_fallback_fixture: bool = True,
        timeout: int = 6
    ) -> Dict[str, Any]:
        """
        Retrieves historical infrastructure data anchored to snapshot_date (default: 2026-07-27).
        Attempts remote historical retrieval (ohsome/overpass attic).
        If remote historical archive times out or is unavailable:
        - If allow_fallback_fixture=True: returns verified historical baseline fixture with explicit notice.
        - If allow_fallback_fixture=False: raises HistoricalSnapshotUnavailableError.
        """
        target_bbox = bbox if bbox is not None else settings.DEFAULT_AOI_BBOX
        self.validate_aoi_bbox(target_bbox)
        target_date = snapshot_date or self.default_snapshot_date

        cache_filename = f"osm_hist_{target_date.replace('-', '').replace(':', '')}_{target_bbox[0]}_{target_bbox[1]}_{target_bbox[2]}_{target_bbox[3]}.geojson"
        cache_path = OSM_CACHE_DIR / cache_filename

        # 1. Return from disk cache if present and not force_live
        if cache_path.exists() and not force_live:
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                return cached_data
            except Exception:
                pass

        # 2. Attempt remote historical retrieval
        remote_error_reason: Optional[str] = None
        try:
            # Query Overpass Attic date
            # Date format for Overpass: YYYY-MM-DDTHH:MM:SSZ
            attic_iso = f"{target_date}T00:00:00Z" if "T" not in target_date else target_date
            south, west, north, east = target_bbox[1], target_bbox[0], target_bbox[3], target_bbox[2]
            overpass_q = f"""
            [out:json][timeout:{timeout}][date:"{attic_iso}"];
            (
              node["amenity"~"hospital|clinic"]({south},{west},{north},{east});
              way["amenity"~"hospital|clinic"]({south},{west},{north},{east});
              node["place"~"town|village|hamlet"]({south},{west},{north},{east});
              way["bridge"="yes"]({south},{west},{north},{east});
              way["highway"~"primary|secondary|trunk|tertiary|residential"]({south},{west},{north},{east});
              way["building"]({south},{west},{north},{east});
            );
            out body;
            >;
            out skel qt;
            """
            resp = requests.post(self.overpass_url, data={"data": overpass_q}, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if "elements" in data and len(data["elements"]) > 0:
                    # Successfully retrieved remote attic data
                    converted_fc = self._convert_overpass_to_geojson(data, attic_iso, target_bbox, "LIVE_OVERPASS_ATTIC")
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(converted_fc, f, indent=2)
                    return converted_fc
                else:
                    remote_error_reason = "Overpass Attic returned empty element list for target timestamp"
            else:
                remote_error_reason = f"Overpass Attic HTTP {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.Timeout:
            remote_error_reason = f"Remote historical archive request timed out after {timeout}s (api.ohsome.org / overpass attic)"
        except requests.exceptions.RequestException as e:
            remote_error_reason = f"Remote historical archive network error: {str(e)}"
        except Exception as e:
            remote_error_reason = f"Unexpected error during historical retrieval: {str(e)}"

        # 3. Handle fallback or raise blocker
        if not allow_fallback_fixture:
            raise HistoricalSnapshotUnavailableError(
                f"Historical OSM snapshot for {target_date} is unavailable. Blocker: {remote_error_reason}"
            )

        # Use verified pre-event baseline fixture
        baseline_fc = json.loads(json.dumps(HISTORICAL_TRISHULI_OSM_FIXTURE))
        clipped_fc = self.clip_geojson_to_bbox(baseline_fc, target_bbox)
        clipped_fc["metadata"]["provenance"] = "DEMO_HISTORICAL_SNAPSHOT_20260727"
        clipped_fc["metadata"]["is_fallback_fixture"] = True
        clipped_fc["metadata"]["remote_blocker_reason"] = remote_error_reason
        clipped_fc["metadata"]["retrieval_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Cache baseline for immediate reuse
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(clipped_fc, f, indent=2)

        return clipped_fc

    def fetch_current_preview(
        self,
        bbox: Optional[List[float]] = None,
        timeout: int = 8
    ) -> Dict[str, Any]:
        """
        Retrieves current live OpenStreetMap data for preview purposes.
        Mandatory Rule: Must be explicitly labeled CURRENT_OSM_PREVIEW and never presented as historical data.
        """
        target_bbox = bbox if bbox is not None else settings.DEFAULT_AOI_BBOX
        self.validate_aoi_bbox(target_bbox)
        cache_filename = f"osm_current_preview_{target_bbox[0]}_{target_bbox[1]}_{target_bbox[2]}_{target_bbox[3]}.geojson"
        cache_path = OSM_CACHE_DIR / cache_filename

        south, west, north, east = target_bbox[1], target_bbox[0], target_bbox[3], target_bbox[2]
        overpass_q = f"""
        [out:json][timeout:{timeout}];
        (
          node["amenity"~"hospital|clinic"]({south},{west},{north},{east});
          way["amenity"~"hospital|clinic"]({south},{west},{north},{east});
          node["place"~"town|village|hamlet"]({south},{west},{north},{east});
          way["bridge"="yes"]({south},{west},{north},{east});
          way["highway"~"primary|secondary|trunk|tertiary"]({south},{west},{north},{east});
        );
        out body;
        >;
        out skel qt;
        """
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            resp = requests.post(self.overpass_url, data={"data": overpass_q}, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                fc = self._convert_overpass_to_geojson(data, now_iso, target_bbox, "CURRENT_OSM_PREVIEW")
                fc["metadata"]["data_notice"] = (
                    "CURRENT DATA PREVIEW — This dataset represents the current OpenStreetMap state, "
                    "NOT the required pre-event historical baseline of 27 July 2026."
                )
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(fc, f, indent=2)
                return fc
        except Exception:
            pass

        # If live network query failed, return cached preview if available
        if cache_path.exists():
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        raise InfrastructureError("Unable to retrieve live OpenStreetMap preview due to network timeout.")

    def _convert_overpass_to_geojson(
        self,
        overpass_json: Dict[str, Any],
        snapshot_date: str,
        bbox: List[float],
        provenance: str
    ) -> Dict[str, Any]:
        """Converts Overpass elements to a clean GeoJSON FeatureCollection."""
        nodes = {}
        features = []

        for elem in overpass_json.get("elements", []):
            if elem.get("type") == "node":
                nodes[elem["id"]] = (elem.get("lon"), elem.get("lat"))
                tags = elem.get("tags", {})
                if tags:
                    category = "settlement" if "place" in tags else ("healthcare" if tags.get("amenity") in ("hospital", "clinic") else "point")
                    features.append({
                        "type": "Feature",
                        "id": f"node/{elem['id']}",
                        "properties": {
                            "osm_id": elem["id"],
                            "osm_type": "node",
                            "category": category,
                            **tags
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [elem.get("lon"), elem.get("lat")]
                        }
                    })

        for elem in overpass_json.get("elements", []):
            if elem.get("type") == "way":
                way_nodes = elem.get("nodes", [])
                coords = [nodes[nid] for nid in way_nodes if nid in nodes]
                if len(coords) < 2:
                    continue
                tags = elem.get("tags", {})
                category = "road"
                if "bridge" in tags:
                    category = "bridge"
                elif "building" in tags:
                    category = "building"
                elif tags.get("amenity") in ("hospital", "clinic"):
                    category = "healthcare"

                # Check if closed polygon
                geom_type = "LineString"
                geom_coords = coords
                if coords[0] == coords[-1] and len(coords) >= 4 and category in ("building", "healthcare"):
                    geom_type = "Polygon"
                    geom_coords = [coords]

                features.append({
                    "type": "Feature",
                    "id": f"way/{elem['id']}",
                    "properties": {
                        "osm_id": elem["id"],
                        "osm_type": "way",
                        "category": category,
                        **tags
                    },
                    "geometry": {
                        "type": geom_type,
                        "coordinates": geom_coords
                    }
                })

        return {
            "type": "FeatureCollection",
            "name": f"OSM_Infrastructure_{provenance}",
            "crs": {"type": "name", "properties": {"name": GEOGRAPHIC_CRS}},
            "metadata": {
                "snapshot_date": snapshot_date,
                "provenance": provenance,
                "aoi_bbox": bbox,
                "attribution": self.attribution,
                "feature_count_total": len(features)
            },
            "features": features
        }


class InfrastructureExposureEngine:
    """
    Spatially compares Sentinel-1 candidate flood extents against pre-event infrastructure.
    Calculates metric exposure for buildings, roads, bridges, and emergency facilities.
    """

    def __init__(self, osm_client: Optional[OSMInfrastructureClient] = None):
        self.osm_client = osm_client or OSMInfrastructureClient()

    def get_flood_polygons_from_analysis(self, analysis_id: str) -> Tuple[gpd.GeoDataFrame, Dict[str, Any], bool]:
        """
        Reads validated Phase 3 flood-candidate GeoJSON and metadata for an analysis ID.
        Returns: (flood_gdf, metadata_dict, is_synthetic_fixture)
        """
        clean_id = validate_analysis_id(analysis_id)
        analysis_dir = OUTPUTS_DIR / clean_id

        if not analysis_dir.exists():
            raise MissingFloodAnalysisError(f"Analysis directory '{clean_id}' does not exist.")

        metadata_path = analysis_dir / "analysis_metadata.json"
        geojson_path = analysis_dir / "flood_candidate_mask.geojson"

        if not metadata_path.exists():
            raise MissingFloodAnalysisError(f"Missing analysis_metadata.json in analysis '{clean_id}'.")
        if not geojson_path.exists() or geojson_path.stat().st_size == 0:
            raise MissingFloodAnalysisError(f"Missing or empty flood_candidate_mask.geojson in analysis '{clean_id}'.")

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        with open(geojson_path, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)

        features = geojson_data.get("features", [])
        if not features:
            raise MissingFloodAnalysisError(f"Flood analysis '{clean_id}' contains 0 candidate flood polygons.")

        geoms = []
        for feat in features:
            geom_dict = feat.get("geometry")
            if geom_dict:
                try:
                    s_geom = shape(geom_dict)
                    if not s_geom.is_empty:
                        geoms.append(s_geom)
                except Exception:
                    pass

        if not geoms:
            raise MissingFloodAnalysisError(f"No valid geometries found in flood mask GeoJSON for '{clean_id}'.")

        flood_gdf = gpd.GeoDataFrame(geometry=geoms, crs=GEOGRAPHIC_CRS)
        is_synthetic = bool(
            metadata.get("is_demo_fixture", False) or
            metadata.get("processing_mode") == "SYNTHETIC_TEST_FIXTURE" or
            "DEMO" in str(metadata.get("analysis_id", "")).upper()
        )

        return flood_gdf, metadata, is_synthetic

    def execute_exposure_assessment(
        self,
        analysis_id: str,
        osm_source: str = "historical",
        allow_fallback_fixture: bool = True,
        buffer_threshold_meters: float = 30.0
    ) -> Dict[str, Any]:
        """
        Executes comprehensive infrastructure exposure assessment against a validated flood analysis.
        """
        clean_id = validate_analysis_id(analysis_id)
        analysis_dir = OUTPUTS_DIR / clean_id

        # 1. Load validated flood polygons and check synthetic status
        flood_gdf, flood_meta, is_flood_synthetic = self.get_flood_polygons_from_analysis(clean_id)
        aoi_bbox = flood_meta.get("area_of_interest", {}).get("bbox", settings.DEFAULT_AOI_BBOX)

        # 2. Retrieve infrastructure dataset
        blocker_reason: Optional[str] = None
        used_provenance = "VERIFIED_HISTORICAL_OSM"

        try:
            if osm_source == "current_preview":
                osm_data = self.osm_client.fetch_current_preview(bbox=aoi_bbox)
                used_provenance = "CURRENT_OSM_PREVIEW"
            else:
                osm_data = self.osm_client.fetch_historical_infrastructure(
                    bbox=aoi_bbox,
                    snapshot_date=self.osm_client.default_snapshot_date,
                    allow_fallback_fixture=allow_fallback_fixture
                )
                if osm_data.get("metadata", {}).get("is_fallback_fixture"):
                    used_provenance = "SYNTHETIC_TEST_FIXTURE"
                    blocker_reason = osm_data.get("metadata", {}).get("remote_blocker_reason")
        except HistoricalSnapshotUnavailableError as e:
            # Explicitly report blocker — do NOT fabricate zero counts
            return {
                "analysis_id": clean_id,
                "status": "BLOCKED",
                "provenance": "UNAVAILABLE",
                "is_synthetic": False,
                "blocker_reason": str(e),
                "osm_attribution": OSM_ATTRIBUTION,
                "osm_snapshot_date": self.osm_client.default_snapshot_date,
                "exposed_buildings_count": None,
                "exposed_building_area_sqm": None,
                "exposed_building_area_sqkm": None,
                "exposed_road_length_km": None,
                "exposed_bridges_count": None,
                "critical_facilities_assessed": 0,
                "critical_facilities_intersecting": None,
                "critical_facilities_in_buffer": None,
                "critical_facilities_details": [],
                "limitations_and_uncertainties": [
                    "Required historical OpenStreetMap snapshot (2026-07-27) is unreachable from remote archive.",
                    "Exposure calculations blocked to prevent substituting inaccurate current data without notice."
                ]
            }

        # If flood mask is synthetic, enforce SYNTHETIC_TEST_FIXTURE provenance
        if is_flood_synthetic:
            used_provenance = "SYNTHETIC_TEST_FIXTURE"

        # 3. Clean and validate OSM geometries
        raw_features = osm_data.get("features", [])
        total_assessed = len(raw_features)
        cleaned_features, valid_cnt, repaired_cnt, dropped_cnt = self.osm_client.validate_and_clean_geometries(raw_features)

        # 4. Project both flood mask and OSM to metric UTM Zone 45N (EPSG:32645)
        flood_utm = flood_gdf.to_crs(PROJECTED_CRS_NEPAL)
        flood_union = flood_utm.union_all()

        # Build GeoDataFrame of OSM features in UTM
        osm_records = []
        osm_geoms = []
        for f in cleaned_features:
            s_geom = shape(f["geometry"])
            osm_records.append({
                "osm_id": f["properties"].get("osm_id", f.get("id")),
                "osm_type": f["properties"].get("osm_type", "unknown"),
                "category": f["properties"].get("category", "unknown"),
                "name": f["properties"].get("name", "Unnamed"),
                "properties": f["properties"],
                "orig_feature": f
            })
            osm_geoms.append(s_geom)

        if not osm_records:
            osm_gdf = gpd.GeoDataFrame(columns=["osm_id", "category", "name", "properties"], geometry=[], crs=GEOGRAPHIC_CRS)
            osm_gdf_utm = osm_gdf
        else:
            osm_gdf = gpd.GeoDataFrame(osm_records, geometry=osm_geoms, crs=GEOGRAPHIC_CRS)
            osm_gdf_utm = osm_gdf.to_crs(PROJECTED_CRS_NEPAL)

        # 5. Spatial Exposure Calculations with Double-Counting Prevention
        # Category A: Buildings
        buildings = osm_gdf_utm[osm_gdf_utm["category"] == "building"].drop_duplicates(subset=["osm_id"])
        inter_buildings = buildings[buildings.intersects(flood_union)]
        exposed_buildings_count = int(len(inter_buildings))
        exposed_building_area_sqm = 0.0

        for _, b in inter_buildings.iterrows():
            try:
                clipped = b.geometry.intersection(flood_union)
                if not clipped.is_empty:
                    exposed_building_area_sqm += float(clipped.area)
            except Exception:
                pass
        exposed_building_area_sqkm = round(exposed_building_area_sqm / 1e6, 6)
        exposed_building_area_sqm = round(exposed_building_area_sqm, 2)

        # Category B: Roads and Tracks
        roads = osm_gdf_utm[osm_gdf_utm["category"] == "road"].drop_duplicates(subset=["osm_id"])
        inter_roads = roads[roads.intersects(flood_union)]
        exposed_road_length_km = 0.0

        for _, r in inter_roads.iterrows():
            try:
                clipped_line = r.geometry.intersection(flood_union)
                if not clipped_line.is_empty:
                    exposed_road_length_km += float(clipped_line.length) / 1000.0
            except Exception:
                pass
        exposed_road_length_km = round(exposed_road_length_km, 3)

        # Category C: Bridges
        bridges = osm_gdf_utm[osm_gdf_utm["category"] == "bridge"].drop_duplicates(subset=["osm_id"])
        inter_bridges = bridges[bridges.intersects(flood_union)]
        exposed_bridges_count = int(len(inter_bridges))

        # Category D: Healthcare and Emergency Facilities
        facilities = osm_gdf_utm[osm_gdf_utm["category"] == "healthcare"].drop_duplicates(subset=["osm_id"])
        critical_facilities_details = []
        facilities_intersecting = 0
        facilities_in_buffer = 0

        for _, fac in facilities.iterrows():
            dist_m = float(fac.geometry.distance(flood_union))
            orig_feat = fac["orig_feature"]
            coords = orig_feat["geometry"]["coordinates"]

            # Format coordinates cleanly [lon, lat]
            if isinstance(coords[0], list):
                # Polygon centroid coords
                c_lon, c_lat = Point(orig_feat["geometry"]["coordinates"][0][0]).x, Point(orig_feat["geometry"]["coordinates"][0][0]).y
            else:
                c_lon, c_lat = coords[0], coords[1]

            if dist_m <= 0.001:
                status = "DIRECTLY_INTERSECTING"
                dist_display = 0.0
                facilities_intersecting += 1
            elif dist_m <= buffer_threshold_meters:
                status = "BUFFER_ZONE_30M"
                dist_display = round(dist_m, 1)
                facilities_in_buffer += 1
            else:
                status = "SAFE_ELEVATED"
                dist_display = round(dist_m, 1)

            critical_facilities_details.append({
                "osm_id": fac["osm_id"],
                "name": fac["name"],
                "facility_type": fac["properties"].get("healthcare") or fac["properties"].get("amenity", "health_facility"),
                "coordinates": [round(c_lon, 5), round(c_lat, 5)],
                "exposure_status": status,
                "distance_to_flood_m": dist_display,
                "beds": fac["properties"].get("beds", "N/A"),
                "emergency": fac["properties"].get("emergency", "N/A")
            })

        # Category E: Settlements
        settlements = osm_gdf_utm[osm_gdf_utm["category"] == "settlement"].drop_duplicates(subset=["osm_id"])
        inter_settlements = settlements[settlements.intersects(flood_union)]

        # 6. Generate Exposed Features GeoJSON for Map Layer
        exposed_features = []

        # Add exposed buildings
        for _, b in inter_buildings.iterrows():
            f_orig = b["orig_feature"]
            feat_out = json.loads(json.dumps(f_orig))
            feat_out["properties"]["exposure_type"] = "building"
            feat_out["properties"]["potentially_exposed"] = True
            exposed_features.append(feat_out)

        # Add exposed roads (preserve original geometry, tagged with exposed status)
        for _, r in inter_roads.iterrows():
            f_orig = r["orig_feature"]
            feat_out = json.loads(json.dumps(f_orig))
            feat_out["properties"]["exposure_type"] = "road"
            feat_out["properties"]["potentially_exposed"] = True
            exposed_features.append(feat_out)

        # Add exposed bridges
        for _, br in inter_bridges.iterrows():
            f_orig = br["orig_feature"]
            feat_out = json.loads(json.dumps(f_orig))
            feat_out["properties"]["exposure_type"] = "bridge"
            feat_out["properties"]["potentially_exposed"] = True
            exposed_features.append(feat_out)

        # Add all critical facilities with their computed distance & exposure status
        for fac_dict in critical_facilities_details:
            exposed_features.append({
                "type": "Feature",
                "id": f"healthcare/{fac_dict['osm_id']}",
                "properties": {
                    "osm_id": fac_dict["osm_id"],
                    "category": "healthcare",
                    "name": fac_dict["name"],
                    "facility_type": fac_dict["facility_type"],
                    "exposure_status": fac_dict["exposure_status"],
                    "distance_to_flood_m": fac_dict["distance_to_flood_m"],
                    "potentially_exposed": fac_dict["exposure_status"] != "SAFE_ELEVATED"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": fac_dict["coordinates"]
                }
            })

        exposed_geojson = {
            "type": "FeatureCollection",
            "name": f"Exposed_Infrastructure_{clean_id}",
            "crs": {"type": "name", "properties": {"name": GEOGRAPHIC_CRS}},
            "metadata": {
                "analysis_id": clean_id,
                "osm_snapshot_date": self.osm_client.default_snapshot_date,
                "attribution": OSM_ATTRIBUTION,
                "provenance": used_provenance,
                "feature_count_exposed": len(exposed_features)
            },
            "features": exposed_features
        }

        # 7. Compile Final Summary Document
        timestamp_now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        summary = {
            "analysis_id": clean_id,
            "created_at": timestamp_now,
            "status": "COMPLETED",
            "provenance": used_provenance,
            "is_synthetic": (used_provenance == "SYNTHETIC_TEST_FIXTURE"),
            "data_notice": (
                "DEMONSTRATION SYNTHETIC FIXTURE — NOT CONFIRMED REAL EXPOSURE"
                if used_provenance == "SYNTHETIC_TEST_FIXTURE"
                else (
                    "CURRENT DATA PREVIEW — NOT PRE-EVENT HISTORICAL SNAPSHOT"
                    if used_provenance == "CURRENT_OSM_PREVIEW"
                    else "REAL SATELLITE & HISTORICAL OSM EXPOSURE ANALYSIS"
                )
            ),
            "osm_source": osm_source,
            "osm_snapshot_date": self.osm_client.default_snapshot_date,
            "osm_attribution": OSM_ATTRIBUTION,
            "aoi_bbox": aoi_bbox,
            "total_infrastructure_assessed": total_assessed,
            "valid_geometry_count": valid_cnt + repaired_cnt,
            "invalid_geometry_count": dropped_cnt,
            "exposed_buildings_count": exposed_buildings_count,
            "exposed_building_area_sqm": exposed_building_area_sqm,
            "exposed_building_area_sqkm": exposed_building_area_sqkm,
            "exposed_road_length_km": exposed_road_length_km,
            "exposed_bridges_count": exposed_bridges_count,
            "critical_facilities_assessed": len(facilities),
            "critical_facilities_intersecting": facilities_intersecting,
            "critical_facilities_in_buffer": facilities_in_buffer,
            "critical_facilities_details": critical_facilities_details,
            "settlements_intersecting_count": int(len(inter_settlements)),
            "blocker_reason": blocker_reason,
            "output_files": {
                "summary_json": f"infrastructure_exposure.json",
                "exposed_geojson": f"exposed_infrastructure.geojson",
                "baseline_geojson": f"baseline_infrastructure.geojson"
            },
            "limitations_and_uncertainties": [
                "Spatial intersection indicates potentially exposed infrastructure, NOT confirmed destroyed or structurally failed infrastructure.",
                "OSM building footprints and heights may be incomplete in remote upper tributary terraces of Nuwakot District.",
                "Road network centerline approximations do not account for embankment elevation above high-water mark.",
                "Topographic radar shadow and steep Himalayan canyon slopes introduce SAR water mask uncertainties."
            ]
        }

        # 8. Persist Artifacts to Analysis Output Directory
        summary_path = analysis_dir / "infrastructure_exposure.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        exposed_path = analysis_dir / "exposed_infrastructure.geojson"
        with open(exposed_path, "w", encoding="utf-8") as f:
            json.dump(exposed_geojson, f, indent=2)

        baseline_path = analysis_dir / "baseline_infrastructure.geojson"
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump(osm_data, f, indent=2)

        return summary


# Global singleton instances
osm_client = OSMInfrastructureClient()
infrastructure_engine = InfrastructureExposureEngine(osm_client=osm_client)
