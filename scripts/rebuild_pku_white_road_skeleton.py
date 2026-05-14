"""Rebuild the PKU outdoor graph from local white-road geometry.

The M13 stages created an empty inspection skeleton.  M14 keeps the same local
OSM white-road source and connects only adjacent nodes along each local
LineString, plus short POI-to-access edges.
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
NODE_ON_LINE_TOLERANCE_M = 2.75
WALK_SPEED_MPS = 1.25


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
    raw_key = quantized_key(projection, lng, lat)
    key = find_nearby_candidate_key(candidates, projection, lng, lat, raw_key)
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


def average_candidate_location(candidate: dict[str, Any]) -> tuple[float, float]:
    return (
        sum(candidate["lng_values"]) / len(candidate["lng_values"]),
        sum(candidate["lat_values"]) / len(candidate["lat_values"]),
    )


def find_nearby_candidate_key(
    candidates: dict[tuple[int, int], dict[str, Any]],
    projection: LocalProjection,
    lng: float,
    lat: float,
    raw_key: tuple[int, int],
) -> tuple[int, int]:
    best_key = raw_key
    best_distance = DEDUP_TOLERANCE_M
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            candidate_key = (raw_key[0] + dx, raw_key[1] + dy)
            candidate = candidates.get(candidate_key)
            if candidate is None:
                continue
            candidate_lng_lat = average_candidate_location(candidate)
            candidate_distance = distance_m(
                projection,
                (lng, lat),
                candidate_lng_lat,
            )
            if candidate_distance <= best_distance:
                best_distance = candidate_distance
                best_key = candidate_key
    return best_key


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
            source_osm_id_values: set[str] = set()
            for source in sources:
                source_osm_id = normalized_text(source.get("source_osm_id"))
                if source_osm_id:
                    source_osm_id_values.add(source_osm_id)
                for nested_osm_id in source.get("source_osm_ids", []):
                    nested_value = normalized_text(nested_osm_id)
                    if nested_value:
                        source_osm_id_values.add(nested_value)
            source_osm_ids = sorted(source_osm_id_values)
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


def node_lng_lat(node: dict[str, Any]) -> tuple[float, float]:
    location = node["location"]
    return float(location["lng"]), float(location["lat"])


def rounded_geometry_point(lng: float, lat: float) -> dict[str, float]:
    return {"lat": round(lat, 7), "lng": round(lng, 7)}


def geometry_distance_m(
    projection: LocalProjection,
    geometry: list[dict[str, float]],
) -> float:
    total = 0.0
    for start, end in zip(geometry, geometry[1:]):
        total += distance_m(
            projection,
            (float(start["lng"]), float(start["lat"])),
            (float(end["lng"]), float(end["lat"])),
        )
    return total


def normalize_geometry_payload(
    projection: LocalProjection,
    points: list[tuple[float, float]],
) -> list[dict[str, float]]:
    geometry: list[dict[str, float]] = []
    for lng, lat in points:
        point = rounded_geometry_point(lng, lat)
        if geometry and distance_m(
            projection,
            (geometry[-1]["lng"], geometry[-1]["lat"]),
            (point["lng"], point["lat"]),
        ) < 0.01:
            continue
        geometry.append(point)
    if len(geometry) == 1:
        geometry.append(dict(geometry[0]))
    return geometry


def polyline_cumulative_distances(
    projection: LocalProjection,
    coordinates: list[tuple[float, float]],
) -> list[float]:
    cumulative = [0.0]
    for start, end in zip(coordinates, coordinates[1:]):
        cumulative.append(cumulative[-1] + distance_m(projection, start, end))
    return cumulative


def interpolate_polyline_point(
    projection: LocalProjection,
    coordinates: list[tuple[float, float]],
    cumulative: list[float],
    along_m: float,
) -> tuple[float, float]:
    if along_m <= 0:
        return coordinates[0]
    if along_m >= cumulative[-1]:
        return coordinates[-1]

    for index, (start, end) in enumerate(zip(coordinates, coordinates[1:])):
        segment_start = cumulative[index]
        segment_end = cumulative[index + 1]
        if along_m > segment_end:
            continue
        segment_length = segment_end - segment_start
        if segment_length <= 0:
            return start
        ratio = (along_m - segment_start) / segment_length
        sx, sy = projection.to_xy(start[0], start[1])
        ex, ey = projection.to_xy(end[0], end[1])
        return projection.to_lng_lat(
            sx + (ex - sx) * ratio,
            sy + (ey - sy) * ratio,
        )
    return coordinates[-1]


def project_point_to_polyline(
    projection: LocalProjection,
    point: tuple[float, float],
    coordinates: list[tuple[float, float]],
    cumulative: list[float],
) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for index, (start, end) in enumerate(zip(coordinates, coordinates[1:])):
        segment = {"start": start, "end": end}
        projected_distance, projected = project_point_to_segment(
            projection,
            point,
            segment,
        )
        segment_distance = distance_m(projection, start, projected)
        along_m = cumulative[index] + segment_distance
        candidate = {
            "distance_m": projected_distance,
            "along_m": along_m,
            "projected": projected,
            "segment_index": index,
        }
        if best is None or projected_distance < best["distance_m"]:
            best = candidate
    if best is None:
        raise ValueError("Cannot project onto an empty polyline.")
    return best


def slice_polyline_geometry(
    projection: LocalProjection,
    coordinates: list[tuple[float, float]],
    cumulative: list[float],
    from_along_m: float,
    to_along_m: float,
) -> list[dict[str, float]]:
    reverse = from_along_m > to_along_m
    start_along = min(from_along_m, to_along_m)
    end_along = max(from_along_m, to_along_m)
    points = [interpolate_polyline_point(projection, coordinates, cumulative, start_along)]

    for vertex, vertex_along in zip(coordinates[1:-1], cumulative[1:-1]):
        if start_along < vertex_along < end_along:
            points.append(vertex)

    points.append(interpolate_polyline_point(projection, coordinates, cumulative, end_along))
    if reverse:
        points = list(reversed(points))
    return normalize_geometry_payload(projection, points)


def make_directed_edge(
    source: str,
    target: str,
    name: str,
    edge_type: str,
    distance: float,
    geometry: list[dict[str, float]],
    description: str,
) -> dict[str, Any]:
    return {
        "from": source,
        "to": target,
        "distance": round(distance, 2),
        "congestion": 1.0,
        "ideal_speed": WALK_SPEED_MPS,
        "type": edge_type,
        "vehicle_access": "pedestrian_only",
        "name": name,
        "description": description,
        "geometry": geometry,
    }


def reversed_geometry(geometry: list[dict[str, float]]) -> list[dict[str, float]]:
    return [dict(point) for point in reversed(geometry)]


def build_access_edges_and_matches(
    poi_nodes: list[dict[str, Any]],
    node_index: dict[str, dict[str, Any]],
    projection: LocalProjection,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    directed_edges: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for poi in poi_nodes:
        poi_id = normalized_text(poi.get("id"))
        access_id = normalized_text(poi.get("route_anchor_node_id"))
        access_node = node_index.get(access_id)
        if not poi_id or access_node is None:
            excluded.append(
                {
                    "kind": "poi_access",
                    "from": poi_id,
                    "to": access_id,
                    "reason": "missing_access_node",
                }
            )
            continue

        geometry = normalize_geometry_payload(
            projection,
            [node_lng_lat(poi), node_lng_lat(access_node)],
        )
        distance = geometry_distance_m(projection, geometry)
        source_osm_id = normalized_text(access_node.get("source_osm_id"))
        source_highway = normalized_text(access_node.get("source_highway"))
        name = f"{poi.get('name', poi_id)}接驳短边"
        description = "POI 只通过本短边连接到自己的 road_access 接驳点。"
        directed_edges.append(
            make_directed_edge(
                poi_id,
                access_id,
                name,
                "poi_access",
                distance,
                geometry,
                description,
            )
        )
        directed_edges.append(
            make_directed_edge(
                access_id,
                poi_id,
                name,
                "poi_access",
                distance,
                reversed_geometry(geometry),
                description,
            )
        )
        matches.append(
            {
                "edge_key": f"{poi_id}->{access_id}",
                "from": poi_id,
                "to": access_id,
                "geometry_source": "manual",
                "white_road_source": "poi_access_projection",
                "source_osm_id": source_osm_id,
                "source_highway": source_highway,
                "osm_way_ids": [source_osm_id] if source_osm_id else [],
                "distance_m": round(distance, 2),
                "confidence": 1.0,
                "geometry": geometry,
                "notes": "Short POI-to-access connector; not a white-road routing segment.",
            }
        )

    return directed_edges, matches, excluded


def build_white_road_edges_and_matches(
    road_nodes: list[dict[str, Any]],
    access_nodes: list[dict[str, Any]],
    features: list[dict[str, Any]],
    projection: LocalProjection,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    routable_nodes = road_nodes + access_nodes
    best_edges: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_candidate_count = 0
    excluded: list[dict[str, Any]] = []
    projected_node_count_by_feature: list[int] = []

    for feature_index, feature in enumerate(features):
        properties = feature.get("properties") or {}
        osm_id = normalized_text(properties.get("osm_id"))
        highway = normalized_text(properties.get("highway"))
        coordinates = [
            (float(lng), float(lat))
            for lng, lat in (feature.get("geometry") or {}).get("coordinates", [])
        ]
        if len(coordinates) < 2:
            continue

        cumulative = polyline_cumulative_distances(projection, coordinates)
        if cumulative[-1] <= 0:
            continue

        projected_by_node: dict[str, dict[str, Any]] = {}
        for node in routable_nodes:
            node_id = normalized_text(node.get("id"))
            projection_result = project_point_to_polyline(
                projection,
                node_lng_lat(node),
                coordinates,
                cumulative,
            )
            if projection_result["distance_m"] > NODE_ON_LINE_TOLERANCE_M:
                continue
            projected_by_node[node_id] = {
                "node": node,
                **projection_result,
            }

        projected_nodes = sorted(
            projected_by_node.values(),
            key=lambda item: (
                round(float(item["along_m"]), 3),
                normalized_text(item["node"].get("id")),
            ),
        )
        projected_node_count_by_feature.append(len(projected_nodes))

        for left, right in zip(projected_nodes, projected_nodes[1:]):
            source = normalized_text(left["node"].get("id"))
            target = normalized_text(right["node"].get("id"))
            if source == target:
                excluded.append(
                    {
                        "kind": "white_road",
                        "source_osm_id": osm_id,
                        "reason": "same_node_after_projection",
                    }
                )
                continue

            geometry = slice_polyline_geometry(
                projection,
                coordinates,
                cumulative,
                float(left["along_m"]),
                float(right["along_m"]),
            )
            if len(geometry) < 2:
                excluded.append(
                    {
                        "kind": "white_road",
                        "from": source,
                        "to": target,
                        "source_osm_id": osm_id,
                        "reason": "insufficient_geometry",
                    }
                )
                continue

            distance = geometry_distance_m(projection, geometry)
            pair_key = tuple(sorted((source, target)))
            candidate = {
                "from": source,
                "to": target,
                "source_osm_id": osm_id,
                "source_highway": highway,
                "feature_index": feature_index,
                "distance_m": distance,
                "geometry": geometry,
            }
            existing = best_edges.get(pair_key)
            if existing is not None and existing["distance_m"] <= distance:
                duplicate_candidate_count += 1
                continue
            if existing is not None:
                duplicate_candidate_count += 1
            best_edges[pair_key] = candidate

    directed_edges: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    for edge in sorted(best_edges.values(), key=lambda item: (item["from"], item["to"])):
        source = edge["from"]
        target = edge["to"]
        osm_id = edge["source_osm_id"]
        highway = edge["source_highway"]
        geometry = edge["geometry"]
        distance = edge["distance_m"]
        name = f"白线道路 {source} 至 {target}"
        description = "由本地 OSM 白线道路 LineString 相邻节点切片生成。"
        directed_edges.append(
            make_directed_edge(
                source,
                target,
                name,
                "white_road",
                distance,
                geometry,
                description,
            )
        )
        directed_edges.append(
            make_directed_edge(
                target,
                source,
                name,
                "white_road",
                distance,
                reversed_geometry(geometry),
                description,
            )
        )
        matches.append(
            {
                "edge_key": f"{source}->{target}",
                "from": source,
                "to": target,
                "geometry_source": "osm_matched",
                "white_road_source": "adjacent_osm_linestring_slice",
                "source_osm_id": osm_id,
                "source_highway": highway,
                "osm_way_ids": [osm_id] if osm_id else [],
                "distance_m": round(distance, 2),
                "confidence": 1.0,
                "geometry": geometry,
                "coverage": {
                    "line_slice_distance_m": round(distance, 2),
                    "node_projection_tolerance_m": NODE_ON_LINE_TOLERANCE_M,
                    "feature_index": edge["feature_index"],
                },
                "notes": "Connected only to the adjacent projected node on this local white-road LineString.",
            }
        )

    feature_projection_counts = [
        count for count in projected_node_count_by_feature if count > 0
    ]
    stats = {
        "undirected_white_road_edge_count": len(best_edges),
        "directed_white_road_edge_count": len(directed_edges),
        "duplicate_candidate_count": duplicate_candidate_count,
        "excluded_candidates": excluded[:50],
        "excluded_candidate_count": len(excluded),
        "features_with_projected_nodes": len(feature_projection_counts),
        "max_projected_nodes_on_feature": max(feature_projection_counts)
        if feature_projection_counts
        else 0,
    }
    return directed_edges, matches, stats


def build_route_edges_and_matches(
    poi_nodes: list[dict[str, Any]],
    road_nodes: list[dict[str, Any]],
    access_nodes: list[dict[str, Any]],
    features: list[dict[str, Any]],
    projection: LocalProjection,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    node_index = {node["id"]: node for node in poi_nodes + road_nodes + access_nodes}
    white_edges, white_matches, white_stats = build_white_road_edges_and_matches(
        road_nodes,
        access_nodes,
        features,
        projection,
    )
    access_edges, access_matches, access_excluded = build_access_edges_and_matches(
        poi_nodes,
        node_index,
        projection,
    )
    all_edges = white_edges + access_edges
    all_matches = white_matches + access_matches
    geometry_edge_count = sum(1 for edge in all_edges if edge.get("geometry"))
    fallback_edge_count = len(all_edges) - geometry_edge_count
    stats = {
        **white_stats,
        "undirected_poi_access_edge_count": len(access_matches),
        "directed_poi_access_edge_count": len(access_edges),
        "directed_edge_count": len(all_edges),
        "match_count": len(all_matches),
        "geometry_edge_count": geometry_edge_count,
        "fallback_edge_count": fallback_edge_count,
        "geometry_coverage_ratio": round(geometry_edge_count / len(all_edges), 4)
        if all_edges
        else 0.0,
        "excluded_access_candidates": access_excluded,
        "excluded_access_candidate_count": len(access_excluded),
    }
    return all_edges, all_matches, stats


def bbox_density_stats(
    nodes: list[dict[str, Any]],
    projection: LocalProjection,
) -> dict[str, Any]:
    if not nodes:
        return {
            "bbox_width_m": 0.0,
            "bbox_height_m": 0.0,
            "bbox_area_km2": 0.0,
            "nodes_per_km2": 0.0,
        }
    xy_points = [projection.to_xy(*node_lng_lat(node)) for node in nodes]
    x_values = [point[0] for point in xy_points]
    y_values = [point[1] for point in xy_points]
    width_m = max(x_values) - min(x_values)
    height_m = max(y_values) - min(y_values)
    area_km2 = (width_m * height_m) / 1_000_000
    return {
        "bbox_width_m": round(width_m, 2),
        "bbox_height_m": round(height_m, 2),
        "bbox_area_km2": round(area_km2, 4),
        "nodes_per_km2": round(len(nodes) / area_km2, 2) if area_km2 else 0.0,
    }


def near_duplicate_review(
    nodes: list[dict[str, Any]],
    projection: LocalProjection,
    threshold_m: float,
) -> dict[str, Any]:
    def source_id_set(node: dict[str, Any]) -> set[str]:
        source_ids = node.get("source_osm_ids") or []
        if not isinstance(source_ids, list):
            source_ids = [source_ids]
        source_id = normalized_text(node.get("source_osm_id"))
        return {normalized_text(item) for item in [*source_ids, source_id] if normalized_text(item)}

    near_pairs: list[dict[str, Any]] = []
    ignored_shared_source_pairs: list[dict[str, Any]] = []
    nearest_by_index: list[float | None] = [None] * len(nodes)
    for left_index, left in enumerate(nodes):
        for right_index, right in enumerate(nodes[left_index + 1 :], start=left_index + 1):
            pair_distance = distance_m(
                projection,
                node_lng_lat(left),
                node_lng_lat(right),
            )
            if (
                nearest_by_index[left_index] is None
                or pair_distance < nearest_by_index[left_index]
            ):
                nearest_by_index[left_index] = pair_distance
            if (
                nearest_by_index[right_index] is None
                or pair_distance < nearest_by_index[right_index]
            ):
                nearest_by_index[right_index] = pair_distance
            if pair_distance < threshold_m:
                pair = {
                    "from": left["id"],
                    "to": right["id"],
                    "distance_m": round(pair_distance, 3),
                }
                if source_id_set(left) & source_id_set(right):
                    ignored_shared_source_pairs.append(pair)
                else:
                    near_pairs.append(pair)
    nearest_distances = [
        distance for distance in nearest_by_index if distance is not None
    ]
    nearest_distances.sort()
    return {
        "threshold_m": threshold_m,
        "pair_count": len(near_pairs),
        "sample_pairs": near_pairs[:10],
        "ignored_shared_source_pair_count": len(ignored_shared_source_pairs),
        "ignored_shared_source_sample_pairs": ignored_shared_source_pairs[:10],
        "nearest_min_m": round(nearest_distances[0], 2) if nearest_distances else None,
        "nearest_median_m": (
            round(nearest_distances[len(nearest_distances) // 2], 2)
            if nearest_distances
            else None
        ),
    }


def nearest_white_distance(
    access_node: dict[str, Any],
    white_nodes: list[dict[str, Any]],
    projection: LocalProjection,
) -> float | None:
    if not white_nodes:
        return None
    return min(
        distance_m(projection, node_lng_lat(access_node), node_lng_lat(white_node))
        for white_node in white_nodes
    )


def build_review_payload(
    road_nodes: list[dict[str, Any]],
    access_nodes: list[dict[str, Any]],
    poi_projection_audit: list[dict[str, Any]],
    projection: LocalProjection,
) -> dict[str, Any]:
    duplicate_review = near_duplicate_review(
        road_nodes,
        projection,
        DEDUP_TOLERANCE_M,
    )
    density_review = bbox_density_stats(road_nodes, projection)
    projection_distances = [
        float(item["projection_distance_m"]) for item in poi_projection_audit
    ]
    max_projection_distance = max(projection_distances) if projection_distances else 0.0
    average_projection_distance = (
        sum(projection_distances) / len(projection_distances)
        if projection_distances
        else 0.0
    )
    access_white_distances = [
        nearest_white_distance(access_node, road_nodes, projection)
        for access_node in access_nodes
    ]
    colocated_access_count = sum(
        1
        for access_distance in access_white_distances
        if access_distance is not None and access_distance < 0.01
    )
    checks = {
        "white_road_near_duplicate_pair_count_is_zero": duplicate_review["pair_count"]
        == 0,
        "all_poi_projection_distances_within_review_threshold": all(
            not item["needs_review"] for item in poi_projection_audit
        ),
        "access_node_count_is_expected": len(access_nodes) == len(poi_projection_audit),
        "role_distribution_is_sufficient_for_next_stage": all(
            Counter(node["network_role"] for node in road_nodes).get(role, 0) >= minimum
            for role, minimum in {
                "junction": 200,
                "bend": 100,
                "endpoint": 250,
            }.items()
        ),
    }
    status = "reviewed_pass" if all(checks.values()) else "needs_follow_up"
    return {
        "status": status,
        "reviewed_at": "2026-05-13",
        "density": density_review,
        "near_duplicate_review": duplicate_review,
        "poi_projection_review": {
            "max_distance_m": round(max_projection_distance, 2),
            "average_distance_m": round(average_projection_distance, 2),
            "needs_review_count": sum(
                1 for item in poi_projection_audit if item["needs_review"]
            ),
            "access_nodes_colocated_with_white_road_nodes": colocated_access_count,
            "note": "Access nodes may intentionally share coordinates with existing white-road nodes because each POI still needs its own route anchor.",
        },
        "checks": checks,
        "notes": [
            "White-road candidate nodes are deduplicated by true projected distance across neighboring quantization buckets.",
            "M14 route edges connect only adjacent projected nodes on local white-road LineStrings.",
        ],
    }


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
    route_edges, edge_matches, edge_stats = build_route_edges_and_matches(
        poi_nodes,
        road_nodes,
        access_nodes,
        filtered_features,
        projection,
    )

    outdoor["nodes"] = rebuilt_nodes
    outdoor["edges"] = route_edges

    match_payload = {
        "metadata": {
            "site_id": site_id,
            "stage": "M14_white_road_adjacent_edges",
            "source": "local_osm_roads_white_line_proxy",
            "source_file": "osm_roads_simplified.geojson",
            "created_at": "2026-05-13",
            "description": "White-road routing graph: adjacent nodes are connected only along local OSM white-road LineString slices; POIs connect through short access edges.",
            "geometry_priority": ["white_road", "poi_access_projection", "fallback_line"],
            "runtime_policy": {
                "web_ui_calls_overpass": False,
                "web_ui_calls_osmnx": False,
                "routing_authority": "course_graph",
            },
            "coverage_statistics": {
                "white_road_edge_count": edge_stats["undirected_white_road_edge_count"],
                "poi_access_edge_count": edge_stats["undirected_poi_access_edge_count"],
                "directed_edge_count": edge_stats["directed_edge_count"],
                "geometry_edge_count": edge_stats["geometry_edge_count"],
                "fallback_edge_count": edge_stats["fallback_edge_count"],
                "geometry_coverage_ratio": edge_stats["geometry_coverage_ratio"],
            },
        },
        "matches": edge_matches,
    }

    role_counts = Counter(node.get("network_role") for node in road_nodes + access_nodes)
    highway_counts = Counter(
        normalized_text((feature.get("properties") or {}).get("highway"))
        for feature in filtered_features
    )
    review_payload = build_review_payload(
        road_nodes,
        access_nodes,
        poi_projection_audit,
        projection,
    )
    audit_payload = {
        "metadata": {
            "site_id": site_id,
            "stage": "M14_white_road_adjacent_edges",
            "created_at": "2026-05-13",
            "white_road_source": "data/sites/PKU/geo/osm_roads_simplified.geojson",
            "implementation": "pure_python_geometry_no_shapely",
            "stage_boundary": "white_road_adjacent_edges_only",
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
            "outdoor_edge_count": len(route_edges),
            "white_road_edge_count": edge_stats["directed_white_road_edge_count"],
            "poi_access_edge_count": edge_stats["directed_poi_access_edge_count"],
            "geometry_edge_count": edge_stats["geometry_edge_count"],
            "fallback_edge_count": edge_stats["fallback_edge_count"],
            "geometry_coverage_ratio": edge_stats["geometry_coverage_ratio"],
            "match_count": len(edge_matches),
            "poi_projection_needs_review_count": sum(
                1 for item in poi_projection_audit if item["needs_review"]
            ),
        },
        "candidate_stats": candidate_stats,
        "edge_construction": edge_stats,
        "generated_role_counts": dict(sorted(role_counts.items())),
        "filtered_highway_counts": dict(sorted(highway_counts.items())),
        "poi_projections": poi_projection_audit,
        "review": review_payload,
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
            "outdoor_edges_have_geometry": edge_stats["fallback_edge_count"] == 0,
            "matches_record_edges": len(edge_matches) > 0,
            "all_pois_have_route_anchor": all(
                normalized_text(node.get("route_anchor_node_id")) for node in poi_nodes
            ),
            "m13b_review_passed": review_payload["status"] == "reviewed_pass",
            "white_road_edges_exist": edge_stats["directed_white_road_edge_count"] > 0,
            "poi_access_edges_exist": edge_stats["directed_poi_access_edge_count"]
            == len(access_nodes) * 2,
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
        f"edges={summary['outdoor_edge_count']} "
        f"fallback_edges={summary['fallback_edge_count']}"
    )


if __name__ == "__main__":
    main()
