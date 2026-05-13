# 地图方案 B 第十一阶段穿楼边清理与真实路口绕行记录

## 阶段目标

M11 基于 M10 的真实数据重制结果继续清理路网拓扑。M10 已做到 `fallback_edge_count=0`，但部分 edge geometry 仍会穿过建筑、水域或非真实通行区域。M11 不执行 M12 的 UI/命名精修，只处理室外课程图边：删除不真实直连，必要时通过真实道路路口、步道节点、广场入口或建筑外侧入口 waypoint 间接到达。

运行时边界不变：课程图仍是 routing authority；Web UI 不调用 OSMnx、Overpass 或高德接口；没有重写 Dijkstra、Floyd 或多目标路线算法。

## 审计方法

审计输入：

- `data/sites/PKU/outdoor.json`
- `data/sites/PKU/geo/edge_osm_geometry_matches.json`
- `data/sites/PKU/geo/osm_buildings.geojson`
- `data/sites/PKU/geo/osm_water_landuse.geojson`
- `data/sites/PKU/geo/osm_roads_simplified.geojson`

本地环境没有 Shapely，因此使用纯 Python 几何初筛：将经纬度投影到局部米制平面，逐条扫描 M10 的 45 条无向 edge geometry，检查 building/water polygon 内部长度、road 对齐情况和长端点吸附。修正后再次对最终 42 条无向 edge 执行 building/water polygon 复扫，结果为 0 条穿楼/穿水。

审计产物：

- `data/sites/PKU/geo/m11_blocked_edge_audit.json`
- `data/sites/PKU/geo/m11_removed_edges.json`
- `data/sites/PKU/geo/m11_added_waypoints.json`

## 删除的直连边

M11 删除 11 条无向直连边，同步删除对应反向 directed edge 和 match 记录：

| 删除边 | 原因 | 替代绕行路径 |
| --- | --- | --- |
| `gate_south -> road_nongyuan_west_south` | 南门到农园西路直连穿过建筑轮廓 | `gate_south -> road_south_gate_inner -> road_nongyuan_north_west -> square_center -> road_wusi_mid -> road_lijiao_west -> road_southeast_campus_west -> road_second_teaching_west -> road_nongyuan_south_east -> road_nongyuan_south_west -> road_nongyuan_west_south` |
| `library -> toilet_lib_area` | 图书馆到洗手间直连穿过一教区域 | `library -> road_library_south -> road_lake_southeast -> road_lijiao_north -> road_lijiao_west -> road_wusi_mid -> road_cross -> road_wusi_north -> toilet_lib_area` |
| `road_centennial_plaza_east -> road_southeast_campus_west` | 百讲广场东侧到东南路口直连穿过智华楼 | `road_centennial_plaza_east -> road_nongyuan_north_west -> square_center -> road_wusi_mid -> road_lijiao_west -> road_southeast_campus_west` |
| `road_cross -> road_lijiao_west` | 理教西路直连穿过地学楼区域 | `road_cross -> road_wusi_mid -> road_lijiao_west` |
| `road_nongyuan_west_south -> road_second_teaching_west` | 缺少农园南侧真实转角 | `road_nongyuan_west_south -> road_nongyuan_south_west -> road_nongyuan_south_east -> road_second_teaching_west` |
| `road_second_teaching_west -> canteen` | 二教到食堂直连穿过农园餐厅 | `road_second_teaching_west -> road_nongyuan_south_east -> road_nongyuan_south_west -> road_nongyuan_west_south -> canteen` |
| `road_second_gym_south_east -> road_yannan_east` | 西南 shortcut 缺少 OSM road 支撑并擦过宿舍楼体 | `road_second_gym_south_east -> road_library_south_west -> road_wusi_mid -> square_center -> road_yannan_east` |
| `road_southeast_campus_west -> teaching_building_2` | 直连进入二教建筑轮廓 | `road_southeast_campus_west -> road_second_teaching_west -> teaching_building_2` |
| `road_southeast_campus_west -> road_third_teaching_south_east` | 直连穿过三教区域 | `road_southeast_campus_west -> road_second_teaching_west -> road_third_teaching_south_east` |
| `road_third_teaching_south_east -> road_science_east` | 长直连穿过中间建筑，应用既有路口绕行 | `road_third_teaching_south_east -> road_second_teaching_west -> road_southeast_campus_west -> road_lijiao_west -> road_lijiao_north -> road_chengfuyuan_west -> road_chengfuyuan_east -> road_east_gate_south -> road_science_east` |
| `road_nongyuan_north_west -> canteen` | 农园北口到食堂直连穿过教育学院区域 | `road_nongyuan_north_west -> square_center -> road_wusi_mid -> road_lijiao_west -> road_southeast_campus_west -> road_second_teaching_west -> road_nongyuan_south_east -> road_nongyuan_south_west -> road_nongyuan_west_south -> canteen` |

## 新增和复用 Waypoint

新增 3 个真实道路 waypoint：

| Waypoint | 坐标 | 用途 |
| --- | --- | --- |
| `road_south_gate_inner` | `39.9861331, 116.3053872` | 南门内侧五四路节点，替代南门到农园西路的穿楼直连 |
| `road_nongyuan_south_west` | `39.9869801, 116.3060061` | 农园南路西侧转角 |
| `road_nongyuan_south_east` | `39.9869969, 116.3064966` | 农园南路东侧转角 |

同时将 `library`、`teaching_building_1`、`teaching_building_2`、`dormitory_1`、`canteen`、`toilet_lib_area` 的室外 route target 坐标收敛到建筑外侧入口或步道接驳点，避免室外 edge 穿入建筑内部。

## Geometry 统计

当前 `/api/map/geojson?site_id=PKU` stats：

```json
{
  "node_feature_count": 42,
  "edge_feature_count": 42,
  "feature_count": 84,
  "geometry_edge_count": 42,
  "osm_matched_edge_count": 40,
  "manual_geometry_edge_count": 2,
  "fallback_edge_count": 0,
  "geometry_coverage_ratio": 1.0,
  "osm_matched_coverage_ratio": 0.9524
}
```

两条 manual edge 为短洗手间接入边，其余 40 条为 `osm_matched`。最终复扫：42 条无向 edge 中 0 条穿 building/water polygon。

## 关键路线验收

| Route | Path 摘要 | route_segment_count | OSM | manual | fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| `gate_north -> library` | 西门经未名湖东南、图书馆南侧步道口到图书馆 | 5 | 5 | 0 | 0 |
| `gate_north -> canteen` | 西门经理教西路、东南路口、农园南侧转角到食堂 | 11 | 11 | 0 | 0 |
| `gate_east -> canteen` | 东门经成府园南路、理教西路、农园南侧转角到食堂 | 11 | 11 | 0 | 0 |
| `gate_south -> teaching_building_1` | 南门经五四路、百讲南侧、五四路北侧到一教 | 7 | 7 | 0 | 0 |
| `library -> sports_ground` | 图书馆经理教西侧、五四路北侧到体育场 | 8 | 8 | 0 | 0 |
| `library -> canteen` | 图书馆经理教西路、农园南侧转角到食堂 | 10 | 10 | 0 | 0 |
| `gate_north -> sports_ground` | 西门经未名湖东南、理教西路、五四路北侧到体育场 | 9 | 9 | 0 | 0 |
| `gate_east -> parking_lot` | 东门到东门停车场 vehicle-only edge | 1 | 1 | 0 | 0 |
| `library -> toilet_lib_area` | 图书馆经理教西路、五四路北侧到洗手间 | 8 | 7 | 1 | 0 |
| `sports_ground -> toilet_sports_area` | 体育场短接入边 | 1 | 0 | 1 | 0 |

多目标路线：

| Multi route | visit_order | route_segment_count | fallback |
| --- | --- | ---: | ---: |
| `gate_north -> library -> canteen` | `gate_north -> canteen -> library -> gate_north` | 26 | 0 |
| `gate_east -> teaching_building_2 -> dormitory_1 -> canteen` | `gate_east -> dormitory_1 -> canteen -> teaching_building_2 -> gate_east` | 32 | 0 |
| `gate_south -> teaching_building_1 -> library -> sports_ground` | `gate_south -> library -> sports_ground -> teaching_building_1 -> gate_south` | 26 | 0 |

## 验证记录

已运行：

```powershell
py -m pytest tests/test_ui_demo.py -q
py -m pytest tests/test_routing.py -q
py -m pytest tests/test_search.py -q
py -m pytest tests/test_course_requirements.py -q
py -m pytest
```

当前结果：

```text
26 passed
19 passed
23 passed
4 passed
110 passed in 1.22s
```

API smoke check 使用临时内存 HTTP server 通过，覆盖：

- `GET /api/bootstrap`
- `GET /api/map/geojson?site_id=PKU`
- `GET /api/map/osm-layers?site_id=PKU`
- `POST /api/route`：`gate_north -> library`、`gate_north -> canteen`、`gate_east -> canteen`、`gate_south -> teaching_building_1`、`library -> sports_ground`、`library -> toilet_lib_area`
- `POST /api/route/multi`：`gate_north -> library -> canteen`
- `POST /api/search/scenic`
- `POST /api/search/places`
- `POST /api/recommend/catering`
- `POST /api/diaries/fulltext`

API smoke 关键结果：

- `/api/map/geojson?site_id=PKU`：42 nodes、42 edges、40 OSM、2 manual、0 fallback。
- 单目标关键路线全部 `fallback_segment_count=0`。
- 多目标 `gate_north -> library -> canteen`：`route_segment_count=26`、`osm_matched_segment_count=26`、`fallback_segment_count=0`。
- 搜索、场所、餐饮推荐和日记全文检索均返回成功响应。

浏览器 smoke check 使用临时端口 `8897` 和 Playwright + 系统 Chrome 通过：

- Leaflet 主地图加载，状态条显示 `节点 42 · 道路 42 · OSM 40 · manual 2 · fallback 0 (100%)`。
- 本地 OSM 图层状态显示 `本地 OSM 932 项 · 3 层开启`。
- `演示单目标` 路线显示 `路线 OSM 5/5 · manual 0 · fallback 0`，摘要距离为 `578.0 m`。
- 切换 `无底图` 后页面保持可用。
- 切换 `SVG` fallback 后状态显示 `SVG 稳定简图`，SVG 渲染元素数为 169，路线统计仍为 fallback 0。

## 已知限制

- M11 仍维护课程图为运行时 routing authority，没有把完整 OSM road network 导入路由算法。
- 个别建筑类 POI 的节点坐标表示“室外入口接驳点”，不是建筑几何中心；这是为了保证室外路线不穿入建筑轮廓。
- 路线比 M10 更长，属于删除不真实直连后的预期结果。
