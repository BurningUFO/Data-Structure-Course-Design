# 地图方案 B 最终交付说明

## 1. 交付基线

- 当前分支：`experiment/map-plan-b`
- 当前阶段：M12 精细化真实地图打磨
- 启动命令：

```powershell
py -B -m src.ui.demo_server
```

- 默认访问地址：

```text
http://127.0.0.1:8765
```

Web UI 运行时只读取本地 JSON / GeoJSON 数据，不调用高德 API、OSMnx、Overpass 或外部路网下载服务。路线算法、图加载语义、搜索、推荐、日记和 AIGC 模块保持原有职责边界。

M10-M12 阶段记录：

```text
docs/地图方案B第十阶段真实数据重制记录.md
docs/地图方案B第十一阶段穿楼边清理与真实路口绕行记录.md
docs/地图方案B第十二阶段精细化真实地图打磨记录.md
```

## 2. 当前能力

地图方案 B 在 M12 具备以下演示能力：

1. 默认使用 `leaflet_geo` 渲染器展示 Leaflet 真实瓦片底图和本地 GeoJSON 地图层。
2. 保留 `simple_svg` 渲染器，可手动切换，也可作为 Leaflet 或 GeoJSON 加载失败时的回退。
3. `GET /api/map/geojson?site_id=PKU` 输出 M12 室外节点和道路 `FeatureCollection`。
4. `GET /api/map/osm-layers?site_id=PKU` 输出本地 OSM-derived roads / buildings / water_landuse 图层。
5. `/api/bootstrap` 保留旧字段，并新增或保留地图 renderer、capabilities、basemap 和 geometry 覆盖统计。
6. `/api/route` 和 `/api/route/multi` 返回 `route_geojson`、`route_line_coordinates`、`route_geometry_stats`。
7. UI 弱化 `road` / waypoint 节点显示，普通搜索和 route target 列表不展示内部路网点。
8. 本地 Leaflet runtime 继续使用 `src/ui/static/vendor/leaflet/`，核心地图渲染不依赖 CDN。

## 3. M12 数据状态

M10 已消除旧 `campus_service_*` 虚拟网格 id，替换为语义化 `road_*` waypoint。M11 删除穿楼、穿非真实通行区域或缺少真实路口的直连边。M12 不继续扩密路网，而是精修名称、tags、description、GeoJSON 展示字段和 UI 显示规则。

当前核心统计：

```text
outdoor nodes: 42
POI nodes: 14
waypoint nodes: 28
directed edges: 84
undirected map edges: 42
GeoJSON features: 84
osm matched edges: 40
manual geometry edges: 2
fallback edges: 0
geometry coverage ratio: 1.0000
osm matched coverage ratio: 0.9524
```

补充审计文件：

```text
data/sites/PKU/geo/node_rebuild_decisions.json
data/sites/PKU/geo/m11_blocked_edge_audit.json
data/sites/PKU/geo/m11_removed_edges.json
data/sites/PKU/geo/m11_added_waypoints.json
data/sites/PKU/geo/M12_visual_audit.json
```

这些文件记录旧虚拟节点替换关系、M11 全量 edge 审计、删除直连边、替代绕行路径、M11 新增 waypoint 和 M12 视觉审计。运行时 `outdoor.json` 和 `edge_osm_geometry_matches.json` 不包含旧 `campus_service_*` id；当前 42 条无向 edge 均有 geometry 和 match 记录，`fallback_edge_count=0`。

## 4. 架构说明

方案 B 采用“课程图仍为算法权威、地图表现层增强”的结构：

1. `outdoor.json` 的节点和边仍是路径规划输入。
2. 本地 OSM roads/buildings/water/landuse 是视觉层和离线校准参考。
3. `edge_osm_geometry_matches.json` 提供路线覆盖层 geometry，匹配失败时按 edge 自带 manual geometry 或 fallback line 处理。
4. 前端通过 `renderMap()` 在 `leaflet_geo` 和 `simple_svg` 间分发。
5. Route overlay 由 `syncLeafletRouteLayer()` 同步，优先渲染后端返回的 `route_geojson`。

## 5. 答辩演示脚本

建议现场按以下顺序操作：

1. 启动服务：`py -B -m src.ui.demo_server`。
2. 打开 `http://127.0.0.1:8765`，进入主要网站。
3. 查看地图状态条，确认 renderer 为 Leaflet 真实地图，并显示 14 个 POI、28 个路网点、42 条道路、40 条 OSM matched、2 条 manual、0 条 fallback。
4. 打开本地 OSM roads/buildings/water_landuse 图层，说明本地图层来自离线 OSM 抽取。
5. 点击“演示单目标”，规划 `gate_north -> library`，说明路线经西门内侧步道口、未名湖东南步道和图书馆南侧步道口，5/5 段为 `osm_matched`。
6. 规划 `gate_north -> canteen`、`gate_east -> canteen`、`gate_south -> teaching_building_1`，确认 route stats 均为 fallback 0。
7. 点击“演示多目标”，规划 `library + canteen`，说明多段 leg 仍返回各自 geometry stats。
8. 切换“无底图”模式，确认本地 OSM 图层、项目道路和路线仍可显示。
9. 点击 `SVG`，展示 `simple_svg` 稳定回退；再切回 `Leaflet`。
10. 可选：综合查询“图书馆”、场所查询“洗手间”、美食推荐、日记全文检索，分别从结果发起路线规划，证明业务链路未被地图改动破坏。

## 6. API 验证清单

合并前至少验证：

| 接口 | 验证重点 |
| --- | --- |
| `GET /api/bootstrap` | 保留旧字段，返回 `map_renderer=leaflet_geo`、`fallback_renderer=simple_svg` |
| `GET /api/map/geojson?site_id=PKU` | 返回 84 个 feature、14 个 POI、28 个 waypoint、42 条 edge、40 条 `osm_matched`、2 条 manual、0 条 fallback |
| `GET /api/map/osm-layers?site_id=PKU` | 返回 roads / buildings / water_landuse 本地图层和 stats |
| `POST /api/route` `gate_north -> library` | 5 段 route geometry，fallback 0 |
| `POST /api/route` `gate_north -> canteen` | route geometry 正常，fallback 0 |
| `POST /api/route` `gate_east -> canteen` | route geometry 正常，fallback 0 |
| `POST /api/route/multi` `gate_north + library + canteen` | 多目标 leg geometry stats 正常，fallback 0 |
| `POST /api/search/scenic` | 查询“图书馆”可返回 route target |
| `POST /api/search/places` | 查询“洗手间”可返回 route target 并按距离排序 |
| `POST /api/recommend/catering` | 餐饮推荐可返回 route target |
| `POST /api/diaries/fulltext` | 日记全文检索可返回可规划目标 |

## 7. 测试建议

M12 合并前建议执行：

```powershell
py -m pytest tests/test_ui_demo.py -q
py -m pytest tests/test_routing.py -q
py -m pytest tests/test_search.py -q
py -m pytest tests/test_course_requirements.py -q
py -m pytest
```

## 8. 后续边界

1. 当前 M12 仍是课程设计演示数据，不把完整 OSM 路网作为运行时 routing graph。
2. 真实底图瓦片依赖网络；无底图模式、本地 OSM 图层和 SVG fallback 可继续支持现场演示。
3. 后续扩展前不做路网扩密、核心 POI route matrix、通用质量脚本或多景区模板。
