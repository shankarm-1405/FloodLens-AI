"""
Historical OpenStreetMap Pre-Event Baseline Fixture for Trishuli River Corridor, Nepal.
Anchored strictly to snapshot date: 2026-07-27T00:00:00Z (Pre-event baseline prior to August 2026 monsoonal surge).

Contains representative, topologically valid vector infrastructure for the study area:
Bounding Box: [85.05, 27.75, 85.25, 27.95] (Trishuli Basin, Nuwakot District, Bagmati / Gandaki Province).

Includes:
- Trishuli Highway (H02) & tributary feeder roads
- Mapped river bridges across the Trishuli and Tadi Khola
- Village & town settlement centers (Bidur, Battar, Devighat, Trishuli Bazaar)
- Healthcare & emergency service centers
- Residential & commercial building footprints in riverine alluvial terraces

Mandatory Attribution: © OpenStreetMap contributors.
"""

from typing import Dict, Any, List

OSM_SNAPSHOT_TIMESTAMP = "2026-07-27T00:00:00Z"
OSM_ATTRIBUTION = "© OpenStreetMap contributors."

HISTORICAL_TRISHULI_OSM_FIXTURE: Dict[str, Any] = {
    "type": "FeatureCollection",
    "name": "Historical_OSM_Infrastructure_Trishuli_20260727",
    "crs": {
        "type": "name",
        "properties": {"name": "EPSG:4326"}
    },
    "metadata": {
        "snapshot_date": OSM_SNAPSHOT_TIMESTAMP,
        "source": "OpenStreetMap Historical Archive (ohsome / Overpass Attic Reference)",
        "aoi_bbox": [85.05, 27.75, 85.25, 27.95],
        "attribution": OSM_ATTRIBUTION,
        "feature_count_total": 48
    },
    "features": [
        # --- CRITICAL HEALTHCARE & EMERGENCY FACILITIES ---
        {
            "type": "Feature",
            "id": "node/1001",
            "properties": {
                "osm_id": 1001,
                "osm_type": "node",
                "category": "healthcare",
                "amenity": "hospital",
                "name": "Trishuli Hospital",
                "name:ne": "त्रिशूली अस्पताल",
                "healthcare": "hospital",
                "operator": "Government of Nepal / Ministry of Health",
                "beds": "100",
                "emergency": "yes",
                "elevation_m": 612
            },
            "geometry": {
                "type": "Point",
                "coordinates": [85.1582, 27.9125]
            }
        },
        {
            "type": "Feature",
            "id": "node/1002",
            "properties": {
                "osm_id": 1002,
                "osm_type": "node",
                "category": "healthcare",
                "amenity": "clinic",
                "name": "Battar Community Health Post",
                "name:ne": "बट्टार स्वास्थ्य चौकी",
                "healthcare": "clinic",
                "emergency": "no",
                "elevation_m": 585
            },
            "geometry": {
                "type": "Point",
                "coordinates": [85.1524, 27.8842]
            }
        },
        {
            "type": "Feature",
            "id": "node/1003",
            "properties": {
                "osm_id": 1003,
                "osm_type": "node",
                "category": "healthcare",
                "amenity": "clinic",
                "name": "Devighat Sub-Health Clinic",
                "name:ne": "देवीघाट उप-स्वास्थ्य चौकी",
                "healthcare": "clinic",
                "emergency": "no",
                "elevation_m": 560
            },
            "geometry": {
                "type": "Point",
                "coordinates": [85.1418, 27.8610]
            }
        },
        {
            "type": "Feature",
            "id": "node/1004",
            "properties": {
                "osm_id": 1004,
                "osm_type": "node",
                "category": "healthcare",
                "amenity": "doctors",
                "name": "Bidur Municipality Family Medical Clinic",
                "name:ne": "विदुर परिवार क्लिनिक",
                "healthcare": "doctors",
                "elevation_m": 605
            },
            "geometry": {
                "type": "Point",
                "coordinates": [85.1610, 27.9045]
            }
        },

        # --- SETTLEMENTS & POPULATED PLACES ---
        {
            "type": "Feature",
            "id": "node/2001",
            "properties": {
                "osm_id": 2001,
                "osm_type": "node",
                "category": "settlement",
                "place": "town",
                "name": "Bidur",
                "name:ne": "विदुर",
                "population": "34000",
                "is_in:district": "Nuwakot",
                "admin_level": "8"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [85.1601, 27.9056]
            }
        },
        {
            "type": "Feature",
            "id": "node/2002",
            "properties": {
                "osm_id": 2002,
                "osm_type": "node",
                "category": "settlement",
                "place": "village",
                "name": "Battar",
                "name:ne": "बट्टार",
                "population": "12500",
                "is_in:district": "Nuwakot"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [85.1530, 27.8860]
            }
        },
        {
            "type": "Feature",
            "id": "node/2003",
            "properties": {
                "osm_id": 2003,
                "osm_type": "node",
                "category": "settlement",
                "place": "village",
                "name": "Devighat",
                "name:ne": "देवीघाट",
                "population": "6200",
                "is_in:district": "Nuwakot"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [85.1430, 27.8620]
            }
        },
        {
            "type": "Feature",
            "id": "node/2004",
            "properties": {
                "osm_id": 2004,
                "osm_type": "node",
                "category": "settlement",
                "place": "hamlet",
                "name": "Trishuli Bazaar",
                "name:ne": "त्रिशूली बजार",
                "population": "4800",
                "is_in:district": "Nuwakot"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [85.1480, 27.9210]
            }
        },
        {
            "type": "Feature",
            "id": "node/2005",
            "properties": {
                "osm_id": 2005,
                "osm_type": "node",
                "category": "settlement",
                "place": "hamlet",
                "name": "Tupche",
                "name:ne": "तुप्चे",
                "population": "2900",
                "is_in:district": "Nuwakot"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [85.1250, 27.8920]
            }
        },

        # --- BRIDGES ACROSS TRISHULI RIVER ---
        {
            "type": "Feature",
            "id": "way/3001",
            "properties": {
                "osm_id": 3001,
                "osm_type": "way",
                "category": "bridge",
                "bridge": "yes",
                "name": "Devighat Confluence Road Bridge",
                "highway": "secondary",
                "surface": "asphalt",
                "layer": "1"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [85.1380, 27.8595],
                    [85.1420, 27.8605],
                    [85.1460, 27.8615]
                ]
            }
        },
        {
            "type": "Feature",
            "id": "way/3002",
            "properties": {
                "osm_id": 3002,
                "osm_type": "way",
                "category": "bridge",
                "bridge": "yes",
                "name": "Battar Trishuli Suspension Footbridge",
                "highway": "footway",
                "bridge:structure": "suspension",
                "layer": "1"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [85.1470, 27.8820],
                    [85.1505, 27.8835],
                    [85.1530, 27.8845]
                ]
            }
        },
        {
            "type": "Feature",
            "id": "way/3003",
            "properties": {
                "osm_id": 3003,
                "osm_type": "way",
                "category": "bridge",
                "bridge": "yes",
                "name": "Bidur-Pipaltar Vehicular Bridge",
                "highway": "primary",
                "ref": "H02",
                "surface": "concrete",
                "layer": "1"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [85.1510, 27.9040],
                    [85.1545, 27.9055],
                    [85.1580, 27.9070]
                ]
            }
        },
        {
            "type": "Feature",
            "id": "way/3004",
            "properties": {
                "osm_id": 3004,
                "osm_type": "way",
                "category": "bridge",
                "bridge": "yes",
                "name": "Trishuli Hydro Intake Crossing",
                "highway": "service",
                "layer": "1"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [85.1450, 27.9280],
                    [85.1480, 27.9295]
                ]
            }
        },

        # --- HIGHWAYS & CORRIDOR ROADS ---
        {
            "type": "Feature",
            "id": "way/4001",
            "properties": {
                "osm_id": 4001,
                "osm_type": "way",
                "category": "road",
                "highway": "primary",
                "ref": "H02",
                "name": "Trishuli Highway (Section Devighat-Battar)",
                "surface": "asphalt",
                "lanes": "2",
                "maxspeed": "50"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [85.1410, 27.8580],
                    [85.1435, 27.8640],
                    [85.1460, 27.8720],
                    [85.1490, 27.8800],
                    [85.1525, 27.8870]
                ]
            }
        },
        {
            "type": "Feature",
            "id": "way/4002",
            "properties": {
                "osm_id": 4002,
                "osm_type": "way",
                "category": "road",
                "highway": "primary",
                "ref": "H02",
                "name": "Trishuli Highway (Section Battar-Bidur)",
                "surface": "asphalt",
                "lanes": "2",
                "maxspeed": "50"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [85.1525, 27.8870],
                    [85.1540, 27.8930],
                    [85.1565, 27.9000],
                    [85.1590, 27.9060]
                ]
            }
        },
        {
            "type": "Feature",
            "id": "way/4003",
            "properties": {
                "osm_id": 4003,
                "osm_type": "way",
                "category": "road",
                "highway": "primary",
                "ref": "H02",
                "name": "Trishuli Highway (Section Bidur-Trishuli Bazaar)",
                "surface": "asphalt",
                "lanes": "2"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [85.1590, 27.9060],
                    [85.1550, 27.9140],
                    [85.1500, 27.9220],
                    [85.1470, 27.9310]
                ]
            }
        },
        {
            "type": "Feature",
            "id": "way/4004",
            "properties": {
                "osm_id": 4004,
                "osm_type": "way",
                "category": "road",
                "highway": "secondary",
                "name": "Devighat Confluence Feeder Road",
                "surface": "paved"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [85.1320, 27.8540],
                    [85.1380, 27.8595],
                    [85.1420, 27.8605],
                    [85.1460, 27.8615],
                    [85.1510, 27.8650]
                ]
            }
        },
        {
            "type": "Feature",
            "id": "way/4005",
            "properties": {
                "osm_id": 4005,
                "osm_type": "way",
                "category": "road",
                "highway": "tertiary",
                "name": "Tupche-Battar River Valley Link",
                "surface": "unpaved"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [85.1250, 27.8920],
                    [85.1340, 27.8890],
                    [85.1430, 27.8860],
                    [85.1500, 27.8845]
                ]
            }
        },
        {
            "type": "Feature",
            "id": "way/4006",
            "properties": {
                "osm_id": 4006,
                "osm_type": "way",
                "category": "road",
                "highway": "residential",
                "name": "Battar Bazaar Access Road",
                "surface": "paved"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [85.1510, 27.8830],
                    [85.1530, 27.8850],
                    [85.1550, 27.8880]
                ]
            }
        },
        {
            "type": "Feature",
            "id": "way/4007",
            "properties": {
                "osm_id": 4007,
                "osm_type": "way",
                "category": "road",
                "highway": "track",
                "name": "Trishuli River Sand Harvesting Track",
                "surface": "ground"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [85.1480, 27.8920],
                    [85.1500, 27.8950],
                    [85.1520, 27.8990]
                ]
            }
        },

        # --- BUILDING FOOTPRINTS (POLYGONS ALONG ALLUVIAL TERRACES & FLOOD MARGINS) ---
        # Buildings near Devighat low alluvial terrace
        {
            "type": "Feature",
            "id": "way/5001",
            "properties": {
                "osm_id": 5001,
                "osm_type": "way",
                "category": "building",
                "building": "commercial",
                "name": "Devighat Confluence Warehousing",
                "levels": "1"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1415, 27.8602],
                    [85.1422, 27.8602],
                    [85.1422, 27.8608],
                    [85.1415, 27.8608],
                    [85.1415, 27.8602]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5002",
            "properties": {
                "osm_id": 5002,
                "osm_type": "way",
                "category": "building",
                "building": "residential",
                "levels": "2"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1425, 27.8611],
                    [85.1431, 27.8611],
                    [85.1431, 27.8616],
                    [85.1425, 27.8616],
                    [85.1425, 27.8611]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5003",
            "properties": {
                "osm_id": 5003,
                "osm_type": "way",
                "category": "building",
                "building": "residential",
                "levels": "2"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1434, 27.8618],
                    [85.1440, 27.8618],
                    [85.1440, 27.8624],
                    [85.1434, 27.8624],
                    [85.1434, 27.8618]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5004",
            "properties": {
                "osm_id": 5004,
                "osm_type": "way",
                "category": "building",
                "building": "industrial",
                "name": "Devighat Aggregate Crusher Shed",
                "levels": "1"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1398, 27.8625],
                    [85.1408, 27.8625],
                    [85.1408, 27.8632],
                    [85.1398, 27.8632],
                    [85.1398, 27.8625]
                ]]
            }
        },

        # Buildings along Battar lower terrace (river margin)
        {
            "type": "Feature",
            "id": "way/5005",
            "properties": {
                "osm_id": 5005,
                "osm_type": "way",
                "category": "building",
                "building": "residential",
                "name": "Riverside Settlement Homestead 1",
                "levels": "1"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1485, 27.8825],
                    [85.1492, 27.8825],
                    [85.1492, 27.8831],
                    [85.1485, 27.8831],
                    [85.1485, 27.8825]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5006",
            "properties": {
                "osm_id": 5006,
                "osm_type": "way",
                "category": "building",
                "building": "residential",
                "name": "Riverside Settlement Homestead 2",
                "levels": "1"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1495, 27.8835],
                    [85.1502, 27.8835],
                    [85.1502, 27.8841],
                    [85.1495, 27.8841],
                    [85.1495, 27.8835]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5007",
            "properties": {
                "osm_id": 5007,
                "osm_type": "way",
                "category": "building",
                "building": "commercial",
                "name": "Battar Agricultural Storage Coop",
                "levels": "1"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1508, 27.8842],
                    [85.1518, 27.8842],
                    [85.1518, 27.8850],
                    [85.1508, 27.8850],
                    [85.1508, 27.8842]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5008",
            "properties": {
                "osm_id": 5008,
                "osm_type": "way",
                "category": "building",
                "building": "residential",
                "levels": "2"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1520, 27.8852],
                    [85.1527, 27.8852],
                    [85.1527, 27.8858],
                    [85.1520, 27.8858],
                    [85.1520, 27.8852]
                ]]
            }
        },

        # Buildings along Battar upper terrace (elevated / safe zone)
        {
            "type": "Feature",
            "id": "way/5009",
            "properties": {
                "osm_id": 5009,
                "osm_type": "way",
                "category": "building",
                "building": "school",
                "name": "Battar Higher Secondary School",
                "levels": "2"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1550, 27.8870],
                    [85.1565, 27.8870],
                    [85.1565, 27.8885],
                    [85.1550, 27.8885],
                    [85.1550, 27.8870]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5010",
            "properties": {
                "osm_id": 5010,
                "osm_type": "way",
                "category": "building",
                "building": "commercial",
                "name": "Nuwakot Chamber of Commerce",
                "levels": "3"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1570, 27.8890],
                    [85.1580, 27.8890],
                    [85.1580, 27.8900],
                    [85.1570, 27.8900],
                    [85.1570, 27.8890]
                ]]
            }
        },

        # Buildings in Bidur center & riverside
        {
            "type": "Feature",
            "id": "way/5011",
            "properties": {
                "osm_id": 5011,
                "osm_type": "way",
                "category": "building",
                "building": "government",
                "name": "Bidur Municipality Municipal Office",
                "levels": "3"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1610, 27.9050],
                    [85.1622, 27.9050],
                    [85.1622, 27.9062],
                    [85.1610, 27.9062],
                    [85.1610, 27.9050]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5012",
            "properties": {
                "osm_id": 5012,
                "osm_type": "way",
                "category": "building",
                "building": "residential",
                "name": "Bidur Riverside Residence A",
                "levels": "2"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1520, 27.9035],
                    [85.1528, 27.9035],
                    [85.1528, 27.9042],
                    [85.1520, 27.9042],
                    [85.1520, 27.9035]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5013",
            "properties": {
                "osm_id": 5013,
                "osm_type": "way",
                "category": "building",
                "building": "residential",
                "name": "Bidur Riverside Residence B",
                "levels": "1"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1532, 27.9045],
                    [85.1540, 27.9045],
                    [85.1540, 27.9052],
                    [85.1532, 27.9052],
                    [85.1532, 27.9045]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5014",
            "properties": {
                "osm_id": 5014,
                "osm_type": "way",
                "category": "building",
                "building": "commercial",
                "name": "Pipaltar Vehicle Repair Workshop",
                "levels": "1"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1545, 27.9052],
                    [85.1555, 27.9052],
                    [85.1555, 27.9060],
                    [85.1545, 27.9060],
                    [85.1545, 27.9052]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5015",
            "properties": {
                "osm_id": 5015,
                "osm_type": "way",
                "category": "building",
                "building": "hospital",
                "name": "Trishuli Hospital Ward Wing",
                "levels": "3"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1578, 27.9120],
                    [85.1590, 27.9120],
                    [85.1590, 27.9130],
                    [85.1578, 27.9130],
                    [85.1578, 27.9120]
                ]]
            }
        },

        # Trishuli Hydro & upstream buildings
        {
            "type": "Feature",
            "id": "way/5016",
            "properties": {
                "osm_id": 5016,
                "osm_type": "way",
                "category": "building",
                "building": "industrial",
                "name": "Trishuli Hydropower Control Substation",
                "operator": "Nepal Electricity Authority",
                "levels": "2"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1465, 27.9270],
                    [85.1478, 27.9270],
                    [85.1478, 27.9282],
                    [85.1465, 27.9282],
                    [85.1465, 27.9270]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5017",
            "properties": {
                "osm_id": 5017,
                "osm_type": "way",
                "category": "building",
                "building": "residential",
                "name": "Trishuli Bazaar River Cottage",
                "levels": "1"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1475, 27.9225],
                    [85.1482, 27.9225],
                    [85.1482, 27.9232],
                    [85.1475, 27.9232],
                    [85.1475, 27.9225]
                ]]
            }
        },
        {
            "type": "Feature",
            "id": "way/5018",
            "properties": {
                "osm_id": 5018,
                "osm_type": "way",
                "category": "building",
                "building": "commercial",
                "name": "Trishuli Riverside Trout Restaurant",
                "levels": "1"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [85.1485, 27.9235],
                    [85.1493, 27.9235],
                    [85.1493, 27.9242],
                    [85.1485, 27.9242],
                    [85.1485, 27.9235]
                ]]
            }
        }
    ]
}
