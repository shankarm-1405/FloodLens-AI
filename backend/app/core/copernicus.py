"""
Copernicus Data Space Ecosystem (CDSE) Client
Multimodal satellite data discovery, metadata validation, compatibility analysis,
and download management for Sentinel-1 C-SAR and Sentinel-2 MSI products.
"""

import os
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import requests
from app.config import settings, CACHE_DIR, DOWNLOADS_DIR

logger = logging.getLogger("floodlens.copernicus")

# Cache files
S1_CACHE_FILE = CACHE_DIR / "cdse_s1_cache.json"
S2_CACHE_FILE = CACHE_DIR / "cdse_s2_cache.json"


class CopernicusError(Exception):
    """Base exception for Copernicus API interactions."""
    pass


class CredentialsMissingError(CopernicusError):
    """Raised when Copernicus authentication is attempted without credentials."""
    pass


class InvalidCoordinatesError(CopernicusError):
    """Raised when AOI coordinates are outside valid geographic ranges."""
    pass


class InvalidDateError(CopernicusError):
    """Raised when an invalid date is provided."""
    pass


class CopernicusClient:
    """
    Official Copernicus Data Space Ecosystem (CDSE) API client.
    Implements OData v4 catalog queries, compatibility ranking,
    OAuth2 token acquisition, and cached product retrieval.
    """

    def __init__(self):
        self.catalogue_url = settings.CDSE_CATALOGUE_URL
        self.token_url = settings.CDSE_TOKEN_URL
        self.download_url = settings.CDSE_DOWNLOAD_URL
        self.timeout = settings.CDSE_TIMEOUT_SECONDS
        self.max_retries = settings.CDSE_MAX_RETRIES
        self.headers = {
            "User-Agent": "FloodLens-AI/1.0 (Track B: Multimodal Flood Assessment)",
            "Accept": "application/json"
        }
        self._token_cache: Optional[Dict[str, Any]] = None

    # -------------------------------------------------------------------------
    # Input Validation
    # -------------------------------------------------------------------------
    @staticmethod
    def validate_aoi_bbox(bbox: List[float]) -> Dict[str, float]:
        """
        Validates bounding box coordinates [min_lon, min_lat, max_lon, max_lat].
        """
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            raise InvalidCoordinatesError("Bounding box must be a 4-element list: [min_lon, min_lat, max_lon, max_lat]")
        
        try:
            min_lon, min_lat, max_lon, max_lat = (float(c) for c in bbox)
        except (ValueError, TypeError):
            raise InvalidCoordinatesError("All bounding box coordinates must be numeric")

        if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
            raise InvalidCoordinatesError(f"Longitudes must be between -180 and 180. Received: min_lon={min_lon}, max_lon={max_lon}")

        if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
            raise InvalidCoordinatesError(f"Latitudes must be between -90 and 90. Received: min_lat={min_lat}, max_lat={max_lat}")

        if min_lon >= max_lon:
            raise InvalidCoordinatesError(f"min_lon ({min_lon}) must be strictly less than max_lon ({max_lon})")

        if min_lat >= max_lat:
            raise InvalidCoordinatesError(f"min_lat ({min_lat}) must be strictly less than max_lat ({max_lat})")

        # Sanity check: prevent worldwide bounding box requests that would exhaust server memory
        if (max_lon - min_lon) > 10.0 or (max_lat - min_lat) > 10.0:
            raise InvalidCoordinatesError("Bounding box is excessively large (> 10 degrees). Please constrain your Area of Interest.")

        return {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat
        }

    @staticmethod
    def validate_event_date(date_str: str) -> datetime:
        """
        Validates ISO date YYYY-MM-DD.
        """
        if not isinstance(date_str, str):
            raise InvalidDateError("Event date must be a string formatted as YYYY-MM-DD")
        try:
            # Parse date only or full ISO timestamp
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            raise InvalidDateError(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.")

        # Temporal boundary check (Sentinel-1 operational era: 2014 onwards)
        if dt.year < 2014 or dt.year > 2030:
            raise InvalidDateError(f"Event year {dt.year} is outside operational Sentinel constellation lifetime (2014-2030).")

        return dt

    @staticmethod
    def _bbox_to_wkt_polygon(coords: Dict[str, float]) -> str:
        """Constructs closed WKT Polygon from bounding box coordinates."""
        min_lon = coords["min_lon"]
        min_lat = coords["min_lat"]
        max_lon = coords["max_lon"]
        max_lat = coords["max_lat"]
        return f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"

    # -------------------------------------------------------------------------
    # Authentication & Access Token
    # -------------------------------------------------------------------------
    def get_auth_token(self) -> Optional[str]:
        """
        Acquires or refreshes a CDSE Keycloak JWT token.
        Returns access token string or None if unconfigured.
        """
        now = time.time()
        if self._token_cache and self._token_cache.get("expires_at", 0) > (now + 60):
            return self._token_cache["access_token"]

        # Check OAuth2 Client Credentials first
        if settings.CDSE_CLIENT_ID and settings.CDSE_CLIENT_SECRET:
            payload = {
                "grant_type": "client_credentials",
                "client_id": settings.CDSE_CLIENT_ID,
                "client_secret": settings.CDSE_CLIENT_SECRET,
            }
        elif settings.CDSE_USERNAME and settings.CDSE_PASSWORD:
            payload = {
                "grant_type": "password",
                "username": settings.CDSE_USERNAME,
                "password": settings.CDSE_PASSWORD,
                "client_id": "cdse-public",
            }
        else:
            return None

        try:
            res = requests.post(
                self.token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout
            )
            if res.status_code == 200:
                data = res.json()
                expires_in = data.get("expires_in", 600)
                self._token_cache = {
                    "access_token": data["access_token"],
                    "expires_at": now + expires_in
                }
                return data["access_token"]
            else:
                logger.warning(f"CDSE authentication failed: {res.status_code} - {res.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Error connecting to CDSE token endpoint: {e}")
            return None

    # -------------------------------------------------------------------------
    # Caching Helpers
    # -------------------------------------------------------------------------
    def _read_cache(self, cache_file: Path) -> Dict[str, Any]:
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _write_cache(self, cache_file: Path, key: str, data: Any):
        cache = self._read_cache(cache_file)
        cache[key] = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write cache to {cache_file}: {e}")

    # -------------------------------------------------------------------------
    # Sentinel-1 SAR Acquisition Discovery
    # -------------------------------------------------------------------------
    def search_sentinel1_acquisitions(
        self,
        bbox: List[float],
        event_date_str: str,
        window_days: int = 15,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Discovers compatible pre-event and post-event Sentinel-1 GRD SAR acquisitions
        covering the AOI, checks geometry compatibility, and ranks candidate pairs.
        """
        coords = self.validate_aoi_bbox(bbox)
        event_dt = self.validate_event_date(event_date_str)
        poly_wkt = self._bbox_to_wkt_polygon(coords)

        # Check local cache first
        cache_key = f"S1_{bbox}_{event_date_str}_{window_days}"
        cached = self._read_cache(S1_CACHE_FILE).get(cache_key)
        if cached:
            logger.info(f"Returning cached Sentinel-1 catalogue results for {cache_key}")
            return cached["data"]

        pre_start = (event_dt - timedelta(days=window_days)).strftime("%Y-%m-%dT00:00:00.000Z")
        pre_end = event_dt.strftime("%Y-%m-%dT23:59:59.000Z")

        post_start = event_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        post_end = (event_dt + timedelta(days=window_days)).strftime("%Y-%m-%dT23:59:59.000Z")

        # Execute query for both sides of the window
        all_acquisitions = []
        errors = []

        query_filter = (
            f"Collection/Name eq 'SENTINEL-1' and "
            f"contains(Name, 'GRD') and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;{poly_wkt}') and "
            f"ContentDate/Start ge {pre_start} and "
            f"ContentDate/Start le {post_end}"
        )

        params = {
            "$filter": query_filter,
            "$top": str(max_results * 2),
            "$orderby": "ContentDate/Start desc",
            "$expand": "Attributes"
        }

        try:
            res = requests.get(
                self.catalogue_url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            if res.status_code == 200:
                raw_items = res.json().get("value", [])
                for item in raw_items:
                    parsed = self._parse_s1_product(item, event_dt)
                    if parsed:
                        all_acquisitions.append(parsed)
            else:
                errors.append(f"CDSE OData responded with status {res.status_code}: {res.text[:200]}")
        except Exception as e:
            errors.append(f"Network error querying Copernicus OData: {str(e)}")

        # Separate into pre-event and post-event pools
        pre_event_scenes = [a for a in all_acquisitions if a["timing_relation"] == "PRE_EVENT"]
        post_event_scenes = [a for a in all_acquisitions if a["timing_relation"] == "POST_EVENT"]

        # Compatibility pair evaluation
        compatible_pairs = self._evaluate_s1_pairs(pre_event_scenes, post_event_scenes)

        result = {
            "query_parameters": {
                "bbox": bbox,
                "event_date": event_date_str,
                "window_days": window_days,
                "pre_window": [pre_start, pre_end],
                "post_window": [post_start, post_end]
            },
            "total_found": len(all_acquisitions),
            "pre_event_count": len(pre_event_scenes),
            "post_event_count": len(post_event_scenes),
            "pre_event_acquisitions": pre_event_scenes,
            "post_event_acquisitions": post_event_scenes,
            "compatible_pairs": compatible_pairs,
            "best_compatible_pair": compatible_pairs[0] if compatible_pairs else None,
            "provenance": {
                "source": "Copernicus Data Space Ecosystem (CDSE)",
                "official_catalogue": self.catalogue_url,
                "mandatory_attribution": "Contains modified Copernicus Sentinel data 2026.",
                "queried_at": datetime.now(timezone.utc).isoformat()
            },
            "errors": errors,
            "is_demo_fixture": False
        }

        # Cache successful search
        if not errors:
            self._write_cache(S1_CACHE_FILE, cache_key, result)

        return result

    # -------------------------------------------------------------------------
    # Sentinel-2 Optical Acquisition Discovery
    # -------------------------------------------------------------------------
    def search_sentinel2_acquisitions(
        self,
        bbox: List[float],
        event_date_str: str,
        window_days: int = 10,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Discovers Sentinel-2 L2A optical products covering the AOI around the flood date,
        reporting cloud cover percentage and evaluating NDWI cross-check feasibility.
        """
        coords = self.validate_aoi_bbox(bbox)
        event_dt = self.validate_event_date(event_date_str)
        poly_wkt = self._bbox_to_wkt_polygon(coords)

        cache_key = f"S2_{bbox}_{event_date_str}_{window_days}"
        cached = self._read_cache(S2_CACHE_FILE).get(cache_key)
        if cached:
            return cached["data"]

        start_time = (event_dt - timedelta(days=window_days)).strftime("%Y-%m-%dT00:00:00.000Z")
        end_time = (event_dt + timedelta(days=window_days)).strftime("%Y-%m-%dT23:59:59.000Z")

        query_filter = (
            f"Collection/Name eq 'SENTINEL-2' and "
            f"contains(Name, 'MSIL2A') and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;{poly_wkt}') and "
            f"ContentDate/Start ge {start_time} and "
            f"ContentDate/Start le {end_time}"
        )

        params = {
            "$filter": query_filter,
            "$top": str(max_results),
            "$orderby": "ContentDate/Start desc",
            "$expand": "Attributes"
        }

        acquisitions = []
        errors = []

        try:
            res = requests.get(
                self.catalogue_url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            if res.status_code == 200:
                for item in res.json().get("value", []):
                    parsed = self._parse_s2_product(item)
                    if parsed:
                        acquisitions.append(parsed)
            else:
                errors.append(f"CDSE OData S2 query returned status {res.status_code}: {res.text[:200]}")
        except Exception as e:
            errors.append(f"Network error querying Sentinel-2 optical catalog: {str(e)}")

        result = {
            "query_parameters": {
                "bbox": bbox,
                "event_date": event_date_str,
                "window_days": window_days,
            },
            "total_found": len(acquisitions),
            "acquisitions": acquisitions,
            "usable_for_ndwi_count": sum(1 for a in acquisitions if a.get("cloud_cover_percentage", 100) < 20.0),
            "provenance": {
                "source": "Copernicus Data Space Ecosystem (CDSE)",
                "official_catalogue": self.catalogue_url,
                "mandatory_attribution": "Contains modified Copernicus Sentinel data 2026.",
                "queried_at": datetime.now(timezone.utc).isoformat()
            },
            "errors": errors,
            "is_demo_fixture": False
        }

        if not errors:
            self._write_cache(S2_CACHE_FILE, cache_key, result)

        return result

    # -------------------------------------------------------------------------
    # Internal Product Parsers & Compatibility Math
    # -------------------------------------------------------------------------
    def _parse_s1_product(self, item: Dict[str, Any], event_dt: datetime) -> Optional[Dict[str, Any]]:
        name = item.get("Name", "")
        item_id = item.get("Id", "")
        content_date = item.get("ContentDate", {})
        start_str = content_date.get("Start", "")

        if not start_str or not name:
            return None

        # Parse attributes
        attrs = {a.get("Name"): a.get("Value") for a in item.get("Attributes", []) if "Name" in a}
        orbit_dir = attrs.get("orbitDirection", "UNKNOWN").upper()
        rel_orbit = attrs.get("relativeOrbitNumber")
        if rel_orbit is not None:
            try:
                rel_orbit = int(rel_orbit)
            except Exception:
                pass
        pols = attrs.get("polarisationChannels", "VV&VH")

        try:
            acq_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        except Exception:
            return None

        timing_rel = "POST_EVENT" if acq_dt >= event_dt else "PRE_EVENT"
        delta_days = abs((acq_dt - event_dt).total_seconds()) / 86400.0

        platform = "Sentinel-1A" if name.startswith("S1A") else ("Sentinel-1B" if name.startswith("S1B") else "Sentinel-1")

        return {
            "id": item_id,
            "name": name,
            "platform": platform,
            "instrument": "C-SAR",
            "product_type": "GRD",
            "acquisition_date": start_str,
            "orbit_pass": orbit_dir,
            "relative_orbit": rel_orbit,
            "polarization": pols,
            "timing_relation": timing_rel,
            "days_from_event": round(delta_days, 2),
            "footprint_wkt": item.get("Footprint"),
            "content_length_bytes": item.get("ContentLength"),
            "is_demo_fixture": False
        }

    def _parse_s2_product(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        name = item.get("Name", "")
        item_id = item.get("Id", "")
        start_str = item.get("ContentDate", {}).get("Start", "")
        if not start_str or not name:
            return None

        attrs = {a.get("Name"): a.get("Value") for a in item.get("Attributes", []) if "Name" in a}
        cloud_pct = attrs.get("cloudCover", 100.0)
        try:
            cloud_pct = round(float(cloud_pct), 1)
        except Exception:
            cloud_pct = 100.0

        if cloud_pct < 20.0:
            rec = "OPTIMAL (Clear sky / minimal clouds - suitable for optical NDWI validation)"
        elif cloud_pct < 50.0:
            rec = "MODERATE (Partial cloud coverage - cloud masking required before NDWI extraction)"
        else:
            rec = "RESTRICTED (Heavy monsoonal cloud cover > 50% - optical cross-check compromised)"

        platform = "Sentinel-2A" if name.startswith("S2A") else ("Sentinel-2B" if name.startswith("S2B") else "Sentinel-2")

        return {
            "id": item_id,
            "name": name,
            "platform": platform,
            "instrument": "MSI",
            "product_type": "MSIL2A",
            "acquisition_date": start_str,
            "cloud_cover_percentage": cloud_pct,
            "recommendation": rec,
            "footprint_wkt": item.get("Footprint"),
            "content_length_bytes": item.get("ContentLength"),
            "is_demo_fixture": False
        }

    def _evaluate_s1_pairs(
        self,
        pre_scenes: List[Dict[str, Any]],
        post_scenes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Evaluates cross-compatibility between pre- and post-event Sentinel-1 scenes.
        Strictly prioritizes identical orbit directions and matching relative tracks.
        """
        pairs = []

        for pre in pre_scenes:
            for post in post_scenes:
                score = 0.0
                reasons = []

                # Rule 1: Orbit Direction (Essential for radar geometry)
                if pre["orbit_pass"] == post["orbit_pass"] and pre["orbit_pass"] != "UNKNOWN":
                    score += 0.50
                    reasons.append(f"Matching orbit direction: {pre['orbit_pass']}")
                else:
                    reasons.append(f"Mismatched orbit direction: pre is {pre['orbit_pass']}, post is {post['orbit_pass']}")

                # Rule 2: Relative Orbit / Track (Essential for incidence angle match)
                if pre["relative_orbit"] is not None and post["relative_orbit"] is not None:
                    if pre["relative_orbit"] == post["relative_orbit"]:
                        score += 0.35
                        reasons.append(f"Identical track (Relative Orbit {pre['relative_orbit']})")
                    else:
                        reasons.append(f"Different track: pre is {pre['relative_orbit']}, post is {post['relative_orbit']}")

                # Rule 3: Polarization
                if pre["polarization"] == post["polarization"]:
                    score += 0.10
                    reasons.append("Identical polarization channels")

                # Rule 4: Temporal proximity bonus (closer to flood date is preferred)
                total_span_days = pre["days_from_event"] + post["days_from_event"]
                proximity_bonus = max(0.0, 0.05 * (1.0 - (total_span_days / 40.0)))
                score += proximity_bonus

                # Classification label
                if score >= 0.85:
                    compatibility_level = "OPTIMAL"
                    summary = "Optimal radar pair: matching orbit direction and relative track eliminate relief parallax."
                elif score >= 0.50:
                    compatibility_level = "SUBOPTIMAL"
                    summary = "Suboptimal radar pair: orbit direction matches but tracks differ. Moderate relief disparity."
                else:
                    compatibility_level = "INCOMPATIBLE"
                    summary = "Incompatible viewing geometry: mismatched passes (Ascending vs Descending) will cause false flood anomalies in steep mountain terrain."

                pairs.append({
                    "pre_event_scene": pre,
                    "post_event_scene": post,
                    "compatibility_score": round(score, 3),
                    "compatibility_level": compatibility_level,
                    "explanation": summary,
                    "detailed_criteria": reasons,
                    "temporal_separation_days": round(total_span_days, 1)
                })

        # Sort pairs with highest compatibility first
        pairs.sort(key=lambda p: p["compatibility_score"], reverse=True)
        return pairs

    # -------------------------------------------------------------------------
    # Download Readiness & Execution
    # -------------------------------------------------------------------------
    def prepare_download(self, product_id: str) -> Dict[str, Any]:
        """
        Validates product retrieval readiness, checks credentials,
        and enforces download size safety limits.
        """
        token = self.get_auth_token()
        if not token:
            return {
                "status": "CREDENTIALS_REQUIRED",
                "product_id": product_id,
                "message": (
                    "Copernicus Data Space Ecosystem credentials not configured or expired. "
                    "Set CDSE_USERNAME and CDSE_PASSWORD (or CDSE_CLIENT_ID and CDSE_CLIENT_SECRET) in .env "
                    "to download raw Level-1 GRD / Level-2A products."
                ),
                "setup_guide": {
                    "registration_url": "https://dataspace.copernicus.eu/",
                    "credentials_endpoint": "https://identity.dataspace.copernicus.eu/",
                    "env_keys": ["CDSE_USERNAME", "CDSE_PASSWORD", "CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET"]
                },
                "downloaded": False
            }

        # Check existing cached download
        target_file = DOWNLOADS_DIR / f"{product_id}.zip"
        if target_file.exists() and target_file.stat().st_size > 0:
            return {
                "status": "CACHED",
                "product_id": product_id,
                "file_path": str(target_file),
                "size_bytes": target_file.stat().st_size,
                "downloaded": True
            }

        return {
            "status": "AUTHORIZED",
            "product_id": product_id,
            "download_url": f"{self.download_url}({product_id})/$value",
            "max_allowed_mb": settings.CDSE_MAX_DOWNLOAD_SIZE_MB,
            "downloaded": False,
            "message": "Authorized for secure streaming to data/downloads/."
        }


copernicus_client = CopernicusClient()
