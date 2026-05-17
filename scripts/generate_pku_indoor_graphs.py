from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PKU_DIR = DATA_DIR / "sites" / "PKU"
GEO_DIR = PKU_DIR / "geo"
GLOBAL_SITES_PATH = DATA_DIR / "global_sites.json"
OUTDOOR_PATH = PKU_DIR / "outdoor.json"


TEMPLATE_CATALOG = [
    {
        "template_id": "teaching_block_v1",
        "template_name": "教学 / 实验楼模板",
        "recommended_building_types": ["teaching", "research", "academy"],
        "default_floor_count": 3,
        "required_zone_types": ["restroom", "elevator", "stairs", "education", "service"],
    },
    {
        "template_id": "library_service_v1",
        "template_name": "图书馆 / 综合服务楼模板",
        "recommended_building_types": ["library", "archive", "service_center"],
        "default_floor_count": 3,
        "required_zone_types": ["restroom", "elevator", "stairs", "reading_room", "service"],
    },
    {
        "template_id": "dormitory_v1",
        "template_name": "宿舍模板",
        "recommended_building_types": ["dormitory", "residence"],
        "default_floor_count": 3,
        "required_zone_types": ["restroom", "elevator", "stairs", "dormitory", "service"],
    },
    {
        "template_id": "canteen_service_v1",
        "template_name": "食堂 / 生活服务楼模板",
        "recommended_building_types": ["canteen", "lifestyle_service"],
        "default_floor_count": 2,
        "required_zone_types": ["restroom", "elevator", "stairs", "catering", "service"],
    },
    {
        "template_id": "sports_public_v1",
        "template_name": "体育 / 大型公共建筑模板",
        "recommended_building_types": ["sports", "public"],
        "default_floor_count": 3,
        "required_zone_types": ["restroom", "elevator", "stairs", "sports", "service"],
    },
]


BUILDINGS = [
    {
        "building_id": "library",
        "building_name": "图书馆",
        "graph_file": "indoor_LIB",
        "template_id": "library_service_v1",
        "builder": "library",
        "prefix": "lib",
        "entry_node_id": "library",
        "entry_reason": "复用现有 is_gate=true 建筑节点作为唯一室内外入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "teaching_building_1",
        "building_name": "第一教学楼",
        "graph_file": "indoor_TB1",
        "template_id": "teaching_block_v1",
        "builder": "teaching",
        "profile": "teaching",
        "prefix": "tb1",
        "entry_node_id": "teaching_building_1",
        "entry_reason": "复用现有 is_gate=true 建筑节点作为唯一室内外入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "teaching_building_2",
        "building_name": "第二教学楼",
        "graph_file": "indoor_TB2",
        "template_id": "teaching_block_v1",
        "builder": "teaching",
        "profile": "teaching",
        "prefix": "tb2",
        "entry_node_id": "teaching_building_2",
        "entry_reason": "复用现有 is_gate=true 建筑节点作为唯一室内外入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "dormitory_1",
        "building_name": "学生宿舍31楼",
        "graph_file": "indoor_DORM1",
        "template_id": "dormitory_v1",
        "builder": "dormitory",
        "prefix": "dorm1",
        "entry_node_id": "dormitory_1",
        "entry_reason": "复用现有 is_gate=true 建筑节点作为唯一室内外入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_building_way_295071478",
        "building_name": "北京大学化学学院A区",
        "graph_file": "indoor_CHEM_A",
        "template_id": "teaching_block_v1",
        "builder": "teaching",
        "profile": "research",
        "prefix": "chem_a",
        "entry_node_id": "poi_door_way_295071478_north",
        "entry_reason": "优先复用 poi_door 节点中的北门作为唯一室内外入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_building_way_295071692",
        "building_name": "北京大学化学学院B区",
        "graph_file": "indoor_CHEM_B",
        "template_id": "teaching_block_v1",
        "builder": "teaching",
        "profile": "research",
        "prefix": "chem_b",
        "entry_node_id": "poi_door_way_295071692_south",
        "entry_reason": "优先复用 poi_door 节点中的南门作为唯一室内外入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_building_way_295072178",
        "building_name": "北京大学化学学院C区",
        "graph_file": "indoor_CHEM_C",
        "template_id": "teaching_block_v1",
        "builder": "teaching",
        "profile": "research",
        "prefix": "chem_c",
        "entry_node_id": "poi_door_way_295072178_north",
        "entry_reason": "优先复用 poi_door 节点中的北门作为唯一室内外入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_building_way_295073722",
        "building_name": "北京大学化学学院D区",
        "graph_file": "indoor_CHEM_D",
        "template_id": "teaching_block_v1",
        "builder": "teaching",
        "profile": "research",
        "prefix": "chem_d",
        "entry_node_id": "poi_door_way_295073722_west",
        "entry_reason": "优先复用 poi_door 节点中的西门作为唯一室内外入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_building_way_392552195",
        "building_name": "北京大学-加速器楼",
        "graph_file": "indoor_ACCEL",
        "template_id": "teaching_block_v1",
        "builder": "teaching",
        "profile": "research",
        "prefix": "accel",
        "entry_node_id": "poi_door_way_392552195_east",
        "entry_reason": "优先复用 poi_door 节点中的东门作为唯一室内外入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_building_way_392563329",
        "building_name": "北京大学-燕东园小楼31号楼",
        "graph_file": "indoor_YDY31",
        "template_id": "dormitory_v1",
        "builder": "dormitory",
        "prefix": "ydy31",
        "entry_node_id": "poi_door_way_392563329_north",
        "entry_reason": "优先复用 poi_door 节点中的北门作为唯一室内外入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_building_way_392563327",
        "building_name": "北京大学-燕东园小楼32号楼",
        "graph_file": "indoor_YDY32",
        "template_id": "dormitory_v1",
        "builder": "dormitory",
        "prefix": "ydy32",
        "entry_node_id": "poi_door_way_392563327_north",
        "entry_reason": "优先复用 poi_door 节点中的北门作为唯一室内外入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_education_way_866277614",
        "building_name": "北京大学工学院",
        "graph_file": "indoor_ENGINEERING",
        "template_id": "teaching_block_v1",
        "builder": "teaching",
        "profile": "research",
        "prefix": "engineering",
        "entry_node_id": "poi_osm_education_way_866277614",
        "entry_reason": "缺少可用 poi_door 节点，回退复用建筑节点作为唯一入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_building_way_866277616",
        "building_name": "北京大学城市与环境学院",
        "graph_file": "indoor_URBAN_ENV",
        "template_id": "teaching_block_v1",
        "builder": "teaching",
        "profile": "research",
        "prefix": "urban_env",
        "entry_node_id": "poi_osm_building_way_866277616",
        "entry_reason": "缺少可稳定绑定的本楼门节点，回退复用建筑节点作为唯一入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_education_node_11135733624",
        "building_name": "数学科学学院",
        "graph_file": "indoor_MATH",
        "template_id": "teaching_block_v1",
        "builder": "teaching",
        "profile": "teaching",
        "prefix": "math",
        "entry_node_id": "poi_osm_education_node_11135733624",
        "entry_reason": "缺少独立门节点，回退复用建筑节点作为唯一入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_education_way_628032101",
        "building_name": "阿卜杜勒·阿齐兹国王公共图书馆北京大学分馆（古籍图书馆）",
        "graph_file": "indoor_ANCIENT_LIB",
        "template_id": "library_service_v1",
        "builder": "library",
        "prefix": "ancient_lib",
        "entry_node_id": "poi_osm_education_way_628032101",
        "entry_reason": "缺少独立门节点，回退复用建筑节点作为唯一入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
        "profile": "archive",
    },
    {
        "building_id": "poi_osm_sports_way_33457546",
        "building_name": "邱德拔体育馆",
        "graph_file": "indoor_QDB_SPORTS",
        "template_id": "sports_public_v1",
        "builder": "sports",
        "prefix": "qdb_sports",
        "entry_node_id": "poi_osm_sports_way_33457546",
        "entry_reason": "缺少独立门节点，回退复用建筑节点作为唯一入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_sports_way_240832253",
        "building_name": "五四体育中心",
        "graph_file": "indoor_WUSI_SPORTS",
        "template_id": "sports_public_v1",
        "builder": "sports",
        "prefix": "wusi_sports",
        "entry_node_id": "poi_osm_sports_way_240832253",
        "entry_reason": "缺少独立门节点，回退复用建筑节点作为唯一入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2", "F3"],
    },
    {
        "building_id": "poi_osm_catering_way_444894329",
        "building_name": "餐饮综合楼（家园食堂）",
        "graph_file": "indoor_CANTEEN_JIAYUAN",
        "template_id": "canteen_service_v1",
        "builder": "canteen",
        "prefix": "jiayuan",
        "entry_node_id": "poi_osm_catering_way_444894329",
        "entry_reason": "缺少独立门节点，回退复用建筑节点作为唯一入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2"],
    },
    {
        "building_id": "poi_osm_catering_way_372945805",
        "building_name": "学一食堂",
        "graph_file": "indoor_CANTEEN_XUEYI",
        "template_id": "canteen_service_v1",
        "builder": "canteen",
        "prefix": "xueyi",
        "entry_node_id": "poi_osm_catering_way_372945805",
        "entry_reason": "缺少独立门节点，回退复用建筑节点作为唯一入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2"],
    },
    {
        "building_id": "poi_osm_catering_way_446944417",
        "building_name": "燕南食堂",
        "graph_file": "indoor_CANTEEN_YANNAN",
        "template_id": "canteen_service_v1",
        "builder": "canteen",
        "prefix": "yannan",
        "entry_node_id": "poi_osm_catering_way_446944417",
        "entry_reason": "缺少独立门节点，回退复用建筑节点作为唯一入口。",
        "default_floor_id": "F1",
        "floor_ids": ["F1", "F2"],
    },
]


TEACHING_PROFILE_ZONES = {
    "teaching": {
        "F1": [
            ("service_desk", "教学服务台", "service", "service"),
            ("classroom_101", "101 教室", "classroom", "education"),
            ("classroom_102", "102 教室", "classroom", "education"),
            ("study_corner_1f", "共享学习区", "service", "service"),
        ],
        "F2": [
            ("classroom_201", "201 教室", "classroom", "education"),
            ("classroom_202", "202 教室", "classroom", "education"),
            ("seminar_room_2f", "研讨室", "service", "education"),
            ("faculty_office_2f", "教师办公室", "service", "service"),
        ],
        "F3": [
            ("classroom_301", "301 教室", "classroom", "education"),
            ("innovation_room_3f", "创新教室", "service", "education"),
            ("meeting_room_3f", "会议室", "service", "service"),
            ("rest_area_3f", "休息区", "service", "service"),
        ],
    },
    "research": {
        "F1": [
            ("service_desk", "门厅服务台", "service", "service"),
            ("lab_101", "101 实验室", "service", "education"),
            ("sample_room_1f", "样品准备室", "service", "service"),
            ("duty_room_1f", "值班室", "service", "service"),
        ],
        "F2": [
            ("lab_201", "201 实验室", "service", "education"),
            ("instrument_room_2f", "仪器平台", "service", "service"),
            ("office_2f", "研究办公室", "service", "service"),
            ("meeting_room_2f", "学术讨论室", "service", "education"),
        ],
        "F3": [
            ("lab_301", "301 实验室", "service", "education"),
            ("analysis_room_3f", "分析室", "service", "education"),
            ("archive_room_3f", "资料室", "service", "service"),
            ("tea_room_3f", "休息交流区", "service", "service"),
        ],
    },
}


LIBRARY_PROFILE_ZONES = {
    "default": {
        "F1": [
            ("reception", "总服务台", "service", "service"),
            ("reading_room_1", "中文社科阅览室", "reading_room", "reading_room"),
            ("self_serve", "自助借还区", "service", "service"),
            ("cafe", "图书馆咖啡厅", "service", "catering"),
        ],
        "F2": [
            ("reading_room_2", "自然科学阅览室", "reading_room", "reading_room"),
            ("digital_room_2f", "数字阅览区", "reading_room", "reading_room"),
            ("group_room_2f", "小组研讨室", "service", "education"),
            ("consult_room_2f", "咨询服务室", "service", "service"),
        ],
        "F3": [
            ("archive_room_3f", "馆藏资料室", "service", "service"),
            ("quiet_room_3f", "安静自习区", "reading_room", "reading_room"),
            ("reference_room_3f", "参考咨询区", "service", "service"),
            ("rest_area_3f", "休息区", "service", "service"),
        ],
    },
    "archive": {
        "F1": [
            ("reception", "古籍服务台", "service", "service"),
            ("reading_room_1", "古籍阅览室", "reading_room", "reading_room"),
            ("self_serve", "预约取书区", "service", "service"),
            ("cafe", "学术休息角", "service", "catering"),
        ],
        "F2": [
            ("reading_room_2", "善本阅览室", "reading_room", "reading_room"),
            ("digital_room_2f", "数字检索室", "reading_room", "reading_room"),
            ("group_room_2f", "学术讨论室", "service", "education"),
            ("consult_room_2f", "编目咨询室", "service", "service"),
        ],
        "F3": [
            ("archive_room_3f", "古籍修复室", "service", "service"),
            ("quiet_room_3f", "特藏阅览区", "reading_room", "reading_room"),
            ("reference_room_3f", "珍本资料室", "service", "service"),
            ("rest_area_3f", "研究者休息区", "service", "service"),
        ],
    },
}


BASE_LAYOUT = {
    "entry": {"x": 56, "y": 240},
    "hub": {"x": 170, "y": 240},
    "stairs": {"x": 330, "y": 96},
    "elevator": {"x": 330, "y": 176},
    "restroom": {"x": 330, "y": 304},
    "zones": [
        {"x": 112, "y": 96},
        {"x": 112, "y": 176},
        {"x": 112, "y": 304},
        {"x": 244, "y": 96},
        {"x": 244, "y": 304},
    ],
}


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def node(
    *,
    node_id: str,
    name: str,
    node_type: str,
    category: str,
    floor_id: str,
    floor_label: str,
    x: int,
    y: int,
    is_gate: bool = False,
    tags: list[str] | None = None,
    description: str = "",
    facilities: list[str] | None = None,
    location: dict[str, float] | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": node_id,
        "name": name,
        "type": node_type,
        "is_gate": is_gate,
        "sub_graph_id": None,
        "tags": tags or [],
        "description": description,
        "category": category,
        "facilities": facilities or [],
        "floor_id": floor_id,
        "floor_label": floor_label,
        "layout": {"x": x, "y": y},
    }
    if location:
        payload["location"] = location
    if extra:
        payload.update(extra)
    return payload


def add_bidirectional_edge(
    edges: list[dict[str, object]],
    source_id: str,
    target_id: str,
    *,
    distance: float,
    edge_type: str,
    name: str,
    description: str = "",
    vehicle_access: str = "pedestrian_only",
    congestion: float = 1.0,
    ideal_speed: float = 1.5,
) -> None:
    edge = {
        "distance": distance,
        "type": edge_type,
        "congestion": congestion,
        "ideal_speed": ideal_speed,
        "vehicle_access": vehicle_access,
        "name": name,
        "description": description,
    }
    forward = {"from": source_id, "to": target_id}
    forward.update(edge)
    backward = {"from": target_id, "to": source_id}
    backward.update(edge)
    edges.extend([forward, backward])


def build_template_graph(
    *,
    graph_file: str,
    building_name: str,
    building_id: str,
    template_id: str,
    default_floor_id: str,
    floor_ids: list[str],
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "graph_id": f"PKU_{graph_file}",
        "graph_type": "indoor",
        "building_id": building_id,
        "building_name": building_name,
        "template_id": template_id,
        "floor": "1F",
        "default_floor_id": default_floor_id,
        "floor_ids": floor_ids,
        "nodes": nodes,
        "edges": edges,
    }


def build_generic_graph(spec: dict[str, object], entry_location: dict[str, float], zone_map: dict[str, list[tuple[str, str, str, str]]], *, corridor_name: str, entry_name: str, entry_type: str, entry_category: str) -> dict[str, object]:
    prefix = str(spec["prefix"])
    building_name = str(spec["building_name"])
    floor_ids = list(spec["floor_ids"])
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []

    for floor_id in floor_ids:
        floor_label = floor_id.replace("F", "") + "F"
        hub_id = f"{prefix}_corridor_{floor_id.lower()}"
        stairs_id = f"{prefix}_stairs_{floor_id.lower()}"
        elevator_id = f"{prefix}_elevator_{floor_id.lower()}"
        restroom_id = f"{prefix}_restroom_{floor_id.lower()}"

        if floor_id == "F1":
            entry_id = f"{prefix}_entrance"
            nodes.append(
                node(
                    node_id=entry_id,
                    name=entry_name,
                    node_type=entry_type,
                    category=entry_category,
                    floor_id=floor_id,
                    floor_label=floor_label,
                    x=BASE_LAYOUT["entry"]["x"],
                    y=BASE_LAYOUT["entry"]["y"],
                    is_gate=True,
                    tags=[building_name, "入口", floor_label],
                    description=f"{building_name} 的主入口大厅，连接室外主门。",
                    facilities=["导览牌"],
                    location=entry_location,
                )
            )
            add_bidirectional_edge(
                edges,
                entry_id,
                hub_id,
                distance=6,
                edge_type="indoor_path",
                name=f"{building_name}{floor_label} 主走廊",
            )

        nodes.append(
            node(
                node_id=hub_id,
                name=f"{floor_label}{corridor_name}",
                node_type="hall",
                category="passage",
                floor_id=floor_id,
                floor_label=floor_label,
                x=BASE_LAYOUT["hub"]["x"],
                y=BASE_LAYOUT["hub"]["y"],
                tags=[building_name, floor_label, corridor_name],
                description=f"{building_name}{floor_label} 的主通行走廊。",
            )
        )
        nodes.append(
            node(
                node_id=stairs_id,
                name=f"{floor_label}楼梯间",
                node_type="staircase",
                category="passage",
                floor_id=floor_id,
                floor_label=floor_label,
                x=BASE_LAYOUT["stairs"]["x"],
                y=BASE_LAYOUT["stairs"]["y"],
                tags=[building_name, floor_label, "楼梯"],
                description=f"{building_name}{floor_label} 楼梯间。",
                facilities=["楼梯扶手"],
            )
        )
        nodes.append(
            node(
                node_id=elevator_id,
                name=f"{floor_label}电梯",
                node_type="elevator",
                category="passage",
                floor_id=floor_id,
                floor_label=floor_label,
                x=BASE_LAYOUT["elevator"]["x"],
                y=BASE_LAYOUT["elevator"]["y"],
                tags=[building_name, floor_label, "电梯"],
                description=f"{building_name}{floor_label} 电梯厅。",
                facilities=["电梯", "盲文按钮"],
            )
        )
        nodes.append(
            node(
                node_id=restroom_id,
                name=f"{floor_label}洗手间",
                node_type="facility",
                category="restroom",
                floor_id=floor_id,
                floor_label=floor_label,
                x=BASE_LAYOUT["restroom"]["x"],
                y=BASE_LAYOUT["restroom"]["y"],
                tags=[building_name, floor_label, "洗手间"],
                description=f"{building_name}{floor_label} 公共洗手间。",
                facilities=["洗手间", "洗手池"],
                extra={"is_indoor": True, "indoor_building": building_name},
            )
        )

        add_bidirectional_edge(
            edges,
            hub_id,
            stairs_id,
            distance=12,
            edge_type="indoor_path",
            name=f"{floor_label}走廊 -> 楼梯间",
        )
        add_bidirectional_edge(
            edges,
            hub_id,
            elevator_id,
            distance=9,
            edge_type="indoor_path",
            name=f"{floor_label}走廊 -> 电梯",
            vehicle_access="all",
        )
        add_bidirectional_edge(
            edges,
            hub_id,
            restroom_id,
            distance=11,
            edge_type="indoor_path",
            name=f"{floor_label}走廊 -> 洗手间",
        )

        for index, (slug, zone_name, node_type, category) in enumerate(zone_map[floor_id]):
            zone_id = f"{prefix}_{slug}"
            zone_layout = BASE_LAYOUT["zones"][index]
            nodes.append(
                node(
                    node_id=zone_id,
                    name=f"{building_name}{zone_name}",
                    node_type=node_type,
                    category=category,
                    floor_id=floor_id,
                    floor_label=floor_label,
                    x=zone_layout["x"],
                    y=zone_layout["y"],
                    tags=[building_name, floor_label, zone_name],
                    description=f"{building_name}{floor_label} 的{zone_name}。",
                    facilities=[zone_name],
                )
            )
            add_bidirectional_edge(
                edges,
                hub_id,
                zone_id,
                distance=10 + index * 2,
                edge_type="indoor_path",
                name=f"{floor_label}走廊 -> {zone_name}",
            )

    for current_floor, next_floor in zip(floor_ids, floor_ids[1:]):
        add_bidirectional_edge(
            edges,
            f"{prefix}_stairs_{current_floor.lower()}",
            f"{prefix}_stairs_{next_floor.lower()}",
            distance=16,
            edge_type="stairs",
            name=f"{current_floor} -> {next_floor} 楼梯",
        )
        add_bidirectional_edge(
            edges,
            f"{prefix}_elevator_{current_floor.lower()}",
            f"{prefix}_elevator_{next_floor.lower()}",
            distance=12,
            edge_type="elevator",
            name=f"{current_floor} -> {next_floor} 电梯",
            vehicle_access="all",
        )

    return build_template_graph(
        graph_file=str(spec["graph_file"]),
        building_name=str(spec["building_name"]),
        building_id=str(spec["building_id"]),
        template_id=str(spec["template_id"]),
        default_floor_id=str(spec["default_floor_id"]),
        floor_ids=floor_ids,
        nodes=nodes,
        edges=edges,
    )


def build_teaching_graph(spec: dict[str, object], entry_location: dict[str, float]) -> dict[str, object]:
    profile = str(spec.get("profile", "teaching"))
    return build_generic_graph(
        spec,
        entry_location,
        TEACHING_PROFILE_ZONES[profile],
        corridor_name="主走廊",
        entry_name=f"{spec['building_name']}入口大厅",
        entry_type="hall",
        entry_category="hall",
    )


def build_canteen_graph(spec: dict[str, object], entry_location: dict[str, float]) -> dict[str, object]:
    zone_map = {
        "F1": [
            ("service_counter_a", "一层窗口 A", "service", "catering"),
            ("service_counter_b", "一层窗口 B", "service", "catering"),
            ("tray_return_1f", "餐盘回收区", "service", "service"),
            ("condiment_area_1f", "调料自助区", "service", "service"),
        ],
        "F2": [
            ("dining_area_2f", "二层用餐区", "service", "catering"),
            ("coffee_corner_2f", "咖啡休息角", "service", "catering"),
            ("self_service_2f", "自助取餐区", "service", "service"),
            ("office_2f", "后勤办公室", "service", "service"),
        ],
    }
    return build_generic_graph(
        spec,
        entry_location,
        zone_map,
        corridor_name="餐厅主通道",
        entry_name=f"{spec['building_name']}入口大厅",
        entry_type="hall",
        entry_category="hall",
    )


def build_sports_graph(spec: dict[str, object], entry_location: dict[str, float]) -> dict[str, object]:
    zone_map = {
        "F1": [
            ("ticket_desk_1f", "票务服务台", "service", "service"),
            ("locker_room_1f", "更衣室", "service", "sports"),
            ("first_aid_1f", "医务室", "service", "service"),
            ("waiting_area_1f", "等候区", "service", "service"),
        ],
        "F2": [
            ("court_2f", "活动场地", "service", "sports"),
            ("spectator_area_2f", "观赛区", "service", "sports"),
            ("training_room_2f", "训练室", "service", "sports"),
            ("service_room_2f", "器材服务室", "service", "service"),
        ],
        "F3": [
            ("fitness_room_3f", "健身房", "service", "sports"),
            ("studio_3f", "多功能教室", "service", "sports"),
            ("office_3f", "运营办公室", "service", "service"),
            ("rest_area_3f", "休息区", "service", "service"),
        ],
    }
    return build_generic_graph(
        spec,
        entry_location,
        zone_map,
        corridor_name="公共连廊",
        entry_name=f"{spec['building_name']}门厅",
        entry_type="hall",
        entry_category="hall",
    )


def build_library_graph(spec: dict[str, object], entry_location: dict[str, float]) -> dict[str, object]:
    if str(spec["graph_file"]) == "indoor_LIB":
        nodes = [
            node(node_id="lib_entrance", name="图书馆入口大厅", node_type="hall", category="hall", floor_id="F1", floor_label="1F", x=56, y=240, is_gate=True, tags=["图书馆", "大厅", "入口"], description="图书馆主入口大厅，连接室外广场。", facilities=["咨询台", "公告栏", "雨伞架"], location=entry_location),
            node(node_id="lib_reception", name="总服务台", node_type="service", category="service", floor_id="F1", floor_label="1F", x=132, y=160, tags=["服务台", "借还书"], description="图书馆总服务台，提供借还书和咨询服务。", facilities=["借还书终端", "咨询服务"]),
            node(node_id="lib_reading_room_1", name="中文社科阅览室", node_type="reading_room", category="reading_room", floor_id="F1", floor_label="1F", x=132, y=320, tags=["阅览室", "社会科学", "中文"], description="中文社会科学类图书阅览室。", facilities=["阅览座位", "电源插座", "WiFi"]),
            node(node_id="lib_cafe", name="图书馆咖啡厅", node_type="service", category="catering", floor_id="F1", floor_label="1F", x=244, y=320, tags=["咖啡", "休息", "轻食"], description="图书馆内咖啡厅，提供咖啡和轻食。", facilities=["吧台", "座位", "充电座"]),
            node(node_id="lib_toilet_1f", name="一楼洗手间", node_type="facility", category="restroom", floor_id="F1", floor_label="1F", x=332, y=304, tags=["洗手间"], description="图书馆一楼公共洗手间。", facilities=["洗手间", "无障碍卫生间"], extra={"is_indoor": True, "indoor_building": "图书馆"}),
            node(node_id="lib_staircase", name="楼梯间", node_type="staircase", category="passage", floor_id="F1", floor_label="1F", x=332, y=96, tags=["楼梯"], description="图书馆主楼梯，连接各楼层。", facilities=["楼梯扶手"]),
            node(node_id="lib_elevator", name="电梯", node_type="elevator", category="passage", floor_id="F1", floor_label="1F", x=332, y=176, tags=["电梯", "无障碍"], description="图书馆电梯，可达各楼层。", facilities=["电梯", "盲文按钮"]),
            node(node_id="lib_self_serve", name="自助借还区", node_type="service", category="service", floor_id="F1", floor_label="1F", x=244, y=160, tags=["自助", "借还书"], description="自助借还书区域，可用校园卡自助操作。", facilities=["自助借还机", "查询终端"]),
            node(node_id="lib_staircase_f2", name="二楼楼梯间", node_type="staircase", category="passage", floor_id="F2", floor_label="2F", x=332, y=96, tags=["楼梯"], description="图书馆二楼楼梯间。", facilities=["楼梯扶手"]),
            node(node_id="lib_elevator_f2", name="二楼电梯", node_type="elevator", category="passage", floor_id="F2", floor_label="2F", x=332, y=176, tags=["电梯"], description="图书馆二楼电梯厅。", facilities=["电梯", "盲文按钮"]),
            node(node_id="lib_reading_room_2", name="自然科学阅览室", node_type="reading_room", category="reading_room", floor_id="F2", floor_label="2F", x=132, y=96, tags=["阅览室", "自然科学"], description="自然科学类图书阅览室。", facilities=["阅览座位", "WiFi"]),
            node(node_id="lib_digital_room_2f", name="数字阅览区", node_type="reading_room", category="reading_room", floor_id="F2", floor_label="2F", x=132, y=176, tags=["数字阅览"], description="数字资源与数据库阅览区。", facilities=["终端", "WiFi"]),
            node(node_id="lib_group_room_2f", name="小组研讨室", node_type="service", category="education", floor_id="F2", floor_label="2F", x=132, y=304, tags=["研讨"], description="适合小组学习与汇报的研讨室。", facilities=["白板", "投影"]),
            node(node_id="lib_toilet_2f", name="二楼洗手间", node_type="facility", category="restroom", floor_id="F2", floor_label="2F", x=244, y=304, tags=["洗手间"], description="图书馆二楼公共洗手间。", facilities=["洗手间"], extra={"is_indoor": True, "indoor_building": "图书馆"}),
            node(node_id="lib_consult_room_2f", name="咨询服务室", node_type="service", category="service", floor_id="F2", floor_label="2F", x=244, y=96, tags=["咨询"], description="二楼咨询与借阅辅助服务。", facilities=["服务台"]),
            node(node_id="lib_staircase_f3", name="三楼楼梯间", node_type="staircase", category="passage", floor_id="F3", floor_label="3F", x=332, y=96, tags=["楼梯"], description="图书馆三楼楼梯间。", facilities=["楼梯扶手"]),
            node(node_id="lib_elevator_f3", name="三楼电梯", node_type="elevator", category="passage", floor_id="F3", floor_label="3F", x=332, y=176, tags=["电梯"], description="图书馆三楼电梯厅。", facilities=["电梯", "盲文按钮"]),
            node(node_id="lib_archive_room_3f", name="馆藏资料室", node_type="service", category="service", floor_id="F3", floor_label="3F", x=132, y=96, tags=["资料室"], description="馆藏资料与专题书库。", facilities=["档案柜"]),
            node(node_id="lib_quiet_room_3f", name="安静自习区", node_type="reading_room", category="reading_room", floor_id="F3", floor_label="3F", x=132, y=176, tags=["自习"], description="三楼安静自习区。", facilities=["阅览座位", "插座"]),
            node(node_id="lib_reference_room_3f", name="参考咨询区", node_type="service", category="service", floor_id="F3", floor_label="3F", x=132, y=304, tags=["咨询"], description="参考咨询与检索辅导区域。", facilities=["咨询台"]),
            node(node_id="lib_toilet_3f", name="三楼洗手间", node_type="facility", category="restroom", floor_id="F3", floor_label="3F", x=244, y=304, tags=["洗手间"], description="图书馆三楼公共洗手间。", facilities=["洗手间"], extra={"is_indoor": True, "indoor_building": "图书馆"}),
            node(node_id="lib_rest_area_3f", name="休息区", node_type="service", category="service", floor_id="F3", floor_label="3F", x=244, y=96, tags=["休息"], description="馆内休息区。", facilities=["座椅"]),
        ]
        edges: list[dict[str, object]] = []
        for source_id, target_id, distance, edge_type, name, vehicle_access, congestion, ideal_speed in [
            ("lib_entrance", "lib_reception", 10, "indoor_path", "入口 -> 总服务台", "pedestrian_only", 0.3, 1.5),
            ("lib_entrance", "lib_reading_room_1", 25, "indoor_path", "入口 -> 中文社科阅览室", "pedestrian_only", 0.4, 1.5),
            ("lib_entrance", "lib_cafe", 15, "indoor_path", "入口 -> 图书馆咖啡厅", "pedestrian_only", 0.5, 1.2),
            ("lib_entrance", "lib_toilet_1f", 20, "indoor_path", "入口 -> 一楼洗手间", "pedestrian_only", 0.2, 1.5),
            ("lib_entrance", "lib_staircase", 12, "indoor_path", "入口 -> 楼梯间", "pedestrian_only", 0.3, 1.5),
            ("lib_entrance", "lib_elevator", 18, "indoor_path", "入口 -> 电梯", "all", 0.3, 1.5),
            ("lib_entrance", "lib_self_serve", 8, "indoor_path", "入口 -> 自助借还区", "pedestrian_only", 0.5, 1.5),
            ("lib_reception", "lib_self_serve", 5, "indoor_path", "", "pedestrian_only", 0.6, 1.5),
            ("lib_staircase", "lib_elevator", 6, "indoor_path", "楼梯间 -> 电梯", "all", 0.2, 2.0),
            ("lib_staircase_f2", "lib_elevator_f2", 6, "indoor_path", "二楼楼梯间 -> 电梯", "all", 0.2, 2.0),
            ("lib_staircase_f2", "lib_reading_room_2", 10, "indoor_path", "二楼楼梯间 -> 自然科学阅览室", "pedestrian_only", 1.0, 1.5),
            ("lib_elevator_f2", "lib_digital_room_2f", 8, "indoor_path", "二楼电梯 -> 数字阅览区", "all", 1.0, 1.5),
            ("lib_elevator_f2", "lib_group_room_2f", 12, "indoor_path", "二楼电梯 -> 小组研讨室", "all", 1.0, 1.5),
            ("lib_elevator_f2", "lib_toilet_2f", 10, "indoor_path", "二楼电梯 -> 洗手间", "all", 1.0, 1.5),
            ("lib_staircase_f2", "lib_consult_room_2f", 9, "indoor_path", "二楼楼梯间 -> 咨询服务室", "pedestrian_only", 1.0, 1.5),
            ("lib_staircase_f3", "lib_archive_room_3f", 9, "indoor_path", "三楼楼梯间 -> 馆藏资料室", "pedestrian_only", 1.0, 1.5),
            ("lib_staircase_f3", "lib_quiet_room_3f", 10, "indoor_path", "三楼楼梯间 -> 安静自习区", "pedestrian_only", 1.0, 1.5),
            ("lib_elevator_f3", "lib_reference_room_3f", 10, "indoor_path", "三楼电梯 -> 参考咨询区", "all", 1.0, 1.5),
            ("lib_elevator_f3", "lib_toilet_3f", 9, "indoor_path", "三楼电梯 -> 洗手间", "all", 1.0, 1.5),
            ("lib_elevator_f3", "lib_rest_area_3f", 7, "indoor_path", "三楼电梯 -> 休息区", "all", 1.0, 1.5),
            ("lib_staircase", "lib_staircase_f2", 16, "stairs", "F1 -> F2 楼梯", "pedestrian_only", 1.0, 1.5),
            ("lib_staircase_f2", "lib_staircase_f3", 16, "stairs", "F2 -> F3 楼梯", "pedestrian_only", 1.0, 1.5),
            ("lib_elevator", "lib_elevator_f2", 12, "elevator", "F1 -> F2 电梯", "all", 1.0, 1.5),
            ("lib_elevator_f2", "lib_elevator_f3", 12, "elevator", "F2 -> F3 电梯", "all", 1.0, 1.5),
        ]:
            description = "服务台旁的自助区" if {source_id, target_id} == {"lib_reception", "lib_self_serve"} else ""
            add_bidirectional_edge(
                edges,
                source_id,
                target_id,
                distance=distance,
                edge_type=edge_type,
                name=name,
                description=description,
                vehicle_access=vehicle_access,
                congestion=congestion,
                ideal_speed=ideal_speed,
            )
        return build_template_graph(
            graph_file=str(spec["graph_file"]),
            building_name=str(spec["building_name"]),
            building_id=str(spec["building_id"]),
            template_id=str(spec["template_id"]),
            default_floor_id=str(spec["default_floor_id"]),
            floor_ids=list(spec["floor_ids"]),
            nodes=nodes,
            edges=edges,
        )

    profile = str(spec.get("profile", "default"))
    return build_generic_graph(
        spec,
        entry_location,
        LIBRARY_PROFILE_ZONES[profile],
        corridor_name="馆内连廊",
        entry_name=f"{spec['building_name']}入口大厅",
        entry_type="hall",
        entry_category="hall",
    )


def build_dormitory_graph(spec: dict[str, object], entry_location: dict[str, float]) -> dict[str, object]:
    if str(spec["graph_file"]) == "indoor_DORM1":
        nodes = [
            node(node_id="dorm1_entrance", name="宿舍入口大厅", node_type="hall", category="hall", floor_id="F1", floor_label="1F", x=56, y=240, is_gate=True, tags=["宿舍", "大厅", "入口"], description="学生宿舍31楼入口大厅，连接宿舍区室外道路。", facilities=["公告栏", "信箱", "门禁系统"], location=entry_location),
            node(node_id="dorm1_corridor", name="一楼走廊", node_type="hall", category="passage", floor_id="F1", floor_label="1F", x=170, y=240, tags=["走廊"], description="宿舍一楼主走廊。"),
            node(node_id="dorm1_room_101", name="101 宿舍", node_type="dormitory", category="dormitory", floor_id="F1", floor_label="1F", x=112, y=96, tags=["宿舍"], description="一楼 101 宿舍，四人间。", facilities=["床", "书桌", "衣柜"]),
            node(node_id="dorm1_room_102", name="102 宿舍", node_type="dormitory", category="dormitory", floor_id="F1", floor_label="1F", x=112, y=176, tags=["宿舍"], description="一楼 102 宿舍，四人间。", facilities=["床", "书桌", "衣柜"]),
            node(node_id="dorm1_room_103", name="103 宿舍", node_type="dormitory", category="dormitory", floor_id="F1", floor_label="1F", x=112, y=304, tags=["宿舍"], description="一楼 103 宿舍，四人间。", facilities=["床", "书桌", "衣柜"]),
            node(node_id="dorm1_room_104", name="104 宿舍", node_type="dormitory", category="dormitory", floor_id="F1", floor_label="1F", x=244, y=96, tags=["宿舍"], description="一楼 104 宿舍，四人间。", facilities=["床", "书桌", "衣柜"]),
            node(node_id="dorm1_staircase", name="楼梯间", node_type="staircase", category="passage", floor_id="F1", floor_label="1F", x=332, y=96, tags=["楼梯"], description="宿舍主楼梯，连接各楼层。", facilities=["楼梯扶手"]),
            node(node_id="dorm1_elevator", name="电梯", node_type="elevator", category="passage", floor_id="F1", floor_label="1F", x=332, y=176, tags=["电梯"], description="宿舍无障碍电梯。", facilities=["电梯", "盲文按钮"]),
            node(node_id="dorm1_laundry", name="洗衣房", node_type="service", category="service", floor_id="F1", floor_label="1F", x=244, y=176, tags=["洗衣"], description="公共洗衣房。", facilities=["洗衣机", "烘干机"]),
            node(node_id="dorm1_toilet", name="一楼公共卫生间", node_type="facility", category="restroom", floor_id="F1", floor_label="1F", x=332, y=304, tags=["洗手间"], description="一楼公共卫生间。", facilities=["洗手间", "洗手池"], extra={"is_indoor": True, "indoor_building": "学生宿舍31楼"}),
            node(node_id="dorm1_common_room", name="公共活动室", node_type="service", category="service", floor_id="F1", floor_label="1F", x=244, y=304, tags=["活动室"], description="一楼公共活动室。", facilities=["电视", "桌椅"]),
            node(node_id="dorm1_corridor_f2", name="二楼走廊", node_type="hall", category="passage", floor_id="F2", floor_label="2F", x=170, y=240, tags=["走廊"], description="宿舍二楼主走廊。"),
            node(node_id="dorm1_room_201", name="201 宿舍", node_type="dormitory", category="dormitory", floor_id="F2", floor_label="2F", x=112, y=96, tags=["宿舍"], description="二楼 201 宿舍。", facilities=["床", "书桌", "衣柜"]),
            node(node_id="dorm1_room_202", name="202 宿舍", node_type="dormitory", category="dormitory", floor_id="F2", floor_label="2F", x=112, y=176, tags=["宿舍"], description="二楼 202 宿舍。", facilities=["床", "书桌", "衣柜"]),
            node(node_id="dorm1_staircase_f2", name="二楼楼梯间", node_type="staircase", category="passage", floor_id="F2", floor_label="2F", x=332, y=96, tags=["楼梯"], description="宿舍二楼楼梯间。", facilities=["楼梯扶手"]),
            node(node_id="dorm1_elevator_f2", name="二楼电梯", node_type="elevator", category="passage", floor_id="F2", floor_label="2F", x=332, y=176, tags=["电梯"], description="宿舍二楼电梯。", facilities=["电梯", "盲文按钮"]),
            node(node_id="dorm1_restroom_f2", name="二楼公共卫生间", node_type="facility", category="restroom", floor_id="F2", floor_label="2F", x=332, y=304, tags=["洗手间"], description="二楼公共卫生间。", facilities=["洗手间"], extra={"is_indoor": True, "indoor_building": "学生宿舍31楼"}),
            node(node_id="dorm1_pantry_f2", name="二楼开水间", node_type="service", category="service", floor_id="F2", floor_label="2F", x=244, y=176, tags=["开水间"], description="二楼开水与便民服务区。", facilities=["开水器"]),
            node(node_id="dorm1_lounge_f2", name="二楼休息区", node_type="service", category="service", floor_id="F2", floor_label="2F", x=244, y=304, tags=["休息"], description="二楼休息区。", facilities=["沙发"]),
            node(node_id="dorm1_corridor_f3", name="三楼走廊", node_type="hall", category="passage", floor_id="F3", floor_label="3F", x=170, y=240, tags=["走廊"], description="宿舍三楼主走廊。"),
            node(node_id="dorm1_room_301", name="301 宿舍", node_type="dormitory", category="dormitory", floor_id="F3", floor_label="3F", x=112, y=96, tags=["宿舍"], description="三楼 301 宿舍。", facilities=["床", "书桌", "衣柜"]),
            node(node_id="dorm1_room_302", name="302 宿舍", node_type="dormitory", category="dormitory", floor_id="F3", floor_label="3F", x=112, y=176, tags=["宿舍"], description="三楼 302 宿舍。", facilities=["床", "书桌", "衣柜"]),
            node(node_id="dorm1_staircase_f3", name="三楼楼梯间", node_type="staircase", category="passage", floor_id="F3", floor_label="3F", x=332, y=96, tags=["楼梯"], description="宿舍三楼楼梯间。", facilities=["楼梯扶手"]),
            node(node_id="dorm1_elevator_f3", name="三楼电梯", node_type="elevator", category="passage", floor_id="F3", floor_label="3F", x=332, y=176, tags=["电梯"], description="宿舍三楼电梯。", facilities=["电梯", "盲文按钮"]),
            node(node_id="dorm1_restroom_f3", name="三楼公共卫生间", node_type="facility", category="restroom", floor_id="F3", floor_label="3F", x=332, y=304, tags=["洗手间"], description="三楼公共卫生间。", facilities=["洗手间"], extra={"is_indoor": True, "indoor_building": "学生宿舍31楼"}),
            node(node_id="dorm1_study_room_f3", name="三楼学习角", node_type="service", category="service", floor_id="F3", floor_label="3F", x=244, y=176, tags=["学习"], description="三楼共享学习角。", facilities=["桌椅"]),
            node(node_id="dorm1_duty_room_f3", name="值班室", node_type="service", category="service", floor_id="F3", floor_label="3F", x=244, y=304, tags=["值班"], description="宿舍值班室。", facilities=["值班台"]),
        ]
        edges: list[dict[str, object]] = []
        for source_id, target_id, distance, edge_type, name, vehicle_access in [
            ("dorm1_entrance", "dorm1_corridor", 5, "indoor_path", "入口 -> 一楼走廊", "pedestrian_only"),
            ("dorm1_corridor", "dorm1_room_101", 8, "indoor_path", "一楼走廊 -> 101 宿舍", "pedestrian_only"),
            ("dorm1_corridor", "dorm1_room_102", 12, "indoor_path", "一楼走廊 -> 102 宿舍", "pedestrian_only"),
            ("dorm1_corridor", "dorm1_room_103", 18, "indoor_path", "一楼走廊 -> 103 宿舍", "pedestrian_only"),
            ("dorm1_corridor", "dorm1_room_104", 22, "indoor_path", "一楼走廊 -> 104 宿舍", "pedestrian_only"),
            ("dorm1_corridor", "dorm1_staircase", 15, "indoor_path", "一楼走廊 -> 楼梯间", "pedestrian_only"),
            ("dorm1_corridor", "dorm1_elevator", 13, "indoor_path", "一楼走廊 -> 电梯", "all"),
            ("dorm1_corridor", "dorm1_laundry", 10, "indoor_path", "一楼走廊 -> 洗衣房", "pedestrian_only"),
            ("dorm1_corridor", "dorm1_toilet", 6, "indoor_path", "一楼走廊 -> 公共卫生间", "pedestrian_only"),
            ("dorm1_corridor", "dorm1_common_room", 20, "indoor_path", "一楼走廊 -> 公共活动室", "pedestrian_only"),
            ("dorm1_corridor_f2", "dorm1_room_201", 8, "indoor_path", "二楼走廊 -> 201 宿舍", "pedestrian_only"),
            ("dorm1_corridor_f2", "dorm1_room_202", 10, "indoor_path", "二楼走廊 -> 202 宿舍", "pedestrian_only"),
            ("dorm1_corridor_f2", "dorm1_staircase_f2", 15, "indoor_path", "二楼走廊 -> 楼梯间", "pedestrian_only"),
            ("dorm1_corridor_f2", "dorm1_elevator_f2", 13, "indoor_path", "二楼走廊 -> 电梯", "all"),
            ("dorm1_corridor_f2", "dorm1_restroom_f2", 6, "indoor_path", "二楼走廊 -> 公共卫生间", "pedestrian_only"),
            ("dorm1_corridor_f2", "dorm1_pantry_f2", 9, "indoor_path", "二楼走廊 -> 开水间", "pedestrian_only"),
            ("dorm1_corridor_f2", "dorm1_lounge_f2", 12, "indoor_path", "二楼走廊 -> 休息区", "pedestrian_only"),
            ("dorm1_corridor_f3", "dorm1_room_301", 8, "indoor_path", "三楼走廊 -> 301 宿舍", "pedestrian_only"),
            ("dorm1_corridor_f3", "dorm1_room_302", 10, "indoor_path", "三楼走廊 -> 302 宿舍", "pedestrian_only"),
            ("dorm1_corridor_f3", "dorm1_staircase_f3", 15, "indoor_path", "三楼走廊 -> 楼梯间", "pedestrian_only"),
            ("dorm1_corridor_f3", "dorm1_elevator_f3", 13, "indoor_path", "三楼走廊 -> 电梯", "all"),
            ("dorm1_corridor_f3", "dorm1_restroom_f3", 6, "indoor_path", "三楼走廊 -> 公共卫生间", "pedestrian_only"),
            ("dorm1_corridor_f3", "dorm1_study_room_f3", 9, "indoor_path", "三楼走廊 -> 学习角", "pedestrian_only"),
            ("dorm1_corridor_f3", "dorm1_duty_room_f3", 11, "indoor_path", "三楼走廊 -> 值班室", "pedestrian_only"),
            ("dorm1_staircase_f2", "dorm1_corridor_f2", 4, "indoor_path", "二楼楼梯间 -> 二楼走廊", "pedestrian_only"),
            ("dorm1_elevator_f2", "dorm1_corridor_f2", 4, "indoor_path", "二楼电梯 -> 二楼走廊", "all"),
            ("dorm1_staircase_f3", "dorm1_corridor_f3", 4, "indoor_path", "三楼楼梯间 -> 三楼走廊", "pedestrian_only"),
            ("dorm1_elevator_f3", "dorm1_corridor_f3", 4, "indoor_path", "三楼电梯 -> 三楼走廊", "all"),
            ("dorm1_staircase", "dorm1_staircase_f2", 16, "stairs", "F1 -> F2 楼梯", "pedestrian_only"),
            ("dorm1_staircase_f2", "dorm1_staircase_f3", 16, "stairs", "F2 -> F3 楼梯", "pedestrian_only"),
            ("dorm1_elevator", "dorm1_elevator_f2", 12, "elevator", "F1 -> F2 电梯", "all"),
            ("dorm1_elevator_f2", "dorm1_elevator_f3", 12, "elevator", "F2 -> F3 电梯", "all"),
        ]:
            add_bidirectional_edge(edges, source_id, target_id, distance=distance, edge_type=edge_type, name=name, vehicle_access=vehicle_access)
        return build_template_graph(
            graph_file=str(spec["graph_file"]),
            building_name=str(spec["building_name"]),
            building_id=str(spec["building_id"]),
            template_id=str(spec["template_id"]),
            default_floor_id=str(spec["default_floor_id"]),
            floor_ids=list(spec["floor_ids"]),
            nodes=nodes,
            edges=edges,
        )

    zone_map = {
        "F1": [
            ("room_101", "101 宿舍", "dormitory", "dormitory"),
            ("room_102", "102 宿舍", "dormitory", "dormitory"),
            ("laundry_1f", "洗衣房", "service", "service"),
            ("lounge_1f", "公共活动室", "service", "service"),
        ],
        "F2": [
            ("room_201", "201 宿舍", "dormitory", "dormitory"),
            ("room_202", "202 宿舍", "dormitory", "dormitory"),
            ("pantry_2f", "开水间", "service", "service"),
            ("rest_area_2f", "休息区", "service", "service"),
        ],
        "F3": [
            ("room_301", "301 宿舍", "dormitory", "dormitory"),
            ("room_302", "302 宿舍", "dormitory", "dormitory"),
            ("study_room_3f", "共享学习角", "service", "service"),
            ("duty_room_3f", "值班室", "service", "service"),
        ],
    }
    return build_generic_graph(
        spec,
        entry_location,
        zone_map,
        corridor_name="宿舍走廊",
        entry_name=f"{spec['building_name']}入口大厅",
        entry_type="hall",
        entry_category="hall",
    )


BUILDERS = {
    "teaching": build_teaching_graph,
    "library": build_library_graph,
    "dormitory": build_dormitory_graph,
    "canteen": build_canteen_graph,
    "sports": build_sports_graph,
}


def update_outdoor_with_entries(outdoor: dict[str, object], registry: list[dict[str, object]]) -> None:
    nodes = outdoor["nodes"]
    node_index = {node["id"]: node for node in nodes}

    target_entry_ids = {entry["entry_node_id"] for entry in registry}
    for node in nodes:
        node_id = node["id"]
        if node_id not in target_entry_ids:
            if node_id.startswith("poi_door_"):
                node["is_gate"] = False
                node["sub_graph_id"] = None
            continue

        building_entry = next(item for item in registry if item["entry_node_id"] == node_id)
        node["is_gate"] = True
        node["sub_graph_id"] = building_entry["indoor_graph_id"]

    for item in registry:
        building_node = node_index[item["building_id"]]
        building_node["indoor_supported"] = True
        building_node["indoor_graph_id"] = item["indoor_graph_id"]
        building_node["indoor_entry_node_id"] = item["entry_node_id"]


def update_global_sites(global_sites: dict[str, object], sub_graph_ids: list[str]) -> None:
    for site in global_sites["sites"]:
        if site.get("id") == "PKU":
            site["sub_graphs"] = ["outdoor", *sub_graph_ids]
            return
    raise RuntimeError("PKU site not found in global_sites.json")


def main() -> None:
    outdoor = read_json(OUTDOOR_PATH)
    global_sites = read_json(GLOBAL_SITES_PATH)
    outdoor_node_index = {node["id"]: node for node in outdoor["nodes"]}

    registry: list[dict[str, object]] = []

    for spec in BUILDINGS:
        entry_node = outdoor_node_index[str(spec["entry_node_id"])]
        location = dict(entry_node.get("location", {}))
        builder = BUILDERS[str(spec["builder"])]
        graph = builder(spec, location)
        write_json(PKU_DIR / f"{spec['graph_file']}.json", graph)
        registry.append(
            {
                "building_id": spec["building_id"],
                "building_name": spec["building_name"],
                "entry_node_id": spec["entry_node_id"],
                "indoor_graph_id": spec["graph_file"],
                "template_id": spec["template_id"],
                "floor_ids": spec["floor_ids"],
                "default_floor_id": spec["default_floor_id"],
                "entry_mapping_reason": spec["entry_reason"],
            }
        )

    write_json(GEO_DIR / "indoor_template_catalog.json", {"templates": TEMPLATE_CATALOG})
    write_json(GEO_DIR / "indoor_building_registry.json", {"buildings": registry})
    update_outdoor_with_entries(outdoor, registry)
    update_global_sites(global_sites, [str(spec["graph_file"]) for spec in BUILDINGS])
    write_json(OUTDOOR_PATH, outdoor)
    write_json(GLOBAL_SITES_PATH, global_sites)


if __name__ == "__main__":
    main()
