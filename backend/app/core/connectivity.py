"""
Settlement Road Disconnection & Isolation Analysis Module
FloodLens AI - Phase 5: Trishuli River Corridor, Nepal

Models topological road-network connectivity between mountain settlements and regional lifeline hubs.
Simulates candidate post-flood road and bridge closures using validated Sentinel-1 flood extents.

Core capabilities:
1. Projected metric graph construction (EPSG:32645 UTM Zone 45N) using NetworkX.
2. At-grade intersection splitting with vertical elevation / layer separation (bridges/tunnels).
3. Documented snapping tolerance for nodes and settlements to prevent false connections.
4. Documented, modeled travel-speed assumptions per road functional classification.
5. Baseline vs post-flood shortest path routing (Dijkstra) and detour metrics.
6. Rigorous settlement classification: NEWLY_DISCONNECTED, ALREADY_DISCONNECTED, DETOURED, UNCHANGED, SNAP_FAILED, UNAVAILABLE.
7. Strict data provenance propagation (SYNTHETIC_TEST_FIXTURE vs REAL_DATA_ANALYSIS).
8. Clear uncertainty notices: simulated closures, not confirmed structural damage.
"""

import math
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path
import networkx as nx
import shapely
import shapely.geometry
from shapely.geometry import Point, LineString, MultiLineString, Polygon, MultiPolygon, shape, mapping
from shapely.validation import make_valid
import pyproj

from app.config import settings, OUTPUTS_DIR
from app.core.infrastructure import (
    validate_analysis_id,
    InfrastructureError,
    MissingFloodAnalysisError,
    HistoricalSnapshotUnavailableError,
    PROJECTED_CRS_NEPAL,
    GEOGRAPHIC_CRS,
    OSM_ATTRIBUTION,
    osm_client
)

logger = logging.getLogger("floodlens.connectivity")

# --- DOCUMENTED SPEED ASSUMPTIONS (km/h) ---
# Modeled estimates based on Nepal rural/mountain road design standards (DoR Nepal / IRC guidelines).
# These are explicit assumptions for relative travel-time estimation, NOT real-time sensor measurements.
ASSUMED_HIGHWAY_SPEEDS_KMH: Dict[str, float] = {
    "motorway": 60.0,
    "trunk": 50.0,
    "primary": 50.0,       # Trishuli Highway (H02) designed corridor speed
    "secondary": 40.0,     # Feeder & inter-district paved roads
    "tertiary": 30.0,      # Valley links and agricultural connection roads
    "residential": 25.0,   # Village and municipal access roads
    "unclassified": 25.0,  # Rural access links
    "service": 20.0,       # Infrastructure facility & intake service roads
    "track": 15.0,         # Earthen agricultural & riverbed tracks
    "footway": 5.0,        # Suspension footbridges & walking paths
    "path": 5.0,           # Mountain trails
    "pedestrian": 5.0,
    "default": 30.0        # Fallback speed when classification is unknown
}

# --- DEFAULT CANDIDATE HUBS & COMMUNITIES ---
DEFAULT_REGIONAL_HUBS: List[str] = [
    "Bidur",            # District Administrative Center & Relief Depot
    "Trishuli Bazaar"   # Upper Valley Commercial & Referral Hub
]

CANDIDATE_COMMUNITIES_TO_CHECK: List[str] = [
    "Devighat",
    "Battar",
    "Tupche",
    "Salme"             # Remote mountain settlement (must report unavailable if missing from source)
]


class ConnectivityError(InfrastructureError):
    """Base exception for road connectivity and isolation analysis errors."""
    pass


class MissingConnectivityInputError(ConnectivityError):
    """Raised when flood extents or infrastructure inputs are missing."""
    pass


class CoordinateTransformer:
    """Helper for converting between geographic (EPSG:4326) and projected metric (EPSG:32645) coordinates."""

    def __init__(self, from_crs: str = GEOGRAPHIC_CRS, to_crs: str = PROJECTED_CRS_NEPAL):
        self.to_utm = pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform
        self.to_wgs = pyproj.Transformer.from_crs(to_crs, from_crs, always_xy=True).transform

    def transform_point_to_utm(self, lon: float, lat: float) -> Tuple[float, float]:
        x, y = self.to_utm(lon, lat)
        return float(x), float(y)

    def transform_point_to_wgs(self, x: float, y: float) -> Tuple[float, float]:
        lon, lat = self.to_wgs(x, y)
        return float(lon), float(lat)

    def transform_linestring_to_utm(self, line_wgs: LineString) -> LineString:
        coords_utm = [self.transform_point_to_utm(c[0], c[1]) for c in line_wgs.coords]
        return LineString(coords_utm)

    def transform_linestring_to_wgs(self, line_utm: LineString) -> LineString:
        coords_wgs = [self.transform_point_to_wgs(c[0], c[1]) for c in line_utm.coords]
        return LineString(coords_wgs)


# Singleton transformer
transformer = CoordinateTransformer()


class RoadNetworkGraphBuilder:
    """
    Builds a topologically consistent metric graph from road and bridge geometries.
    Splits road segments at genuine intersections while respecting vertical layer/elevation separation.
    """

    def __init__(
        self,
        snapping_tolerance_m: float = 50.0,
        assumed_speeds: Optional[Dict[str, float]] = None
    ):
        self.snapping_tolerance_m = snapping_tolerance_m
        self.assumed_speeds = assumed_speeds or ASSUMED_HIGHWAY_SPEEDS_KMH

    def parse_vertical_layer(self, properties: Dict[str, Any]) -> int:
        """
        Parses vertical layer for elevation separation.
        Returns integer layer (0 = at-grade, 1 = bridge/overpass, -1 = tunnel/underpass).
        """
        layer_val = properties.get("layer")
        if layer_val is not None:
            try:
                return int(str(layer_val).strip())
            except ValueError:
                pass
        if properties.get("bridge") == "yes":
            return 1
        if properties.get("tunnel") == "yes":
            return -1
        return 0

    def extract_speed_kmh(self, properties: Dict[str, Any]) -> Tuple[float, str]:
        """
        Calculates travel speed based on maxspeed tag or documented functional class assumption.
        Returns (speed_kmh, speed_basis).
        """
        maxspeed_str = properties.get("maxspeed")
        if maxspeed_str:
            try:
                # Handle formats like "50", "50 km/h", "50mph"
                clean_num = str(maxspeed_str).lower().replace("km/h", "").replace("kph", "").strip()
                val = float(clean_num.split()[0])
                if 5.0 <= val <= 130.0:
                    return val, "OSM_MAXSPEED_TAG"
            except Exception:
                pass

        highway_type = str(properties.get("highway", "default")).lower().strip()
        speed = self.assumed_speeds.get(highway_type, self.assumed_speeds.get("default", 30.0))
        return speed, "ASSUMED_ROAD_CLASS_SPEED"

    def build_graph(
        self,
        features: List[Dict[str, Any]]
    ) -> Tuple[nx.Graph, Dict[str, Any]]:
        """
        Constructs an undirected metric road graph.
        Returns: (G, graph_stats_dict)
        """
        G = nx.Graph()
        stats = {
            "total_features_evaluated": len(features),
            "roads_and_bridges_processed": 0,
            "invalid_geometries_count": 0,
            "roads_omitted_count": 0,
            "split_segments_created": 0,
            "total_road_length_km": 0.0,
            "nodes_count": 0,
            "edges_count": 0,
            "connected_components_count": 0,
            "snapping_tolerance_m": self.snapping_tolerance_m,
            "elevation_separation_applied": True,
            "speed_assumptions_applied": dict(self.assumed_speeds)
        }

        # 1. Filter, validate, and reproject road/bridge geometries to UTM Zone 45N
        valid_lines: List[Dict[str, Any]] = []
        lines_by_layer: Dict[int, List[Dict[str, Any]]] = {}

        for f in features:
            props = dict(f.get("properties", {}))
            cat = str(props.get("category", "")).lower()
            hway = props.get("highway")

            if cat not in ("road", "bridge") and not hway:
                continue

            geom_dict = f.get("geometry")
            if not geom_dict:
                stats["invalid_geometries_count"] += 1
                stats["roads_omitted_count"] += 1
                continue

            try:
                geom = shape(geom_dict)
                if geom.is_empty:
                    stats["invalid_geometries_count"] += 1
                    stats["roads_omitted_count"] += 1
                    continue
                if not geom.is_valid:
                    geom = make_valid(geom)
                    if geom.is_empty:
                        stats["invalid_geometries_count"] += 1
                        stats["roads_omitted_count"] += 1
                        continue

                # Expand MultiLineString into LineStrings
                line_geoms: List[LineString] = []
                if geom.geom_type == "LineString":
                    line_geoms.append(geom)
                elif geom.geom_type == "MultiLineString":
                    line_geoms.extend(list(geom.geoms))
                else:
                    stats["invalid_geometries_count"] += 1
                    stats["roads_omitted_count"] += 1
                    continue

                layer = self.parse_vertical_layer(props)
                props["parsed_layer"] = layer
                speed_kmh, speed_basis = self.extract_speed_kmh(props)
                props["speed_kmh"] = speed_kmh
                props["speed_basis"] = speed_basis

                for lg in line_geoms:
                    if len(lg.coords) < 2:
                        continue
                    # Reproject to metric UTM Zone 45N
                    utm_line = transformer.transform_linestring_to_utm(lg)
                    if utm_line.length < 0.1:
                        continue

                    item = {
                        "properties": props,
                        "utm_geometry": utm_line,
                        "wgs_geometry": lg,
                        "layer": layer
                    }
                    valid_lines.append(item)
                    lines_by_layer.setdefault(layer, []).append(item)
                    stats["roads_and_bridges_processed"] += 1
            except Exception as e:
                logger.warning(f"Error processing road feature {props.get('osm_id')}: {e}")
                stats["invalid_geometries_count"] += 1
                stats["roads_omitted_count"] += 1

        # 2. Split lines at genuine intersections within the SAME vertical layer
        # When two lines on the same layer cross, they are split at the intersection point.
        # Lines on DIFFERENT layers (e.g., bridge with layer=1 crossing road with layer=0) do NOT split each other!
        split_segments: List[Dict[str, Any]] = []

        for layer, layer_items in lines_by_layer.items():
            for i, item_i in enumerate(layer_items):
                line_i = item_i["utm_geometry"]
                props_i = item_i["properties"]
                cuts = [0.0, line_i.length]

                for j, item_j in enumerate(layer_items):
                    if i == j:
                        continue
                    line_j = item_j["utm_geometry"]
                    if line_i.intersects(line_j):
                        inter = line_i.intersection(line_j)
                        pts: List[Point] = []
                        if inter.geom_type == "Point":
                            pts = [inter]
                        elif inter.geom_type == "MultiPoint":
                            pts = list(inter.geoms)
                        elif inter.geom_type in ("LineString", "MultiLineString"):
                            # Overlap endpoints
                            if inter.geom_type == "LineString":
                                pts = [Point(inter.coords[0]), Point(inter.coords[-1])]
                            else:
                                for g in inter.geoms:
                                    pts.extend([Point(g.coords[0]), Point(g.coords[-1])])

                        for pt in pts:
                            dist = float(line_i.project(pt))
                            if 0.5 < dist < (line_i.length - 0.5):
                                cuts.append(dist)

                cuts = sorted(set(cuts))
                if len(cuts) <= 2:
                    split_segments.append(item_i)
                else:
                    for k in range(len(cuts) - 1):
                        d0, d1 = cuts[k], cuts[k + 1]
                        if d1 - d0 < 0.5:
                            continue
                        p0 = line_i.interpolate(d0)
                        p1 = line_i.interpolate(d1)
                        sub_coords = [p0.coords[0]]
                        for c in line_i.coords:
                            pt_c = Point(c)
                            d_c = line_i.project(pt_c)
                            if d0 + 0.1 < d_c < d1 - 0.1:
                                sub_coords.append(c)
                        sub_coords.append(p1.coords[0])
                        sub_line = LineString(sub_coords)
                        if sub_line.length < 0.5:
                            continue

                        split_segments.append({
                            "properties": props_i,
                            "utm_geometry": sub_line,
                            "wgs_geometry": transformer.transform_linestring_to_wgs(sub_line),
                            "layer": layer
                        })

        stats["split_segments_created"] = len(split_segments)

        # 3. Node Registry and Snapping
        # To avoid false connections while connecting legitimate intersections and bridge ramps:
        # A node is identified by (x, y) coordinates and snapped within snapping_tolerance_m.
        # Notice: At bridge endpoints, vehicles transition between bridge and road, so bridge endpoints
        # snap to connecting road endpoints within snapping_tolerance_m!
        node_records: List[Dict[str, Any]] = []

        def get_or_register_node(x: float, y: float, layer: int, is_endpoint: bool = True) -> str:
            # Check existing nodes
            best_node_id: Optional[str] = None
            min_dist = float("inf")

            for n in node_records:
                dist = math.hypot(x - n["x"], y - n["y"])
                if dist <= self.snapping_tolerance_m:
                    # If same layer or bridge/ramp endpoint connection, can snap
                    if n["layer"] == layer or is_endpoint:
                        if dist < min_dist:
                            min_dist = dist
                            best_node_id = n["node_id"]

            if best_node_id is not None:
                return best_node_id

            node_id = f"node_{len(node_records) + 1}"
            lon, lat = transformer.transform_point_to_wgs(x, y)
            node_data = {
                "node_id": node_id,
                "x": float(x),
                "y": float(y),
                "lon": round(float(lon), 6),
                "lat": round(float(lat), 6),
                "layer": layer
            }
            node_records.append(node_data)
            G.add_node(
                node_id,
                x=node_data["x"],
                y=node_data["y"],
                lon=node_data["lon"],
                lat=node_data["lat"],
                layer=layer
            )
            return node_id

        # 4. Populate edges in Graph
        total_len_km = 0.0
        edge_index = 0

        for seg in split_segments:
            props = seg["properties"]
            utm_geom = seg["utm_geometry"]
            wgs_geom = seg["wgs_geometry"]
            layer = seg["layer"]

            start_xy = utm_geom.coords[0]
            end_xy = utm_geom.coords[-1]

            u = get_or_register_node(start_xy[0], start_xy[1], layer, is_endpoint=True)
            v = get_or_register_node(end_xy[0], end_xy[1], layer, is_endpoint=True)

            if u == v:
                continue

            length_m = float(utm_geom.length)
            length_km = round(length_m / 1000.0, 4)
            total_len_km += length_km

            speed_kmh = float(props.get("speed_kmh", 30.0))
            speed_basis = str(props.get("speed_basis", "ASSUMED_ROAD_CLASS_SPEED"))

            travel_time_hours = length_km / max(speed_kmh, 1.0)
            travel_time_seconds = round(travel_time_hours * 3600.0, 2)
            travel_time_minutes = round(travel_time_seconds / 60.0, 2)

            edge_index += 1
            osm_id = props.get("osm_id")
            edge_id = f"{osm_id}_{edge_index}" if osm_id else f"edge_{edge_index}"

            # Coords in EPSG:4326 for Leaflet map display
            coords_wgs84 = [[round(c[0], 6), round(c[1], 6)] for c in wgs_geom.coords]

            # In case parallel edge exists, choose shorter length or lowest travel time
            if G.has_edge(u, v):
                existing_data = G.get_edge_data(u, v)
                if existing_data and existing_data.get("length_m", float("inf")) <= length_m:
                    continue

            G.add_edge(
                u,
                v,
                edge_id=edge_id,
                osm_id=osm_id,
                name=props.get("name", "Unnamed Road"),
                category=props.get("category", "road"),
                highway=props.get("highway", "unclassified"),
                bridge=props.get("bridge"),
                tunnel=props.get("tunnel"),
                layer=layer,
                surface=props.get("surface", "unknown"),
                length_m=round(length_m, 2),
                length_km=length_km,
                speed_kmh=speed_kmh,
                speed_basis=speed_basis,
                travel_time_seconds=travel_time_seconds,
                travel_time_minutes=travel_time_minutes,
                utm_geometry=utm_geom,
                wgs_geometry=wgs_geom,
                coords_wgs84=coords_wgs84
            )

        stats["total_road_length_km"] = round(total_len_km, 3)
        stats["nodes_count"] = G.number_of_nodes()
        stats["edges_count"] = G.number_of_edges()
        stats["connected_components_count"] = nx.number_connected_components(G) if G.number_of_nodes() > 0 else 0

        return G, stats


class SettlementConnectivityEngine:
    """
    Evaluates baseline accessibility and simulates post-flood road disconnection and detours.
    """

    def __init__(
        self,
        graph_builder: Optional[RoadNetworkGraphBuilder] = None,
        max_settlement_snap_distance_m: float = 1000.0
    ):
        self.graph_builder = graph_builder or RoadNetworkGraphBuilder()
        self.max_settlement_snap_distance_m = max_settlement_snap_distance_m

    def snap_point_to_graph(
        self,
        G: nx.Graph,
        lon: float,
        lat: float,
        point_name: str
    ) -> Dict[str, Any]:
        """
        Snaps a coordinate to the nearest valid road-network node in EPSG:32645.
        Enforces maximum snapping distance and reports failed snaps.
        """
        if G.number_of_nodes() == 0:
            return {
                "name": point_name,
                "status": "SNAP_FAILED",
                "nearest_node": None,
                "distance_m": None,
                "coordinates": [lon, lat],
                "reason": "Road network graph has zero nodes"
            }

        px, py = transformer.transform_point_to_utm(lon, lat)
        best_node: Optional[str] = None
        min_dist = float("inf")

        for node_id, data in G.nodes(data=True):
            nx_c = data.get("x")
            ny_c = data.get("y")
            if nx_c is not None and ny_c is not None:
                dist = math.hypot(px - nx_c, py - ny_c)
                if dist < min_dist:
                    min_dist = dist
                    best_node = node_id

        if min_dist <= self.max_settlement_snap_distance_m and best_node is not None:
            return {
                "name": point_name,
                "status": "SNAPPED",
                "nearest_node": best_node,
                "distance_m": round(min_dist, 2),
                "coordinates": [lon, lat],
                "snapped_coordinates": [G.nodes[best_node]["lon"], G.nodes[best_node]["lat"]]
            }
        else:
            return {
                "name": point_name,
                "status": "SNAP_FAILED",
                "nearest_node": best_node,
                "distance_m": round(min_dist, 2) if min_dist != float("inf") else None,
                "coordinates": [lon, lat],
                "reason": f"Nearest road node is {round(min_dist, 1)}m away, exceeding max snapping threshold ({self.max_settlement_snap_distance_m}m)"
            }

    def extract_features_by_name(
        self,
        features: List[Dict[str, Any]],
        target_names: List[str],
        category: str = "settlement"
    ) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
        """
        Locates target settlement or hub features by name in source dataset.
        Returns: (matched_dict, missing_names_list)
        """
        matched = {}
        missing = []
        name_map = {}

        for f in features:
            props = f.get("properties", {})
            name = props.get("name")
            if name:
                name_map[name.strip().lower()] = f
                # Also index Nepali or alternative names
                name_ne = props.get("name:ne")
                if name_ne:
                    name_map[name_ne.strip().lower()] = f

        for t in target_names:
            t_key = t.strip().lower()
            if t_key in name_map:
                matched[t] = name_map[t_key]
            else:
                missing.append(t)

        return matched, missing

    def find_shortest_route(
        self,
        G: nx.Graph,
        source_node: str,
        target_node: str,
        weight: str = "length_m"
    ) -> Optional[Dict[str, Any]]:
        """
        Calculates shortest path using Dijkstra algorithm.
        Returns path details or None if no path exists.
        """
        if not G.has_node(source_node) or not G.has_node(target_node):
            return None

        if not nx.has_path(G, source_node, target_node):
            return None

        try:
            path_nodes = nx.shortest_path(G, source=source_node, target=target_node, weight=weight)
            total_dist_m = 0.0
            total_tt_sec = 0.0
            route_edge_ids: List[str] = []
            route_osm_ids: List[Any] = []
            route_coords: List[List[float]] = []

            for i in range(len(path_nodes) - 1):
                u = path_nodes[i]
                v = path_nodes[i + 1]
                edge_data = G.get_edge_data(u, v)
                if not edge_data:
                    continue

                total_dist_m += float(edge_data.get("length_m", 0.0))
                total_tt_sec += float(edge_data.get("travel_time_seconds", 0.0))
                route_edge_ids.append(edge_data.get("edge_id", ""))
                route_osm_ids.append(edge_data.get("osm_id"))

                coords = edge_data.get("coords_wgs84", [])
                if coords:
                    # Orient coords along path direction
                    u_data = G.nodes[u]
                    c_start = coords[0]
                    # Check if reversed
                    if math.hypot(c_start[0] - u_data["lon"], c_start[1] - u_data["lat"]) > 0.001:
                        coords = list(reversed(coords))
                    for pt in coords:
                        if not route_coords or route_coords[-1] != pt:
                            route_coords.append(pt)

            return {
                "connected": True,
                "distance_m": round(total_dist_m, 2),
                "distance_km": round(total_dist_m / 1000.0, 3),
                "travel_time_seconds": round(total_tt_sec, 2),
                "travel_time_minutes": round(total_tt_sec / 60.0, 2),
                "path_nodes": path_nodes,
                "route_edge_ids": route_edge_ids,
                "route_osm_ids": list(set(route_osm_ids)),
                "route_coordinates": route_coords
            }
        except nx.NetworkXNoPath:
            return None
        except Exception as e:
            logger.warning(f"Shortest path calculation failed between {source_node} and {target_node}: {e}")
            return None

    def identify_closed_edges(
        self,
        G: nx.Graph,
        flood_polygons_utm: List[Any],
        closure_method: str = "complete_severance"
    ) -> List[Dict[str, Any]]:
        """
        Identifies road and bridge edges intersecting candidate flood polygons in EPSG:32645.
        Returns list of closed edge detail dictionaries.
        """
        closed_edges = []
        if not flood_polygons_utm:
            return closed_edges

        # Union flood polygons for efficient spatial intersection
        flood_union = shapely.unary_union(flood_polygons_utm) if len(flood_polygons_utm) > 1 else flood_polygons_utm[0]

        for u, v, data in G.edges(data=True):
            utm_geom = data.get("utm_geometry")
            if not utm_geom:
                continue

            is_bridge = (data.get("bridge") == "yes" or data.get("category") == "bridge")

            if closure_method == "bridge_severance_only" and not is_bridge:
                continue

            if utm_geom.intersects(flood_union):
                inter = utm_geom.intersection(flood_union)
                closed_edges.append({
                    "u": u,
                    "v": v,
                    "edge_id": data.get("edge_id"),
                    "osm_id": data.get("osm_id"),
                    "name": data.get("name"),
                    "category": data.get("category"),
                    "highway": data.get("highway"),
                    "bridge": data.get("bridge"),
                    "is_bridge": is_bridge,
                    "length_km": data.get("length_km"),
                    "coords_wgs84": data.get("coords_wgs84", []),
                    "intersection_length_m": round(float(inter.length), 2) if hasattr(inter, "length") else 0.0
                })

        return closed_edges

    def execute_connectivity_assessment(
        self,
        analysis_id: str,
        hubs: Optional[List[str]] = None,
        candidate_communities: Optional[List[str]] = None,
        closure_method: str = "complete_severance",
        snapping_tolerance_m: float = 50.0,
        max_settlement_snap_distance_m: float = 1000.0,
        osm_source: str = "historical",
        allow_fallback_fixture: bool = True
    ) -> Dict[str, Any]:
        """
        Orchestrates full baseline and post-flood connectivity assessment for an analysis ID.
        """
        clean_id = validate_analysis_id(analysis_id)
        analysis_dir = OUTPUTS_DIR / clean_id

        if not analysis_dir.exists():
            raise MissingConnectivityInputError(f"Analysis directory '{clean_id}' does not exist.")

        metadata_path = analysis_dir / "analysis_metadata.json"
        flood_geojson_path = analysis_dir / "flood_candidate_mask.geojson"

        if not metadata_path.exists():
            raise MissingConnectivityInputError(f"Missing analysis_metadata.json in analysis '{clean_id}'.")
        if not flood_geojson_path.exists() or flood_geojson_path.stat().st_size == 0:
            raise MissingConnectivityInputError(f"Missing flood_candidate_mask.geojson in analysis '{clean_id}'.")

        # Load flood metadata and GeoJSON
        with open(metadata_path, "r", encoding="utf-8") as f:
            flood_meta = json.load(f)

        with open(flood_geojson_path, "r", encoding="utf-8") as f:
            flood_geojson = json.load(f)

        flood_features = flood_geojson.get("features", [])
        if not flood_features:
            raise MissingConnectivityInputError(f"Flood analysis '{clean_id}' contains 0 candidate flood polygons.")

        # Check flood provenance
        is_flood_synthetic = bool(
            flood_meta.get("is_demo_fixture", False) or
            flood_meta.get("processing_mode") == "SYNTHETIC_TEST_FIXTURE" or
            "DEMO" in str(flood_meta.get("analysis_id", "")).upper()
        )

        aoi_bbox = flood_meta.get("area_of_interest", {}).get("bbox", settings.DEFAULT_AOI_BBOX)

        # Retrieve infrastructure dataset
        infrastructure_provenance = "VERIFIED_HISTORICAL_OSM"
        osm_blocker_reason: Optional[str] = None
        try:
            if osm_source == "current_preview":
                osm_data = osm_client.fetch_current_preview(bbox=aoi_bbox)
                infrastructure_provenance = "CURRENT_OSM_PREVIEW"
            else:
                osm_data = osm_client.fetch_historical_infrastructure(
                    bbox=aoi_bbox,
                    snapshot_date=osm_client.default_snapshot_date,
                    allow_fallback_fixture=allow_fallback_fixture
                )
                if osm_data.get("metadata", {}).get("is_fallback_fixture"):
                    infrastructure_provenance = "SYNTHETIC_TEST_FIXTURE"
                    osm_blocker_reason = osm_data.get("metadata", {}).get("remote_blocker_reason")
        except HistoricalSnapshotUnavailableError as e:
            return {
                "analysis_id": clean_id,
                "status": "BLOCKED",
                "provenance": "UNAVAILABLE",
                "is_synthetic": False,
                "blocker_reason": str(e),
                "message": "Required pre-event historical OpenStreetMap snapshot is unreachable.",
                "settlements_assessed": 0,
                "newly_disconnected_count": None,
                "detoured_count": None,
                "connected_count": None,
                "limitations_and_uncertainties": [
                    "Historical snapshot (2026-07-27) blocked; current OSM data was not substituted to preserve baseline integrity."
                ]
            }

        # Overall provenance rule
        if is_flood_synthetic or infrastructure_provenance == "SYNTHETIC_TEST_FIXTURE":
            analysis_provenance = "SYNTHETIC_TEST_FIXTURE"
            is_synthetic_overall = True
        elif infrastructure_provenance == "CURRENT_OSM_PREVIEW":
            analysis_provenance = "CURRENT_OSM_PREVIEW"
            is_synthetic_overall = False
        else:
            analysis_provenance = "REAL_SATELLITE_DERIVED"
            is_synthetic_overall = False

        # Build baseline road-network graph
        self.graph_builder.snapping_tolerance_m = snapping_tolerance_m
        G_baseline, graph_stats = self.graph_builder.build_graph(osm_data.get("features", []))

        # Project flood polygons to UTM Zone 45N
        flood_polys_utm: List[Any] = []
        for feat in flood_features:
            g_dict = feat.get("geometry")
            if g_dict:
                try:
                    s_geom = shape(g_dict)
                    if not s_geom.is_empty and s_geom.is_valid:
                        # Reproject
                        if s_geom.geom_type == "Polygon":
                            coords_utm = [transformer.transform_point_to_utm(c[0], c[1]) for c in s_geom.exterior.coords]
                            holes_utm = [[transformer.transform_point_to_utm(c[0], c[1]) for c in hole.coords] for hole in s_geom.interiors]
                            flood_polys_utm.append(Polygon(coords_utm, holes_utm))
                        elif s_geom.geom_type == "MultiPolygon":
                            for poly in s_geom.geoms:
                                coords_utm = [transformer.transform_point_to_utm(c[0], c[1]) for c in poly.exterior.coords]
                                holes_utm = [[transformer.transform_point_to_utm(c[0], c[1]) for c in hole.coords] for hole in poly.interiors]
                                flood_polys_utm.append(Polygon(coords_utm, holes_utm))
                except Exception:
                    pass

        # Identify closed road edges
        closed_edge_records = self.identify_closed_edges(
            G=G_baseline,
            flood_polygons_utm=flood_polys_utm,
            closure_method=closure_method
        )

        # Build post-flood graph G_post
        G_post = G_baseline.copy()
        for ce in closed_edge_records:
            u, v = ce["u"], ce["v"]
            if G_post.has_edge(u, v):
                G_post.remove_edge(u, v)

        # Identify regional hubs
        target_hubs = hubs or DEFAULT_REGIONAL_HUBS
        all_features = osm_data.get("features", [])
        matched_hubs, missing_hubs = self.extract_features_by_name(all_features, target_hubs, category="settlement")

        snapped_hubs: Dict[str, Dict[str, Any]] = {}
        for hub_name in target_hubs:
            if hub_name in matched_hubs:
                f = matched_hubs[hub_name]
                geom = f.get("geometry", {})
                coords = geom.get("coordinates", [0, 0])
                snap_res = self.snap_point_to_graph(G_baseline, coords[0], coords[1], hub_name)
                snap_res["osm_id"] = f.get("properties", {}).get("osm_id")
                snapped_hubs[hub_name] = snap_res
            else:
                snapped_hubs[hub_name] = {
                    "name": hub_name,
                    "status": "UNAVAILABLE",
                    "reason": "Hub not found in retrieved infrastructure dataset",
                    "coordinates": None,
                    "nearest_node": None
                }

        # Identify candidate communities
        target_communities = candidate_communities or CANDIDATE_COMMUNITIES_TO_CHECK
        matched_communities, missing_communities = self.extract_features_by_name(all_features, target_communities, category="settlement")

        settlement_results: List[Dict[str, Any]] = []
        routes_geojson_features: List[Dict[str, Any]] = []

        newly_disconnected_count = 0
        already_disconnected_count = 0
        detoured_count = 0
        unchanged_count = 0
        unavailable_count = 0
        snap_failed_count = 0

        # Assess connectivity for each community
        for comm_name in target_communities:
            if comm_name not in matched_communities:
                unavailable_count += 1
                settlement_results.append({
                    "name": comm_name,
                    "status": "UNAVAILABLE",
                    "isolation_cause": "Settlement feature not found in retrieved OpenStreetMap baseline dataset",
                    "coordinates": None,
                    "nearest_hub": None,
                    "baseline_distance_km": None,
                    "baseline_travel_time_minutes": None,
                    "post_flood_distance_km": None,
                    "post_flood_travel_time_minutes": None,
                    "detour_distance_km": None,
                    "detour_travel_time_minutes": None,
                    "hub_connections": {}
                })
                continue

            comm_feat = matched_communities[comm_name]
            coords = comm_feat.get("geometry", {}).get("coordinates", [0, 0])
            comm_osm_id = comm_feat.get("properties", {}).get("osm_id")

            snap_comm = self.snap_point_to_graph(G_baseline, coords[0], coords[1], comm_name)
            if snap_comm["status"] != "SNAPPED":
                snap_failed_count += 1
                settlement_results.append({
                    "name": comm_name,
                    "osm_id": comm_osm_id,
                    "status": "SNAP_FAILED",
                    "isolation_cause": snap_comm.get("reason", "Settlement too far from network nodes"),
                    "coordinates": coords,
                    "nearest_hub": None,
                    "snapped_distance_m": snap_comm.get("distance_m"),
                    "baseline_distance_km": None,
                    "baseline_travel_time_minutes": None,
                    "post_flood_distance_km": None,
                    "post_flood_travel_time_minutes": None,
                    "detour_distance_km": None,
                    "detour_travel_time_minutes": None,
                    "hub_connections": {}
                })
                continue

            comm_node = snap_comm["nearest_node"]

            # Evaluate route to every snapped hub
            hub_connections: Dict[str, Any] = {}
            best_baseline_hub: Optional[str] = None
            min_baseline_dist = float("inf")

            for h_name, h_info in snapped_hubs.items():
                if h_info.get("status") != "SNAPPED":
                    hub_connections[h_name] = {
                        "status": "HUB_UNAVAILABLE",
                        "baseline_route": None,
                        "post_flood_route": None
                    }
                    continue

                h_node = h_info["nearest_node"]

                # Baseline route
                base_route = self.find_shortest_route(G_baseline, comm_node, h_node)
                post_route = self.find_shortest_route(G_post, comm_node, h_node)

                hub_connections[h_name] = {
                    "baseline_connected": base_route is not None,
                    "baseline_distance_km": base_route["distance_km"] if base_route else None,
                    "baseline_travel_time_minutes": base_route["travel_time_minutes"] if base_route else None,
                    "post_connected": post_route is not None,
                    "post_distance_km": post_route["distance_km"] if post_route else None,
                    "post_travel_time_minutes": post_route["travel_time_minutes"] if post_route else None,
                    "detour_distance_km": round(post_route["distance_km"] - base_route["distance_km"], 3) if (base_route and post_route) else None,
                    "detour_travel_time_minutes": round(post_route["travel_time_minutes"] - base_route["travel_time_minutes"], 2) if (base_route and post_route) else None,
                }

                if base_route and base_route["distance_km"] < min_baseline_dist:
                    min_baseline_dist = base_route["distance_km"]
                    best_baseline_hub = h_name

            # Determine primary status relative to the nearest reachable baseline hub
            primary_hub = best_baseline_hub or (list(snapped_hubs.keys())[0] if snapped_hubs else None)
            hub_conn = hub_connections.get(primary_hub, {}) if primary_hub else {}

            baseline_conn = hub_conn.get("baseline_connected", False)
            post_conn = hub_conn.get("post_connected", False)

            if not baseline_conn:
                status_cat = "ALREADY_DISCONNECTED"
                already_disconnected_count += 1
                cause_text = "Disconnected at pre-event baseline (isolated network component prior to flood)"
            elif not post_conn:
                status_cat = "NEWLY_DISCONNECTED"
                newly_disconnected_count += 1
                cause_text = f"Simulated road/bridge closure severed all traversable routes to {primary_hub}"
            else:
                detour_km = hub_conn.get("detour_distance_km", 0.0) or 0.0
                if detour_km > 0.05:
                    status_cat = "DETOURED"
                    detoured_count += 1
                    cause_text = f"Alternative road route utilized with +{detour_km:.2f} km detour"
                else:
                    status_cat = "UNCHANGED"
                    unchanged_count += 1
                    cause_text = f"Primary road route to {primary_hub} unaffected by flood closures"

            settlement_results.append({
                "name": comm_name,
                "osm_id": comm_osm_id,
                "status": status_cat,
                "isolation_cause": cause_text,
                "coordinates": coords,
                "nearest_hub": primary_hub,
                "snapped_distance_m": snap_comm.get("distance_m"),
                "baseline_distance_km": hub_conn.get("baseline_distance_km"),
                "baseline_travel_time_minutes": hub_conn.get("baseline_travel_time_minutes"),
                "post_flood_distance_km": hub_conn.get("post_distance_km"),
                "post_flood_travel_time_minutes": hub_conn.get("post_travel_time_minutes"),
                "detour_distance_km": hub_conn.get("detour_distance_km"),
                "detour_travel_time_minutes": hub_conn.get("detour_travel_time_minutes"),
                "hub_connections": hub_connections
            })

            # Add routes to GeoJSON for primary hub
            if primary_hub and primary_hub in snapped_hubs and snapped_hubs[primary_hub].get("nearest_node"):
                h_node = snapped_hubs[primary_hub]["nearest_node"]
                b_route = self.find_shortest_route(G_baseline, comm_node, h_node)
                p_route = self.find_shortest_route(G_post, comm_node, h_node)

                if b_route and b_route.get("route_coordinates"):
                    routes_geojson_features.append({
                        "type": "Feature",
                        "id": f"baseline_route_{comm_name}_{primary_hub}",
                        "properties": {
                            "type": "baseline_route",
                            "settlement": comm_name,
                            "hub": primary_hub,
                            "distance_km": b_route["distance_km"],
                            "travel_time_minutes": b_route["travel_time_minutes"],
                            "edge_ids": b_route["route_edge_ids"]
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": b_route["route_coordinates"]
                        }
                    })

                if p_route and p_route.get("route_coordinates"):
                    routes_geojson_features.append({
                        "type": "Feature",
                        "id": f"post_route_{comm_name}_{primary_hub}",
                        "properties": {
                            "type": "post_flood_route",
                            "settlement": comm_name,
                            "hub": primary_hub,
                            "distance_km": p_route["distance_km"],
                            "travel_time_minutes": p_route["travel_time_minutes"],
                            "is_detour": status_cat == "DETOURED"
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": p_route["route_coordinates"]
                        }
                    })

        # Add closed edges to routes GeoJSON
        for ce in closed_edge_records:
            routes_geojson_features.append({
                "type": "Feature",
                "id": f"closed_{ce['edge_id']}",
                "properties": {
                    "type": "simulated_closed_edge",
                    "edge_id": ce["edge_id"],
                    "osm_id": ce["osm_id"],
                    "name": ce["name"],
                    "category": ce["category"],
                    "highway": ce["highway"],
                    "bridge": ce["bridge"],
                    "is_bridge": ce["is_bridge"],
                    "length_km": ce["length_km"],
                    "closure_reason": "Spatial intersection with SAR candidate flood polygon"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": ce["coords_wgs84"]
                }
            })

        # Add settlement point markers to GeoJSON
        for s in settlement_results:
            if s.get("coordinates"):
                routes_geojson_features.append({
                    "type": "Feature",
                    "id": f"settlement_{s['name']}",
                    "properties": {
                        "type": "settlement_marker",
                        "name": s["name"],
                        "osm_id": s.get("osm_id"),
                        "status": s["status"],
                        "isolation_cause": s["isolation_cause"],
                        "nearest_hub": s["nearest_hub"],
                        "baseline_distance_km": s["baseline_distance_km"],
                        "post_distance_km": s["post_flood_distance_km"],
                        "detour_km": s["detour_distance_km"]
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": s["coordinates"]
                    }
                })

        # Add hub point markers to GeoJSON
        for h_name, h_info in snapped_hubs.items():
            if h_info.get("coordinates"):
                routes_geojson_features.append({
                    "type": "Feature",
                    "id": f"hub_{h_name}",
                    "properties": {
                        "type": "regional_hub_marker",
                        "name": h_name,
                        "status": h_info["status"]
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": h_info["coordinates"]
                    }
                })

        routes_geojson = {
            "type": "FeatureCollection",
            "name": f"Connectivity_Routes_{clean_id}",
            "crs": {"type": "name", "properties": {"name": GEOGRAPHIC_CRS}},
            "metadata": {
                "analysis_id": clean_id,
                "provenance": analysis_provenance,
                "is_synthetic": is_synthetic_overall,
                "feature_count": len(routes_geojson_features)
            },
            "features": routes_geojson_features
        }

        # Closed roads GeoJSON
        closed_roads_geojson = {
            "type": "FeatureCollection",
            "name": f"Closed_Roads_{clean_id}",
            "crs": {"type": "name", "properties": {"name": GEOGRAPHIC_CRS}},
            "metadata": {
                "analysis_id": clean_id,
                "closed_count": len(closed_edge_records),
                "closure_method": closure_method
            },
            "features": [
                {
                    "type": "Feature",
                    "id": f"closed_{ce['edge_id']}",
                    "properties": {
                        "edge_id": ce["edge_id"],
                        "osm_id": ce["osm_id"],
                        "name": ce["name"],
                        "category": ce["category"],
                        "highway": ce["highway"],
                        "is_bridge": ce["is_bridge"],
                        "length_km": ce["length_km"],
                        "status": "SIMULATED_CLOSED"
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": ce["coords_wgs84"]
                    }
                }
                for ce in closed_edge_records
            ]
        }

        # Compile final summary
        summary = {
            "analysis_id": clean_id,
            "status": "COMPLETED",
            "provenance": analysis_provenance,
            "is_synthetic": is_synthetic_overall,
            "data_notice": (
                "DEMONSTRATION SYNTHETIC FIXTURE — NOT CONFIRMED REAL-WORLD DISCONNECTION"
                if is_synthetic_overall
                else (
                    "CURRENT DATA PREVIEW — NOT PRE-EVENT HISTORICAL BASELINE"
                    if infrastructure_provenance == "CURRENT_OSM_PREVIEW"
                    else "REAL SATELLITE & HISTORICAL OSM ROAD DISCONNECTION ANALYSIS"
                )
            ),
            "flood_analysis_id": clean_id,
            "flood_provenance": flood_meta.get("provenance", "SYNTHETIC_TEST_FIXTURE" if is_flood_synthetic else "REAL_SATELLITE_DERIVED"),
            "infrastructure_provenance": infrastructure_provenance,
            "osm_snapshot_date": osm_client.default_snapshot_date,
            "osm_attribution": OSM_ATTRIBUTION,
            "graph_construction_settings": {
                "projected_crs": PROJECTED_CRS_NEPAL,
                "snapping_tolerance_m": snapping_tolerance_m,
                "max_settlement_snap_distance_m": max_settlement_snap_distance_m,
                "elevation_separation_handled": True,
                "nodes_count": graph_stats["nodes_count"],
                "edges_count": graph_stats["edges_count"],
                "connected_components_count": graph_stats["connected_components_count"],
                "total_road_length_km": graph_stats["total_road_length_km"],
                "invalid_geometries_count": graph_stats["invalid_geometries_count"],
                "roads_omitted_count": graph_stats["roads_omitted_count"]
            },
            "closure_parameters": {
                "road_closure_method": closure_method,
                "closed_edges_count": len(closed_edge_records),
                "closed_bridges_count": sum(1 for ce in closed_edge_records if ce["is_bridge"]),
                "closure_description": "Edges intersecting candidate flood polygons removed from network"
            },
            "speed_assumptions": {
                "speeds_kmh": dict(self.graph_builder.assumed_speeds),
                "notice": "Documented speed assumptions per functional road class; not empirical measurements."
            },
            "summary_counts": {
                "settlements_evaluated": len(target_communities),
                "settlements_matched_and_snapped": len(target_communities) - unavailable_count - snap_failed_count,
                "newly_disconnected": newly_disconnected_count,
                "already_disconnected_at_baseline": already_disconnected_count,
                "detoured": detoured_count,
                "route_unchanged": unchanged_count,
                "unavailable": unavailable_count,
                "snap_failed": snap_failed_count
            },
            "settlement_details": settlement_results,
            "regional_hubs": snapped_hubs,
            "output_files": {
                "summary_json": "connectivity_summary.json",
                "routes_geojson": "connectivity_routes.geojson",
                "closed_roads_geojson": "closed_roads.geojson"
            },
            "limitations_and_uncertainties": [
                "Simulated closure based on spatial intersection with SAR candidate flood polygon; does not prove structural collapse or impassability.",
                "Vehicle travel speeds are modeled assumptions based on road functional classification, not empirical probe speeds.",
                "OSM road graph excludes informal mountain footpaths, rope bridges, and river fords capable of emergency pedestrian egress.",
                "Embankment elevations and bridge clearance heights above high-water mark are not modeled."
            ]
        }

        # Persist artifacts to disk
        summary_path = analysis_dir / "connectivity_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        routes_path = analysis_dir / "connectivity_routes.geojson"
        with open(routes_path, "w", encoding="utf-8") as f:
            json.dump(routes_geojson, f, indent=2)

        closed_path = analysis_dir / "closed_roads.geojson"
        with open(closed_path, "w", encoding="utf-8") as f:
            json.dump(closed_roads_geojson, f, indent=2)

        return summary


# Global singleton engine
connectivity_engine = SettlementConnectivityEngine()
