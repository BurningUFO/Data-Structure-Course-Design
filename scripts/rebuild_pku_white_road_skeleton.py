"""Rebuild the PKU outdoor graph as a white-road inspection skeleton.

This script intentionally stops before adding route edges.  It keeps outdoor
POIs at their display coordinates, removes old road waypoints, creates new
white-road nodes from local OSM road geometry, and adds one projected road
access node for each outdoor POI.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any


WALKABLE_HIGHWAYS = {
    "footway",
    "path",
    "pedestrian",
    "steps",
    "service",
    "residential",
    "unclassified",
}

EXCLUDED_HIGHWAYS = {
    "primary",
    "secondary",
    "tertiary",
    "primary_link",
    "cycleway",
}

METER_PER_DEG_LAT = 111_320.0
WORK_BOUNDS_PADDING_M = 120.0
DEDUP_TOLERANCE_M = 2.0
HARD_BEND_DEGREES = 30.0
ACCESS_REVIEW_DISTANCE_M = 80.0


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def normalized_text(value: Any) -> str:
    return str(value or "").strip()


class LocalProjection:
    def __init__(self, lat0: float, lng0: float) -> None:
        self.lat0 = lat0
        self.lng0 = lng0
        self.lng_scale = METER_PER_DEG_LAT * math.cos(math.radians(lat0))

    def to_xy(self, lng: float, lat: float) -> tuple[float, float]:
        return (
            (lng - self.lng0) * self.lng_scale,
            (lat - self.lat0) * METER_PER_DEG_LAT,
        )

    def to_lng_lat(self, x: float, y: float) -> tuple[float, float]:
        return (
            self.lng0 + x / self.lng_scale,
            self.lat0 + y / METER_PER_DEG_LAT,
        )


def distance_m(
    projection: LocalProjection,
    left: tuple[float, float],
    right: tuple[float, float],
) -> float:
    lx, ly = projection.to_xy(left[0], left[1])
    rx, ry = projection.to_xy(right[0], right[1])
    return math.hypot(lx - rx, ly - ry)


def build_work_bounds(
    poi_nodes: list[dict[str, Any]],
) -> tuple[float, float, float, float, float, float]:
    lat_values = [node["location"]["lat"] for node in poi_nodes]
    lng_values = [node["location"]["lng"] for node in poi_nodes]
    lat0 = sum(lat_values) / len(lat_values)
    lng0 = sum(lng_values) / len(lng_values)
    lng_scale = METER_PER_DEG_LAT * math.cos(math.radians(lat0))
    lat_pad = WORK_BOUNDS_PADDING_M / METER_PER_DEG_LAT
    lng_pad = WORK_BOUNDS_PADDING_M / lng_scale
    return (
        min(lat_values) - lat_pad,
        min(lng_values) - lng_pad,
        max(lat_values) + lat_pad,
        max(lng_values) + lng_pad,
        lat0,
        lng0,
    )


def point_in_bounds(
    lng: float,
    lat: float,
    bounds: tuple[float, float, float, float],
) -> bool:
    south, west, north, east = bounds
    return south <= lat <= north and west <= lng <= east


def feature_intersects_bounds(
    coordinates: list[list[float]],
    bounds: tuple[float, float, float, float],
) -> bool:
    if any(point_in_bounds(float(lng), float(lat), bounds) for lng, lat in coordinates):
        return True
    south, west, north, east = bounds
    lng_values = [float(point[0]) for point in coordinates]
    lat_values = [float(point[1]) for point in coordinates]
    return not (
        max(lat_values) < south
        or min(lat_values) > north
        or max(lng_values) < west
        or min(lng_values) > east
    )


def filtered_road_features(
    roads_geojson: dict[str, Any],
    bounds: tuple[float, float, float, float],
) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for feature in roads_geojson.get("features", []):
        geometry = feature.get("geometry") or {}
        properties = feature.get("properties") or {}
        if geometry.get("type") != "LineString":
            continue
        highway = normalized_text(properties.get("highway"))
        if highway in EXCLUDED_HIGHWAYS or highway not in WALKABLE_HIGHWAYS:
            continue
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2:
            continue
        if not feature_intersects_bounds(coordinates, bounds):
            continue
        features.append(feature)
    return features


def quantized_key(
    projection: LocalProjection,
    lng: float,
    lat: float,
    tolerance_m: float = DEDUP_TOLERANCE_M,
) -> tuple[int, int]:
    x, y = projection.to_xy(lng, lat)
    return round(x / tolerance_m), round(y / tolerance_m)


def segment_intersection(
    projection: LocalProjection,
    a_lng_lat: tuple[float, float],
    b_lng_lat: tuple[float, float],
    c_lng_lat: tuple[float, float],
    d_lng_lat: tuple[float, float],
) -> tuple[float, float] | None:
    ax, ay = projection.to_xy(*a_lng_lat)
    bx, by = projection.to_xy(*b_lng_lat)
    cx, cy = projection.to_xy(*c_lng_lat)
    dx, dy = projection.to_xy(*d_lng_lat)
    rx, ry = bx - ax, by - ay
    sx, sy = dx - cx, dy - cy
    denominator = rx * sy - ry * sx
    if abs(denominator) < 1e-9:
        return None
    qpx, qpy = cx - ax, cy - ay
    t = (qpx * sy - qpy * sx) / denominator
    u = (qpx * ry - qpy * rx) / denominator
    endpoint_margin = 1e-6
    if not (-endpoint_margin <= t <= 1 + endpoint_margin):
        return None
    if not (-endpoint_margin <= u <= 1 + endpoint_margin):
        return None
    if endpoint_margin < t < 1 - endpoint_margin and endpoint_margin < u < 1 - endpoint_margin:
        return projection.to_lng_lat(ax + t * rx, ay + t * ry)
    return None


def angle_deflection_degrees(
    projection: LocalProjection,
    prev_point: tuple[float, float],
    point: tuple[float, float],
    next_point: tuple[float, float],
) -> float:
    ax, ay = projection.to_xy(*prev_point)
    bx, by = projection.to_xy(*point)
    cx, cy = projection.to_xy(*next_point)
    v1 = (ax - bx, ay - by)
    v2 = (cx - bx, cy - by)
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 < 1.0 or n2 < 1.0:
        return 0.0
    cosine = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return 180.0 - math.degrees(math.acos(cosine))


def add_candidate(
    candidates: dict[tuple[int, int], dict[str, Any]],
    projection: LocalProjection,
    lng: float,
    lat: float,
    role: str,
    source: dict[str, Any],
) -> None:
    key = quantized_key(projection, lng, lat)
    role_priority = {"junction": 4, "poi_access": 3, "bend": 2, "endpoint": 1}
    existing = candidates.get(key)
    if existing is None:
        candidates[key] = {
            "lng_values": [lng],
            "lat_values": [lat],
            "role": role,
            "sources": [source],
        }
        return
    existing["lng_values"].append(lng)
    existing["lat_values"].append(lat)
    existing["sources"].append(source)
    if role_priority[role] > role_priority[existing["role"]]:
        existing["role"] = role


def build_road_candidates(
    features: list[dict[str, Any]],
    projection: LocalProjection,
    bounds: tuple[float, float, float, float],
) -> tuple[dict[tuple[int, int], dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    candidates: dict[tuple[int, int], dict[str, Any]] = {}
    segments: list[dict[str, Any]] = []
    incidence: dict[tuple[int, int], set[int]] = defaultdict(set)
    stats = {
        "raw_endpoint_count": 0,
        "raw_bend_count": 0,
        "raw_shared_junction_count": 0,
        "raw_crossing_junction_count": 0,
    }

    for feature_index, feature in enumerate(features):
        properties = feature.get("properties") or {}
        osm_id = normalized_text(properties.get("osm_id"))
        highway = normalized_text(properties.get("highway"))
        coordinates = [
            (float(lng), float(lat))
            for lng, lat in (feature.get("geometry") or {}).get("coordinates", [])
        ]
        scoped = [point for point in coordinates if point_in_bounds(point[0], point[1], bounds)]
        if len(scoped) >= 2:
            for point in (scoped[0], scoped[-1]):
                add_candidate(
                    candidates,
                    projection,
                    point[0],
                    point[1],
                    "endpoint",
                    {"source_osm_id": osm_id, "source_highway": highway},
                )
                stats["raw_endpoint_count"] += 1

        for prev_point, point, next_point in zip(coordinates, coordinates[1:], coordinates[2:]):
            if not point_in_bounds(point[0], point[1], bounds):
                continue
            deflection = angle_deflection_degrees(projection, prev_point, point, next_point)
            if deflection >= HARD_BEND_DEGREES:
                add_candidate(
                    candidates,
                    projection,
                    point[0],
                    point[1],
                    "bend",
                    {
                        "source_osm_id": osm_id,
                        "source_highway": highway,
                        "deflection_degrees": round(deflection, 1),
                    },
                )
                stats["raw_bend_count"] += 1

        for start, end in zip(coordinates, coordinates[1:]):
            midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            if not (
                point_in_bounds(start[0], start[1], bounds)
                or point_in_bounds(end[0], end[1], bounds)
                or point_in_bounds(midpoint[0], midpoint[1], bounds)
            ):
                continue
            segment = {
                "start": start,
                "end": end,
                "feature_index": feature_index,
                "source_osm_id": osm_id,
                "source_highway": highway,
            }
            segment_index = len(segments)
            segments.append(segment)
            for point in (start, end):
                key = quantized_key(projection, point[0], point[1])
                incidence[key].add(segment_index)

    for key, segment_indexes in incidence.items():
        if len(segment_indexes) < 3:
            continue
        point_samples = []
        for segment_index in segment_indexes:
            segment = segments[segment_index]
            for point in (segment["start"], segment["end"]):
                if quantized_key(projection, point[0], point[1]) == key:
                    point_samples.append(point)
        lng = sum(point[0] for point in point_samples) / len(point_samples)
        lat = sum(point[1] for point in point_samples) / len(point_samples)
        add_candidate(
            candidates,
            projection,
            lng,
            lat,
            "junction",
            {"incident_segment_count": len(segment_indexes)},
        )
        stats["raw_shared_junction_count"] += 1

    for left_index, left in enumerate(segments):
        left_min_lng = min(left["start"][0], left["end"][0])
        left_max_lng = max(left["start"][0], left["end"][0])
        left_min_lat = min(left["start"][1], left["end"][1])
        left_max_lat = max(left["start"][1], left["end"][1])
        for right in segments[left_index + 1 :]:
            if left["feature_index"] == right["feature_index"]:
                continue
            if (
                max(right["start"][0], right["end"][0]) < left_min_lng
                or min(right["start"][0], right["end"][0]) > left_max_lng
                or max(right["start"][1], right["end"][1]) < left_min_lat
                or min(right["start"][1], right["end"][1]) > left_max_lat
            ):
                continue
            intersection = segment_intersection(
                projection,
                left["start"],
                left["end"],
                right["start"],
                right["end"],
            )
            if intersection is None:
                continue
            if not point_in_bounds(intersection[0], intersection[1], bounds):
                continue
            add_candidate(
                candidates,
                projection,
                intersection[0],
                intersection[1],
                "junction",
                {
                    "source_osm_ids": [left["source_osm_id"], right["source_osm_id"]],
                    "intersection_type": "proper_crossing",
                },
            )
            stats["raw_crossing_junction_count"] += 1

    return candidates, segments, stats


def project_point_to_segment(
    projection: LocalProjection,
    point: tuple[float, float],
    segment: dict[str, Any],
) -> tuple[float, tuple[float, float]]:
    px, py = projection.to_xy(point[0], point[1])
    ax, ay = projection.to_xy(segment["start"][0], segment["start"][1])
    bx, by = projection.to_xy(segment["end"][0], segment["end"][1])
    vx, vy = bx - ax, by - ay
    length_sq = vx * vx + vy * vy
    if length_sq <= 0:
        projected_xy = (ax, ay)
    else:
        t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / length_sq))
        projected_xy = (ax + t * vx, ay + t * vy)
    distance = math.hypot(px - projected_xy[0], py - projected_xy[1])
    lng, lat = projection.to_lng_lat(projected_xy[0], projected_xy[1])
    return distance, (lng, lat)


def find_nearest_segment_projection(
    projection: LocalProjection,
    point: tuple[float, float],
    segments: list[dict[str, Any]],
) -> tuple[float, tuple[float, float], dict[str, Any]]:
    best: tuple[float, tuple[float, float], dict[str, Any]] | None = None
    for segment in segments:
        distance, projected = project_point_to_segment(projection, point, segment)
        if best is None or distance < best[0]:
            best = (distance, projected, segment)
    if best is None:
        raise ValueError("No candidate white-road segments available for POI projection.")
    return best


def role_name(role: str) -> str:
    return {
        "junction": "白线道路交叉口",
        "bend": "白线道路硬拐点",
        "endpoint": "白线道路端点",
        "poi_access": "场所道路接驳点",
    }.get(role, role)


def build_road_nodes(
    candidates: dict[tuple[int, int], dict[str, Any]],
) -> list[dict[str, Any]]:
    role_order = {"junction": 0, "bend": 1, "endpoint": 2, "poi_access": 3}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates.values():
        lng = sum(candidate["lng_values"]) / len(candidate["lng_values"])
        lat = sum(candidate["lat_values"]) / len(candidate["lat_values"])
        grouped[candidate["role"]].append(
            {
                "lat": round(lat, 7),
                "lng": round(lng, 7),
                "role": candidate["role"],
                "sources": candidate["sources"],
            }
        )

    road_nodes: list[dict[str, Any]] = []
    for role in sorted(grouped, key=lambda item: role_order[item]):
        items = sorted(grouped[role], key=lambda item: (item["lat"], item["lng"]))
        for index, item in enumerate(items, start=1):
            node_id = f"road_white_{role}_{index:04d}"
            sources = item["sources"]
            source_osm_ids = sorted(
                {
                    normalized_text(source.get("source_osm_id"))
                    for source in sources
                    if normalized_text(source.get("source_osm_id"))
                }
            )
            source_highways = sorted(
                {
                    normalized_text(source.get("source_highway"))
                    for source in sources
                    if normalized_text(source.get("source_highway"))
                }
            )
            road_nodes.append(
                {
                    "id": node_id,
                    "name": f"{role_name(role)}{index:04d}",
                    "type": "waypoint",
                    "is_gate": False,
                    "sub_graph_id": None,
                    "tags": ["白线道路", "道路接驳点", role_name(role)],
                    "description": f"由本地 OSM 白线道路代理自动生成的{role_name(role)}，用于检查真实道路骨架。",
                    "category": "road",
                    "facilities": [],
                    "network_role": role,
                    "source": "osm_roads_simplified",
                    "source_osm_ids": source_osm_ids,
                    "source_highways": source_highways,
                    "location": {"lat": item["lat"], "lng": item["lng"]},
                }
            )
    return road_nodes


def build_access_nodes(
    poi_nodes: list[dict[str, Any]],
    projection: LocalProjection,
    segments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    access_nodes: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for poi in poi_nodes:
        poi_id = normalized_text(poi.get("id"))
        poi_name = normalized_text(poi.get("name")) or poi_id
        location = poi["location"]
        distance, projected, segment = find_nearest_segment_projection(
            projection,
            (float(location["lng"]), float(location["lat"])),
            segments,
        )
        distance = round(distance, 2)
        access_id = f"road_access_{poi_id}"
        needs_review = distance > ACCESS_REVIEW_DISTANCE_M
        poi["route_anchor_node_id"] = access_id
        poi["route_anchor_distance_m"] = distance
        poi["route_anchor_source"] = "white_road_projection"
        poi["route_anchor_needs_review"] = needs_review
        access_node = {
            "id": access_id,
            "name": f"{poi_name}道路接驳点",
            "type": "waypoint",
            "is_gate": False,
            "sub_graph_id": None,
            "tags": ["白线道路", "场所接驳", poi_name],
            "description": f"{poi_name}投影到最近白线道路上的接驳点。本阶段只用于检查，不建立路由边。",
            "category": "road",
            "facilities": [],
            "network_role": "poi_access",
            "anchor_for": poi_id,
            "anchor_for_name": poi_name,
            "projection_distance_m": distance,
            "projection_source": "nearest_white_road_segment",
            "source_osm_id": normalized_text(segment.get("source_osm_id")),
            "source_highway": normalized_text(segment.get("source_highway")),
            "needs_review": needs_review,
            "location": {
                "lat": round(projected[1], 7),
                "lng": round(projected[0], 7),
            },
        }
        access_nodes.append(access_node)
        audit_rows.append(
            {
                "poi_id": poi_id,
                "poi_name": poi_name,
                "category": poi.get("category"),
                "original_location": location,
                "anchor_node_id": access_id,
                "anchor_location": access_node["location"],
                "projection_distance_m": distance,
                "source_osm_id": access_node["source_osm_id"],
                "source_highway": access_node["source_highway"],
                "needs_review": needs_review,
            }
        )
    return access_nodes, audit_rows


def rebuild(repo_root: Path, site_id: str) -> dict[str, Any]:
    site_dir = repo_root / "data" / "sites" / site_id
    geo_dir = site_dir / "geo"
    outdoor_path = site_dir / "outdoor.json"
    roads_path = geo_dir / "osm_roads_simplified.geojson"
    matches_path = geo_dir / "edge_osm_geometry_matches.json"
    audit_path = geo_dir / "white_road_skeleton_audit.json"

    original_outdoor = load_json(outdoor_path)
    outdoor = deepcopy(original_outdoor)
    roads_geojson = load_json(roads_path)

    poi_nodes = [
        deepcopy(node)
        for node in outdoor.get("nodes", [])
        if normalized_text(node.get("category")) != "road"
    ]
    if not poi_nodes:
        raise ValueError("No outdoor POI nodes found; refusing to rebuild an empty graph.")

    south, west, north, east, lat0, lng0 = build_work_bounds(poi_nodes)
    bounds = (south, west, north, east)
    projection = LocalProjection(lat0, lng0)
    filtered_features = filtered_road_features(roads_geojson, bounds)
    candidates, segments, candidate_stats = build_road_candidates(
        filtered_features,
        projection,
        bounds,
    )
    if not segments:
        raise ValueError("No white-road segments found in the working bounds.")

    road_nodes = build_road_nodes(candidates)
    access_nodes, poi_projection_audit = build_access_nodes(poi_nodes, projection, segments)
    rebuilt_nodes = poi_nodes + road_nodes + access_nodes

    outdoor["nodes"] = rebuilt_nodes
    outdoor["edges"] = []

    match_payload = {
        "metadata": {
            "site_id": site_id,
            "stage": "M13A_white_road_empty_skeleton",
            "source": "local_osm_roads_white_line_proxy",
            "source_file": "osm_roads_simplified.geojson",
            "created_at": "2026-05-13",
            "description": "White-road inspection skeleton: outdoor route edges are intentionally empty while road nodes and POI access projections are reviewed.",
            "geometry_priority": ["white_road", "manual", "fallback_line"],
            "runtime_policy": {
                "web_ui_calls_overpass": False,
                "web_ui_calls_osmnx": False,
                "routing_authority": "course_graph",
            },
        },
        "matches": [],
    }

    role_counts = Counter(node.get("network_role") for node in road_nodes + access_nodes)
    highway_counts = Counter(
        normalized_text((feature.get("properties") or {}).get("highway"))
        for feature in filtered_features
    )
    audit_payload = {
        "metadata": {
            "site_id": site_id,
            "stage": "M13A_white_road_empty_skeleton",
            "created_at": "2026-05-13",
            "white_road_source": "data/sites/PKU/geo/osm_roads_simplified.geojson",
            "implementation": "pure_python_geometry_no_shapely",
            "stage_boundary": "outdoor_edges_intentionally_empty",
        },
        "rules": {
            "included_highways": sorted(WALKABLE_HIGHWAYS),
            "excluded_highways": sorted(EXCLUDED_HIGHWAYS),
            "work_bounds_padding_m": WORK_BOUNDS_PADDING_M,
            "dedup_tolerance_m": DEDUP_TOLERANCE_M,
            "hard_bend_degrees": HARD_BEND_DEGREES,
            "access_review_distance_m": ACCESS_REVIEW_DISTANCE_M,
        },
        "bounds": {
            "south": round(south, 7),
            "west": round(west, 7),
            "north": round(north, 7),
            "east": round(east, 7),
        },
        "summary": {
            "input_outdoor_node_count": len(original_outdoor.get("nodes", [])),
            "poi_node_count": len(poi_nodes),
            "old_road_node_count_removed": sum(
                1
                for node in original_outdoor.get("nodes", [])
                if normalized_text(node.get("category")) == "road"
            ),
            "road_feature_count_total": len(roads_geojson.get("features", [])),
            "road_feature_count_filtered": len(filtered_features),
            "road_segment_count_filtered": len(segments),
            "generated_white_road_node_count": len(road_nodes),
            "generated_access_node_count": len(access_nodes),
            "generated_node_count_total": len(rebuilt_nodes),
            "outdoor_edge_count": 0,
            "match_count": 0,
            "poi_projection_needs_review_count": sum(
                1 for item in poi_projection_audit if item["needs_review"]
            ),
        },
        "candidate_stats": candidate_stats,
        "generated_role_counts": dict(sorted(role_counts.items())),
        "filtered_highway_counts": dict(sorted(highway_counts.items())),
        "poi_projections": poi_projection_audit,
        "checks": {
            "old_road_nodes_removed": not any(
                normalized_text(node.get("id")).startswith("road_")
                and normalized_text(node.get("network_role")) not in {
                    "junction",
                    "bend",
                    "endpoint",
                    "poi_access",
                }
                for node in rebuilt_nodes
                if normalized_text(node.get("category")) == "road"
            ),
            "outdoor_edges_empty": True,
            "matches_empty": True,
            "all_pois_have_route_anchor": all(
                normalized_text(node.get("route_anchor_node_id")) for node in poi_nodes
            ),
        },
    }

    write_json(outdoor_path, outdoor)
    write_json(matches_path, match_payload)
    write_json(audit_path, audit_payload)
    return audit_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-id", default="PKU")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    audit = rebuild(Path(args.repo_root), args.site_id)
    summary = audit["summary"]
    print(
        "rebuilt white-road skeleton: "
        f"nodes={summary['generated_node_count_total']} "
        f"white_road_nodes={summary['generated_white_road_node_count']} "
        f"access_nodes={summary['generated_access_node_count']} "
        f"edges={summary['outdoor_edge_count']}"
    )


if __name__ == "__main__":
    main()
