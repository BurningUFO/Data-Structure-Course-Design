# 地图方案 B M9：OSM 路线匹配记录

## 1. 本阶段范围

M9 在 M8 本地 OSM roads / buildings / water / landuse 图层基础上，增加课程图 edge 到本地 OSM road geometry 的匹配表。路径规划仍使用课程图和现有 routing 算法，OSM 只提供 route overlay 和项目道路展示的可视化线形。

本阶段没有修改：

1. routing 算法。
2. graph loader 语义。
3. `data/sites/PKU/outdoor.json` 的课程图节点、边和手工 geometry。
4. Web UI 运行时的 OSMnx / Overpass 调用策略。
5. 搜索、推荐、日记、压缩等非地图模块。

## 2. 匹配文件

匹配数据文件：

```text
data/sites/PKU/geo/edge_osm_geometry_matches.json
```

数据来源：

```text
data/sites/PKU/geo/osm_roads_simplified.geojson
```

匹配文件中每条记录包含：

1. `edge_key`、`from`、`to`：课程图 edge 标识。
2. `geometry_source=osm_matched`：说明该 geometry 来自本地 OSM road 候选。
3. `confidence`：人工核验后的匹配置信度。
4. `osm_way_ids`：使用到的本地 OSM way id。
5. `geometry`：内部维护为 `{"lat": ..., "lng": ...}`，API 输出时统一转换为 GeoJSON `[lng, lat]`。
6. `notes`：记录端点吸附、低置信度或道路来源说明。

## 3. 匹配策略

本阶段采用半自动加人工核验策略：

1. 读取 M8 生成的 `osm_roads_simplified.geojson`。
2. 以课程图 edge 的 `from` / `to` 节点坐标为端点，在本地 OSM roads 中查找端点附近、路径附近或方向一致的 `LineString`。
3. 优先选择 `footway`、`path`、`service`、`residential` 等校园内部可步行道路。
4. 对课程图节点坐标与 OSM road 端点不完全重合的情况，在 matched geometry 首尾保留课程图节点坐标，并在中间使用 OSM road 坐标作为贴路形状。
5. 对低置信度 edge 保留 `confidence` 和 `notes`，后续可用更精确采点替换。
6. 匹配失败时不阻断路线规划，继续使用 manual geometry 或 fallback line。

## 4. Geometry 来源优先级

服务层解析 edge geometry 的优先级为：

1. `osm_matched`：来自 `edge_osm_geometry_matches.json`。
2. `manual`：来自 `data/sites/PKU/outdoor.json` 中已有 `geometry`。
3. `fallback_line`：由 from / to 两个课程图节点坐标生成两点 `LineString`。

反向路线会复用正向或已存储方向的 geometry，并在 route overlay 中 reverse 坐标；课程图仍是路径规划权威。

## 5. 已匹配 Edge

当前匹配表覆盖 13 条课程图 edge：

| Edge | OSM way ids | Confidence | 说明 |
| --- | --- | --- | --- |
| `gate_north->square_center` | `1075644762` | 0.74 | 西门到广场附近 footway |
| `square_center->library` | `1154086721`, `1169804426` | 0.86 | 图书馆前 footway |
| `square_center->road_cross` | `1154086721`, `1151226558` | 0.72 | 广场到路口连接段 |
| `road_cross->canteen` | `226703721`, `1149802301` | 0.78 | 东西向道路和食堂路径 |
| `road_cross->gate_east` | `1154086722`, `237011438` | 0.63 | 东门方向，课程图坐标较抽象 |
| `road_cross->teaching_building_1` | `1159305380`, `1159305381`, `1151226559` | 0.77 | 教学楼附近 footway / steps |
| `road_cross->teaching_building_2` | `1159305380` | 0.72 | 第二教学楼附近 footway |
| `road_cross->dormitory_1` | `970687429`, `1159305375` | 0.66 | 宿舍方向 service / footway |
| `road_cross->convenience_store` | `970687429`, `33457409`, `970687433` | 0.72 | 商业节点方向 service / residential |
| `gate_south->teaching_building_1` | `33457307`, `1159305373`, `1159305374`, `1151226559` | 0.65 | 南门到一教，含端点吸附 |
| `sports_ground->gate_north` | `1101010405`, `1172670686` | 0.72 | 体育场到西门附近 footway |
| `parking_lot->gate_east` | `1111656405`, `237011438` | 0.66 | 停车场到东门方向 |
| `toilet_sports_area->sports_ground` | `1101010405` | 0.74 | 体育场洗手间到体育场 |

`toilet_lib_area->library` 保持使用 `manual` geometry，用于保留并验证 manual geometry 回退层级。

## 6. 覆盖率统计

当前 `/api/map/geojson?site_id=PKU` 统计：

```text
node_feature_count: 39
edge_feature_count: 81
feature_count: 120
geometry_edge_count: 14
osm_matched_edge_count: 13
manual_geometry_edge_count: 1
fallback_edge_count: 67
geometry_coverage_ratio: 0.1728
osm_matched_coverage_ratio: 0.1605
```

关键演示路线统计：

| Route | Path | route geometry stats |
| --- | --- | --- |
| `gate_north -> library` | `gate_north -> square_center -> library` | `osm_matched_segment_count=2`, `manual_geometry_segment_count=0`, `fallback_segment_count=0` |
| `gate_east -> canteen` | `gate_east -> road_cross -> canteen` | `osm_matched_segment_count=2`, `manual_geometry_segment_count=0`, `fallback_segment_count=0` |
| `gate_north -> canteen` | `gate_north -> square_center -> road_cross -> canteen` | `osm_matched_segment_count=3`, `manual_geometry_segment_count=0`, `fallback_segment_count=0` |
| `library -> gate_north` | `library -> square_center -> gate_north` | 反向复用 `osm_matched` geometry，`reverse_edge_reuse_count=1` |

## 7. API 和 UI 表达

`/api/map/geojson` 的 edge properties 保留旧字段，并增加：

1. `geometry_source`
2. `geometry_confidence`
3. `osm_way_ids`

`/api/map/geojson` 的 stats 增加：

1. `osm_matched_edge_count`
2. `manual_geometry_edge_count`
3. `osm_matched_coverage_ratio`

`/api/route` 和 `/api/route/multi` 的 `route_geometry_stats` 增加：

1. `osm_matched_segment_count`
2. `manual_geometry_segment_count`

前端地图状态、route caption 和 route 状态条显示 `OSM匹配 / manual / fallback` 段数。Leaflet 项目道路按 `geometry_source` 做轻微区分，route overlay 仍保持最高视觉层级。

## 8. 已知限制

1. 课程图节点坐标是课程演示数据，和 OSM 路网端点并不总是完全重合，因此 matched geometry 首尾存在端点吸附。
2. `road_cross->gate_east`、`gate_south->teaching_building_1`、`parking_lot->gate_east` 置信度较低，后续应优先复核。
3. 当前仍只覆盖关键演示边，非关键课程图 edge 继续使用 fallback line。
4. OSM roads 只影响可视化 geometry，不参与最短路或多目标路径搜索。
5. 本阶段不下载外部瓦片，也不在 Web UI 请求时调用 OSMnx 或 Overpass。

## 9. 扩展方式

继续扩展匹配时：

1. 在 `osm_roads_simplified.geojson` 中查找候选 road feature，记录 `osm_id`。
2. 新增一条 `edge_osm_geometry_matches.json` 的 `matches[]` 记录。
3. 确认 `geometry[0]` 接近 `from` 节点，最后一点接近 `to` 节点。
4. 设定 `confidence`，低置信度必须写入 `notes`。
5. 不修改 routing 算法，不把 OSM roads 当作搜索图。
6. 运行 `py -m pytest tests/test_ui_demo.py` 和 `py -m pytest`。
7. 通过 API smoke check 观察 `/api/map/geojson` stats 和关键 route 的 `route_geometry_stats`。

## 10. 验证记录

本阶段已增加测试覆盖：

1. `edge_osm_geometry_matches.json` 可加载。
2. `/api/map/geojson` stats 包含并校验 `osm_matched_edge_count`、`manual_geometry_edge_count`。
3. `gate_north->square_center` 使用 `geometry_source=osm_matched`。
4. `gate_north -> library` route 使用 `osm_matched` geometry。
5. `library -> gate_north` 能反向复用 `osm_matched` geometry。
6. 缺失 match 文件时可回退到 `manual` 和 `fallback_line`。

已运行：

```powershell
py -m pytest tests/test_ui_demo.py -q
py -m pytest
```

结果：

```text
26 passed
109 passed in 2.47s
```
