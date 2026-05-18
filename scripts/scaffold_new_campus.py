from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SITE_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
DEFAULT_TRANSPORT_SPEEDS = {"walk": 1.2, "bike": 3.0, "mixed": 2.0}


@dataclass(frozen=True)
class ScaffoldConfig:
    site_id: str
    site_name: str
    location: str
    description: str
    center_lat: float
    center_lng: float
    data_root: Path
    with_indoor_placeholder: bool = False
    indoor_building_id: str = "library"
    indoor_building_name: str = "Library Placeholder"
    indoor_graph_id: str | None = None
    indoor_template_id: str = "library_service_v1"
    overwrite: bool = False
    dry_run: bool = False


def normalize_site_id(raw_site_id: str) -> str:
    site_id = str(raw_site_id).strip().upper()
    if not SITE_ID_RE.match(site_id):
        raise ValueError(
            "site_id must start with an uppercase letter and contain only "
            "uppercase letters, numbers, or underscores"
        )
    return site_id


def json_dump(data: dict[str, Any], path: Path, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def shifted_location(center_lat: float, center_lng: float, north_m: float, east_m: float) -> dict[str, float]:
    lat_delta = north_m / 111_320.0
    lng_scale = max(abs(math.cos(math.radians(center_lat))), 0.01)
    lng_delta = east_m / (111_320.0 * lng_scale)
    return {
        "lat": round(center_lat + lat_delta, 7),
        "lng": round(center_lng + lng_delta, 7),
    }


def haversine_m(left: dict[str, float], right: dict[str, float]) -> float:
    radius_m = 6_371_000.0
    lat1 = math.radians(float(left["lat"]))
    lat2 = math.radians(float(right["lat"]))
    dlat = math.radians(float(right["lat"]) - float(left["lat"]))
    dlng = math.radians(float(right["lng"]) - float(left["lng"]))
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return round(radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


def base_node(
    *,
    node_id: str,
    name: str,
    category: str,
    node_type: str,
    location: dict[str, float],
    is_gate: bool = False,
    tags: list[str] | None = None,
    facilities: list[str] | None = None,
    open_hours: str | None = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": node_id,
        "name": name,
        "type": node_type,
        "is_gate": is_gate,
        "sub_graph_id": None,
        "tags": tags or [category],
        "keywords": tags or [category],
        "description": "M25C template placeholder; replace with verified campus data before rollout.",
        "category": category,
        "facilities": facilities or [],
        "location": location,
    }
    if open_hours:
        node["open_hours"] = open_hours
    if category != "road":
        node["heat"] = 0.5
        node["rating"] = 4.0
    return node


def build_outdoor_nodes(config: ScaffoldConfig) -> list[dict[str, Any]]:
    name_prefix = config.site_name or config.site_id
    center_lat = config.center_lat
    center_lng = config.center_lng
    nodes = [
        base_node(
            node_id="gate_north",
            name=f"{name_prefix} North Gate Placeholder",
            category="entrance",
            node_type="entrance",
            is_gate=True,
            tags=["gate", "entrance", "north"],
            facilities=["security"],
            location=shifted_location(center_lat, center_lng, 260, 0),
        ),
        base_node(
            node_id="gate_south",
            name=f"{name_prefix} South Gate Placeholder",
            category="entrance",
            node_type="entrance",
            is_gate=True,
            tags=["gate", "entrance", "south"],
            facilities=["security"],
            location=shifted_location(center_lat, center_lng, -260, 0),
        ),
        base_node(
            node_id="library",
            name=f"{name_prefix} Library Placeholder",
            category="education",
            node_type="building",
            is_gate=config.with_indoor_placeholder,
            tags=["library", "study", "education"],
            facilities=["reading", "self-study"],
            open_hours="replace_with_local_hours",
            location=shifted_location(center_lat, center_lng, 80, -80),
        ),
        base_node(
            node_id="teaching_building",
            name=f"{name_prefix} Teaching Building Placeholder",
            category="education",
            node_type="building",
            is_gate=False,
            tags=["teaching", "classroom", "education"],
            facilities=["classroom"],
            location=shifted_location(center_lat, center_lng, 80, 100),
        ),
        base_node(
            node_id="canteen",
            name=f"{name_prefix} Canteen Placeholder",
            category="catering",
            node_type="facility",
            tags=["canteen", "food", "dining"],
            facilities=["dining"],
            open_hours="replace_with_local_hours",
            location=shifted_location(center_lat, center_lng, -90, -110),
        ),
        base_node(
            node_id="dormitory_1",
            name=f"{name_prefix} Dormitory Placeholder",
            category="dormitory",
            node_type="dormitory",
            tags=["dormitory", "residence", "life"],
            facilities=["laundry"],
            location=shifted_location(center_lat, center_lng, -120, 120),
        ),
        base_node(
            node_id="service_center",
            name=f"{name_prefix} Service Center Placeholder",
            category="service",
            node_type="facility",
            tags=["service", "campus-card", "helpdesk"],
            facilities=["helpdesk"],
            location=shifted_location(center_lat, center_lng, 0, 150),
        ),
        base_node(
            node_id="restroom_main",
            name=f"{name_prefix} Restroom Placeholder",
            category="restroom",
            node_type="facility",
            tags=["restroom", "service"],
            facilities=["restroom"],
            location=shifted_location(center_lat, center_lng, -10, 80),
        ),
        base_node(
            node_id="road_core",
            name="Core Road Placeholder",
            category="road",
            node_type="waypoint",
            tags=["road", "waypoint"],
            location=shifted_location(center_lat, center_lng, 0, 0),
        ),
        base_node(
            node_id="road_north",
            name="North Road Waypoint Placeholder",
            category="road",
            node_type="waypoint",
            tags=["road", "waypoint"],
            location=shifted_location(center_lat, center_lng, 150, 0),
        ),
        base_node(
            node_id="road_south",
            name="South Road Waypoint Placeholder",
            category="road",
            node_type="waypoint",
            tags=["road", "waypoint"],
            location=shifted_location(center_lat, center_lng, -150, 0),
        ),
        base_node(
            node_id="road_academic",
            name="Academic Road Waypoint Placeholder",
            category="road",
            node_type="waypoint",
            tags=["road", "waypoint"],
            location=shifted_location(center_lat, center_lng, 70, 0),
        ),
        base_node(
            node_id="road_life",
            name="Life Area Road Waypoint Placeholder",
            category="road",
            node_type="waypoint",
            tags=["road", "waypoint"],
            location=shifted_location(center_lat, center_lng, -90, 0),
        ),
    ]

    if config.with_indoor_placeholder:
        indoor_graph_id = resolve_indoor_graph_id(config)
        linked_indoor_entry = False
        for node in nodes:
            if node["id"] == config.indoor_building_id:
                node["is_gate"] = True
                node["sub_graph_id"] = indoor_graph_id
                node["indoor_supported"] = True
                node["indoor_graph_id"] = indoor_graph_id
                node["indoor_entry_node_id"] = indoor_gate_node_id(config.indoor_building_id)
                linked_indoor_entry = True
                break
        if not linked_indoor_entry:
            raise ValueError(
                "indoor_building_id must match a generated outdoor node id; "
                "use one of library, teaching_building, canteen, dormitory_1, service_center, or restroom_main"
            )

    return nodes


def edge_record(
    source: str,
    target: str,
    nodes_by_id: dict[str, dict[str, Any]],
    *,
    edge_type: str,
) -> dict[str, Any]:
    source_loc = nodes_by_id[source]["location"]
    target_loc = nodes_by_id[target]["location"]
    return {
        "from": source,
        "to": target,
        "distance": haversine_m(source_loc, target_loc),
        "name": f"{source} to {target}",
        "description": "M25C scaffold edge; replace distance and geometry with verified local data.",
        "type": edge_type,
        "congestion": 1.0,
        "ideal_speed": 1.2,
        "vehicle_access": "all",
        "allowed_transports": ["walk", "bike", "mixed"],
        "transport_speeds": DEFAULT_TRANSPORT_SPEEDS,
        "geometry": [source_loc, target_loc],
    }


def add_two_way_edge(
    edges: list[dict[str, Any]],
    source: str,
    target: str,
    nodes_by_id: dict[str, dict[str, Any]],
    *,
    edge_type: str,
) -> None:
    edges.append(edge_record(source, target, nodes_by_id, edge_type=edge_type))
    edges.append(edge_record(target, source, nodes_by_id, edge_type=edge_type))


def build_outdoor_graph(config: ScaffoldConfig) -> dict[str, Any]:
    nodes = build_outdoor_nodes(config)
    nodes_by_id = {str(node["id"]): node for node in nodes}
    edges: list[dict[str, Any]] = []
    for source, target, edge_type in [
        ("gate_north", "road_north", "campus_walkway"),
        ("road_north", "road_core", "campus_walkway"),
        ("road_core", "road_south", "campus_walkway"),
        ("road_south", "gate_south", "campus_walkway"),
        ("road_core", "road_academic", "campus_walkway"),
        ("road_core", "road_life", "campus_walkway"),
        ("road_academic", "library", "poi_access"),
        ("road_academic", "teaching_building", "poi_access"),
        ("road_life", "canteen", "poi_access"),
        ("road_life", "dormitory_1", "poi_access"),
        ("road_core", "service_center", "poi_access"),
        ("road_core", "restroom_main", "poi_access"),
    ]:
        add_two_way_edge(edges, source, target, nodes_by_id, edge_type=edge_type)

    return {
        "graph_id": f"{config.site_id}_outdoor",
        "graph_type": "outdoor",
        "metadata": {
            "stage": "M25C",
            "scaffold": True,
            "source": "scripts/scaffold_new_campus.py",
            "notes": "Template-only graph. Replace placeholders with verified campus data before M26 or later rollout.",
        },
        "nodes": nodes,
        "edges": edges,
    }


def empty_feature_collection() -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": []}


def build_indoor_template_catalog() -> dict[str, Any]:
    return {
        "templates": [
            {
                "template_id": "teaching_block_v1",
                "template_name": "Teaching / research building template",
                "recommended_building_types": ["teaching", "research", "academy"],
                "default_floor_count": 3,
                "required_zone_types": ["restroom", "elevator", "stairs", "education", "service"],
            },
            {
                "template_id": "library_service_v1",
                "template_name": "Library / service building template",
                "recommended_building_types": ["library", "archive", "service_center"],
                "default_floor_count": 3,
                "required_zone_types": ["restroom", "elevator", "stairs", "reading_room", "service"],
            },
            {
                "template_id": "dormitory_v1",
                "template_name": "Dormitory template",
                "recommended_building_types": ["dormitory", "residence"],
                "default_floor_count": 3,
                "required_zone_types": ["restroom", "elevator", "stairs", "dormitory", "service"],
            },
            {
                "template_id": "canteen_service_v1",
                "template_name": "Canteen / life-service building template",
                "recommended_building_types": ["canteen", "lifestyle_service"],
                "default_floor_count": 2,
                "required_zone_types": ["restroom", "elevator", "stairs", "catering", "service"],
            },
            {
                "template_id": "sports_public_v1",
                "template_name": "Sports / public building template",
                "recommended_building_types": ["sports", "public"],
                "default_floor_count": 3,
                "required_zone_types": ["restroom", "elevator", "stairs", "sports", "service"],
            },
        ]
    }


def resolve_indoor_graph_id(config: ScaffoldConfig) -> str:
    if config.indoor_graph_id:
        graph_id = config.indoor_graph_id.strip()
    else:
        graph_id = f"indoor_{config.indoor_building_id.upper()}"
    if not graph_id.startswith("indoor_"):
        raise ValueError("indoor_graph_id must start with 'indoor_'")
    return graph_id


def indoor_gate_node_id(building_id: str) -> str:
    return f"{building_id}_indoor_gate"


def build_indoor_registry(config: ScaffoldConfig) -> dict[str, Any]:
    if not config.with_indoor_placeholder:
        return {"buildings": []}
    return {
        "buildings": [
            {
                "building_id": config.indoor_building_id,
                "building_name": config.indoor_building_name,
                "entry_node_id": config.indoor_building_id,
                "indoor_graph_id": resolve_indoor_graph_id(config),
                "template_id": config.indoor_template_id,
                "floor_ids": ["F1", "F2", "F3"],
                "default_floor_id": "F1",
                "entry_mapping_reason": "M25C placeholder; verify the real outdoor entry before rollout.",
            }
        ]
    }


def indoor_node(
    *,
    node_id: str,
    name: str,
    category: str,
    floor_id: str,
    x: float,
    y: float,
    is_gate: bool = False,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "name": name,
        "type": category,
        "is_gate": is_gate,
        "sub_graph_id": None,
        "tags": [category, "indoor", "placeholder"],
        "keywords": [category, "indoor", "placeholder"],
        "description": "M25C indoor placeholder; replace with verified floor-plan data.",
        "category": category,
        "facilities": [category],
        "floor_id": floor_id,
        "floor_label": floor_id,
        "layout": {"x": x, "y": y},
        "is_indoor": True,
    }


def indoor_edge(source: str, target: str, distance: float, edge_type: str = "indoor_walkway") -> dict[str, Any]:
    return {
        "from": source,
        "to": target,
        "distance": distance,
        "name": f"{source} to {target}",
        "description": "M25C indoor scaffold edge.",
        "type": edge_type,
        "congestion": 1.0,
        "ideal_speed": 1.0,
        "vehicle_access": "pedestrian_only",
        "allowed_transports": ["walk"],
        "transport_speeds": {"walk": 1.0},
    }


def build_indoor_graph(config: ScaffoldConfig) -> dict[str, Any]:
    building_id = config.indoor_building_id
    building_name = config.indoor_building_name
    gate_id = indoor_gate_node_id(building_id)
    service_id = f"{building_id}_service_f1"
    stairs_f1_id = f"{building_id}_stairs_f1"
    room_f1_id = f"{building_id}_room_f1"
    room_f2_id = f"{building_id}_room_f2"
    room_f3_id = f"{building_id}_room_f3"
    nodes = [
        indoor_node(node_id=gate_id, name=f"{building_name} Indoor Gate", category="hall", floor_id="F1", x=60, y=240, is_gate=True),
        indoor_node(node_id=service_id, name=f"{building_name} Service Placeholder", category="service", floor_id="F1", x=150, y=180),
        indoor_node(node_id=stairs_f1_id, name=f"{building_name} Stairs Placeholder", category="stairs", floor_id="F1", x=240, y=240),
        indoor_node(node_id=room_f1_id, name=f"{building_name} F1 Room Placeholder", category="service", floor_id="F1", x=150, y=320),
        indoor_node(node_id=room_f2_id, name=f"{building_name} F2 Room Placeholder", category="education", floor_id="F2", x=150, y=220),
        indoor_node(node_id=room_f3_id, name=f"{building_name} F3 Room Placeholder", category="education", floor_id="F3", x=150, y=220),
    ]
    edges = [
        indoor_edge(gate_id, service_id, 12),
        indoor_edge(service_id, gate_id, 12),
        indoor_edge(gate_id, stairs_f1_id, 18),
        indoor_edge(stairs_f1_id, gate_id, 18),
        indoor_edge(service_id, room_f1_id, 14),
        indoor_edge(room_f1_id, service_id, 14),
        indoor_edge(stairs_f1_id, room_f2_id, 20, "stairs"),
        indoor_edge(room_f2_id, stairs_f1_id, 20, "stairs"),
        indoor_edge(room_f2_id, room_f3_id, 20, "stairs"),
        indoor_edge(room_f3_id, room_f2_id, 20, "stairs"),
    ]
    return {
        "graph_id": f"{config.site_id}_{resolve_indoor_graph_id(config)}",
        "graph_type": "indoor",
        "building_id": building_id,
        "building_name": building_name,
        "template_id": config.indoor_template_id,
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
        "metadata": {
            "stage": "M25C",
            "scaffold": True,
            "notes": "Template-only indoor graph. Replace layout, rooms, and edges with verified building data.",
        },
        "nodes": nodes,
        "edges": edges,
    }


def build_global_site_entry(config: ScaffoldConfig) -> dict[str, Any]:
    sub_graphs = ["outdoor"]
    if config.with_indoor_placeholder:
        sub_graphs.append(resolve_indoor_graph_id(config))
    return {
        "id": config.site_id,
        "name": config.site_name,
        "description": config.description,
        "location": config.location,
        "sub_graphs": sub_graphs,
    }


def build_readme(config: ScaffoldConfig) -> str:
    indoor_line = (
        f"- Indoor placeholder graph: {resolve_indoor_graph_id(config)}.json\n"
        if config.with_indoor_placeholder
        else "- Indoor graph: not generated; registry is intentionally empty.\n"
    )
    return (
        f"# {config.site_id} M25C Scaffold\n\n"
        "This directory was generated by `scripts/scaffold_new_campus.py`.\n\n"
        "Next steps before using it as real campus data:\n\n"
        "1. Replace placeholder coordinates, names, descriptions, and facilities with verified local data.\n"
        "2. Check every edge endpoint and distance; add reverse edges only where travel is truly bidirectional.\n"
        "3. Merge `global_sites_entry.json` into `data/global_sites.json` only after `outdoor.json` is ready.\n"
        "4. Treat files under `geo/` as placeholders until offline map extraction or matching is performed.\n"
        f"{indoor_line}"
    )


def planned_outputs(config: ScaffoldConfig) -> list[Path]:
    site_dir = config.data_root / "sites" / config.site_id
    geo_dir = site_dir / "geo"
    outputs = [
        site_dir / "outdoor.json",
        site_dir / "global_sites_entry.json",
        site_dir / "README.md",
        geo_dir / "osm_roads_simplified.geojson",
        geo_dir / "osm_buildings.geojson",
        geo_dir / "osm_water_landuse.geojson",
        geo_dir / "edge_osm_geometry_matches.json",
        geo_dir / "osm_extract_metadata.json",
        geo_dir / "indoor_building_registry.json",
        geo_dir / "indoor_template_catalog.json",
    ]
    if config.with_indoor_placeholder:
        outputs.append(site_dir / f"{resolve_indoor_graph_id(config)}.json")
    return outputs


def scaffold_site(config: ScaffoldConfig) -> list[Path]:
    site_dir = config.data_root / "sites" / config.site_id
    geo_dir = site_dir / "geo"
    outputs = planned_outputs(config)

    if config.dry_run:
        print("Planned files:")
        for path in outputs:
            print(f"- {path}")
        print("\nSuggested global_sites entry:")
        print(json.dumps(build_global_site_entry(config), ensure_ascii=False, indent=2))
        return outputs

    site_dir.mkdir(parents=True, exist_ok=True)
    geo_dir.mkdir(parents=True, exist_ok=True)

    json_dump(build_outdoor_graph(config), site_dir / "outdoor.json", overwrite=config.overwrite)
    json_dump(build_global_site_entry(config), site_dir / "global_sites_entry.json", overwrite=config.overwrite)

    readme_path = site_dir / "README.md"
    if readme_path.exists() and not config.overwrite:
        raise FileExistsError(f"refusing to overwrite existing file: {readme_path}")
    readme_path.write_text(build_readme(config), encoding="utf-8")

    for name in [
        "osm_roads_simplified.geojson",
        "osm_buildings.geojson",
        "osm_water_landuse.geojson",
    ]:
        json_dump(empty_feature_collection(), geo_dir / name, overwrite=config.overwrite)

    json_dump(
        {
            "metadata": {
                "site_id": config.site_id,
                "stage": "M25C",
                "placeholder": True,
                "notes": "No OSM edge matches yet. Later stages should populate this from offline matching.",
            },
            "matches": [],
        },
        geo_dir / "edge_osm_geometry_matches.json",
        overwrite=config.overwrite,
    )
    json_dump(
        {
            "site_id": config.site_id,
            "stage": "M25C",
            "placeholder": True,
            "source": "not_extracted",
            "notes": "Placeholder metadata for later offline OSM extraction.",
        },
        geo_dir / "osm_extract_metadata.json",
        overwrite=config.overwrite,
    )
    json_dump(build_indoor_registry(config), geo_dir / "indoor_building_registry.json", overwrite=config.overwrite)
    json_dump(build_indoor_template_catalog(), geo_dir / "indoor_template_catalog.json", overwrite=config.overwrite)

    if config.with_indoor_placeholder:
        json_dump(
            build_indoor_graph(config),
            site_dir / f"{resolve_indoor_graph_id(config)}.json",
            overwrite=config.overwrite,
        )

    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an M25C new-campus scaffold without creating real campus data.",
    )
    parser.add_argument("--site-id", required=True, help="New site id, e.g. THU or WHU.")
    parser.add_argument("--site-name", required=True, help="Display name for the new site.")
    parser.add_argument("--location", default="", help="City or address text for global_sites entry.")
    parser.add_argument("--description", default="", help="Short description for global_sites entry.")
    parser.add_argument("--center-lat", required=True, type=float, help="Approximate campus center latitude.")
    parser.add_argument("--center-lng", required=True, type=float, help="Approximate campus center longitude.")
    parser.add_argument(
        "--data-root",
        default=Path("data"),
        type=Path,
        help="Data root containing sites/. Defaults to ./data.",
    )
    parser.add_argument(
        "--with-indoor-placeholder",
        action="store_true",
        help="Also generate one generic indoor graph plus registry entry.",
    )
    parser.add_argument("--indoor-building-id", default="library", help="Outdoor node used as indoor entry.")
    parser.add_argument("--indoor-building-name", default="Library Placeholder", help="Indoor placeholder name.")
    parser.add_argument("--indoor-graph-id", default=None, help="Indoor graph stem, must start with indoor_.")
    parser.add_argument("--indoor-template-id", default="library_service_v1", help="Indoor template id.")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting generated files.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned outputs without writing files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    site_id = normalize_site_id(args.site_id)
    description = args.description or f"{args.site_name} scaffold generated from the M25C template."
    config = ScaffoldConfig(
        site_id=site_id,
        site_name=args.site_name,
        location=args.location,
        description=description,
        center_lat=args.center_lat,
        center_lng=args.center_lng,
        data_root=args.data_root,
        with_indoor_placeholder=args.with_indoor_placeholder,
        indoor_building_id=args.indoor_building_id,
        indoor_building_name=args.indoor_building_name,
        indoor_graph_id=args.indoor_graph_id,
        indoor_template_id=args.indoor_template_id,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    outputs = scaffold_site(config)
    if not args.dry_run:
        print(f"Generated {len(outputs)} scaffold files for {site_id} under {config.data_root}.")
        print(f"Merge {config.data_root / 'sites' / site_id / 'global_sites_entry.json'} manually when ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
