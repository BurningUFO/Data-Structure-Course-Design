from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from src.graph.loader import GraphLoader


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "scaffold_new_campus.py"


def load_scaffold_module():
    spec = importlib.util.spec_from_file_location("scaffold_new_campus", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_global_sites_from_snippet(data_root: Path, site_id: str) -> dict:
    entry_path = data_root / "sites" / site_id / "global_sites_entry.json"
    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    (data_root / "global_sites.json").write_text(
        json.dumps({"sites": [entry]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return entry


def test_scaffold_generates_outdoor_and_geo_placeholders(tmp_path):
    scaffold = load_scaffold_module()
    data_root = tmp_path / "data"
    config = scaffold.ScaffoldConfig(
        site_id="TEMPLATE",
        site_name="Template Campus",
        location="Template City",
        description="Template campus scaffold.",
        center_lat=39.0,
        center_lng=116.0,
        data_root=data_root,
    )

    outputs = scaffold.scaffold_site(config)

    site_dir = data_root / "sites" / "TEMPLATE"
    geo_dir = site_dir / "geo"
    assert site_dir / "outdoor.json" in outputs
    assert (site_dir / "outdoor.json").exists()
    assert (site_dir / "global_sites_entry.json").exists()
    assert (site_dir / "README.md").exists()
    assert (geo_dir / "osm_roads_simplified.geojson").exists()
    assert (geo_dir / "osm_buildings.geojson").exists()
    assert (geo_dir / "osm_water_landuse.geojson").exists()
    assert (geo_dir / "edge_osm_geometry_matches.json").exists()
    assert (geo_dir / "osm_extract_metadata.json").exists()
    assert (geo_dir / "indoor_building_registry.json").exists()
    assert (geo_dir / "indoor_template_catalog.json").exists()

    outdoor = json.loads((site_dir / "outdoor.json").read_text(encoding="utf-8"))
    assert outdoor["graph_id"] == "TEMPLATE_outdoor"
    assert outdoor["graph_type"] == "outdoor"
    assert outdoor["metadata"]["stage"] == "M25C"
    node_ids = {node["id"] for node in outdoor["nodes"]}
    assert {"gate_north", "library", "canteen", "road_core"} <= node_ids
    assert all("from" in edge and "to" in edge and edge["distance"] > 0 for edge in outdoor["edges"])
    assert all(edge["geometry"][0]["lat"] and edge["geometry"][0]["lng"] for edge in outdoor["edges"])

    entry = write_global_sites_from_snippet(data_root, "TEMPLATE")
    assert entry["sub_graphs"] == ["outdoor"]

    roads = json.loads((geo_dir / "osm_roads_simplified.geojson").read_text(encoding="utf-8"))
    assert roads == {"type": "FeatureCollection", "features": []}
    registry = json.loads((geo_dir / "indoor_building_registry.json").read_text(encoding="utf-8"))
    assert registry == {"buildings": []}
    catalog = json.loads((geo_dir / "indoor_template_catalog.json").read_text(encoding="utf-8"))
    assert {item["template_id"] for item in catalog["templates"]} >= {"library_service_v1", "teaching_block_v1"}

    graph = GraphLoader.load_site_graph("TEMPLATE", data_root=data_root)
    assert set(graph.nodes) == node_ids
    assert any(edge["to"] == "road_north" for edge in graph.adj["gate_north"])


def test_scaffold_with_indoor_placeholder_links_loader_gate(tmp_path):
    scaffold = load_scaffold_module()
    data_root = tmp_path / "data"
    config = scaffold.ScaffoldConfig(
        site_id="TEMPLATE",
        site_name="Template Campus",
        location="Template City",
        description="Template campus scaffold.",
        center_lat=39.0,
        center_lng=116.0,
        data_root=data_root,
        with_indoor_placeholder=True,
        indoor_building_id="library",
        indoor_building_name="Library Placeholder",
    )

    scaffold.scaffold_site(config)
    entry = write_global_sites_from_snippet(data_root, "TEMPLATE")

    site_dir = data_root / "sites" / "TEMPLATE"
    indoor_path = site_dir / "indoor_LIBRARY.json"
    assert entry["sub_graphs"] == ["outdoor", "indoor_LIBRARY"]
    assert indoor_path.exists()

    outdoor = json.loads((site_dir / "outdoor.json").read_text(encoding="utf-8"))
    library = next(node for node in outdoor["nodes"] if node["id"] == "library")
    assert library["sub_graph_id"] == "indoor_LIBRARY"
    assert library["indoor_supported"] is True
    assert library["indoor_entry_node_id"] == "library_indoor_gate"

    registry = json.loads((site_dir / "geo" / "indoor_building_registry.json").read_text(encoding="utf-8"))
    assert registry["buildings"][0]["entry_node_id"] == "library"
    assert registry["buildings"][0]["indoor_graph_id"] == "indoor_LIBRARY"

    indoor = json.loads(indoor_path.read_text(encoding="utf-8"))
    indoor_ids = {node["id"] for node in indoor["nodes"]}
    outdoor_ids = {node["id"] for node in outdoor["nodes"]}
    assert "library_indoor_gate" in indoor_ids
    assert outdoor_ids.isdisjoint(indoor_ids)
    assert any(node["is_gate"] for node in indoor["nodes"])

    graph = GraphLoader.load_site_graph("TEMPLATE", data_root=data_root)
    assert "library_indoor_gate" in graph.nodes
    assert any(
        edge["to"] == "library_indoor_gate" and edge["type"] == "gate_link"
        for edge in graph.adj["library"]
    )
    assert any(
        edge["to"] == "library" and edge["type"] == "gate_link"
        for edge in graph.adj["library_indoor_gate"]
    )


def test_scaffold_refuses_existing_files_without_overwrite(tmp_path):
    scaffold = load_scaffold_module()
    config = scaffold.ScaffoldConfig(
        site_id="TEMPLATE",
        site_name="Template Campus",
        location="Template City",
        description="Template campus scaffold.",
        center_lat=39.0,
        center_lng=116.0,
        data_root=tmp_path / "data",
    )

    scaffold.scaffold_site(config)

    with pytest.raises(FileExistsError):
        scaffold.scaffold_site(config)


def test_scaffold_validates_site_id():
    scaffold = load_scaffold_module()

    assert scaffold.normalize_site_id("template_1") == "TEMPLATE_1"
    with pytest.raises(ValueError):
        scaffold.normalize_site_id("bad-site")
