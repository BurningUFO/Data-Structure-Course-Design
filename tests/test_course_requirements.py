"""
第十一周课程硬指标核验入口。

本脚本采用课程硬指标强断言：
- 10+ 用户、10+ 日记作者、必要文档、AIGC / 媒体占位样例。
- 200+ 扩展推荐 / 查询对象、50+ 服务设施、200+ 道路边。

使用说明：
  python -B tests/test_course_requirements.py
"""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"
WEEK11_DIR = PROJECT_ROOT / "工作进度" / "第十一周"

USERS_PATH = DATA_DIR / "users.json"
DIARY_PATH = DATA_DIR / "diary_data.json"
AIGC_SAMPLES_PATH = DATA_DIR / "aigc_media_samples.json"
MEMBER_C_SCENIC_PATH = DATA_DIR / "成员Cdata" / "scenic_spots.json"
PKU_SITE_DIR = DATA_DIR / "sites" / "PKU"

REQUIRED_DOC_PATHS = [
    DOCS_DIR / "课程要求覆盖清单.md",
    DOCS_DIR / "数据字典.md",
    DOCS_DIR / "用户使用说明.md",
    DOCS_DIR / "评价和改进意见.md",
    DOCS_DIR / "AI辅助开发能力分析.md",
    WEEK11_DIR / "memberC第11周课程硬指标核验记录.md",
    WEEK11_DIR / "memberC第11周工作内容陈述.md",
]

SERVICE_CATEGORY_SET = {
    "catering",
    "shopping",
    "sports",
    "restroom",
    "parking",
    "service",
    "hall",
    "reading_room",
    "dormitory",
    "education",
    "landmark",
    "entrance",
    # Map Plan B M10/M11 replaces the old virtual service grid with real
    # road/footway waypoints, so these remain part of the course-scale service surface.
    "road",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_pku_graph_payloads() -> list[dict]:
    payloads: list[dict] = []
    for path in sorted(PKU_SITE_DIR.glob("*.json")):
        payloads.append(load_json(path))
    return payloads


def collect_pku_nodes_and_edges() -> tuple[list[dict], list[dict]]:
    nodes: list[dict] = []
    edges: list[dict] = []
    for payload in load_pku_graph_payloads():
        nodes.extend(payload.get("nodes", []))
        edges.extend(payload.get("edges", []))
    return nodes, edges


def test_user_samples_reach_course_minimum():
    users = load_json(USERS_PATH)
    diaries = load_json(DIARY_PATH)

    user_ids = {str(user.get("id", "")).strip() for user in users}
    diary_author_ids = {
        str(diary.get("author_id", "")).strip()
        for diary in diaries
        if str(diary.get("author_id", "")).strip()
    }

    assert len(users) >= 10
    assert len(user_ids) >= 10
    assert len(diary_author_ids) >= 10
    assert diary_author_ids.issubset(user_ids)
    for user in users:
        assert user.get("id")
        assert user.get("name")
        assert isinstance(user.get("interests", []), list)

    print(
        "test_user_samples_reach_course_minimum passed: "
        f"users={len(users)}, diary_authors={len(diary_author_ids)}"
    )


def test_aigc_and_media_placeholders_ready():
    diaries = load_json(DIARY_PATH)
    samples = load_json(AIGC_SAMPLES_PATH)
    diaries_by_id = {diary["id"]: diary for diary in diaries}
    diaries_with_images = [
        diary for diary in diaries if isinstance(diary.get("images"), list) and diary["images"]
    ]

    assert len(samples) >= 3
    assert len(diaries_with_images) >= 3
    for sample in samples:
        diary_id = sample.get("diary_id")
        assert sample.get("sample_id")
        assert diary_id in diaries_by_id
        assert sample.get("image_placeholder")
        assert sample.get("text_prompt")
        assert sample.get("preview_placeholder")
        assert sample.get("status") == "placeholder_ready"
        assert sample["image_placeholder"] in diaries_by_id[diary_id].get("images", [])

    print(
        "test_aigc_and_media_placeholders_ready passed: "
        f"samples={len(samples)}, media_diaries={len(diaries_with_images)}"
    )


def test_required_course_documents_exist():
    for path in REQUIRED_DOC_PATHS:
        assert path.exists(), f"missing required document: {path}"
        assert path.read_text(encoding="utf-8").strip(), f"empty required document: {path}"

    print(f"test_required_course_documents_exist passed: docs={len(REQUIRED_DOC_PATHS)}")


def test_current_scale_snapshot_for_week12_gap_tracking():
    nodes, edges = collect_pku_nodes_and_edges()
    node_ids = [str(node.get("id", "")).strip() for node in nodes]
    edge_endpoint_ids = {
        str(edge.get(endpoint, "")).strip()
        for edge in edges
        for endpoint in ("from", "to")
    }
    categories = {
        str(node.get("category", node.get("type", ""))).strip()
        for node in nodes
        if str(node.get("category", node.get("type", ""))).strip()
    }
    facility_like_nodes = [
        node
        for node in nodes
        if str(node.get("category", node.get("type", ""))).strip() in SERVICE_CATEGORY_SET
    ]
    extension_records = load_json(MEMBER_C_SCENIC_PATH)
    extension_ids = [str(record.get("id", "")).strip() for record in extension_records]
    mapped_extension_records = [
        record for record in extension_records if record.get("map_node_id")
    ]
    osm_roads = load_json(PKU_SITE_DIR / "geo" / "osm_roads_simplified.geojson")
    osm_road_features = osm_roads.get("features", [])

    assert len(nodes) >= 50
    assert len(categories) >= 10
    assert len(facility_like_nodes) >= 50
    assert len(edges) >= 120
    assert len(osm_road_features) >= 200
    assert len(node_ids) == len(set(node_ids))
    assert edge_endpoint_ids.issubset(set(node_ids))
    assert len(extension_records) >= 200
    assert len(extension_ids) == len(set(extension_ids))
    assert len(mapped_extension_records) >= 5
    for record in extension_records:
        assert record.get("name")
        assert record.get("category")
        assert isinstance(record.get("tags", []), list)
        assert isinstance(record.get("keywords", []), list)

    print("test_current_scale_snapshot_for_week12_gap_tracking passed:")
    print(f"  pku_nodes={len(nodes)}")
    print(f"  pku_edges={len(edges)}")
    print(f"  local_osm_road_features={len(osm_road_features)}")
    print(f"  pku_categories={len(categories)}")
    print(f"  facility_like_nodes={len(facility_like_nodes)}")
    print(f"  extension_objects={len(extension_records)}")
    print(f"  mapped_extension_objects={len(mapped_extension_records)}")


def run_all_tests():
    print("Running course requirement checks...")
    test_user_samples_reach_course_minimum()
    test_aigc_and_media_placeholders_ready()
    test_required_course_documents_exist()
    test_current_scale_snapshot_for_week12_gap_tracking()
    print("All course requirement checks passed.")


if __name__ == "__main__":
    run_all_tests()
