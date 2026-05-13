# 地图方案 B 第十阶段真实数据重制记录

## 阶段目标

M10 在 M9 已完成 OSM 路线匹配的基础上，按补充后的“高德真实数据强化”要求重制 PKU 室外课程图数据。目标是消除旧的规则网格 waypoint、校准公开地点名称与坐标、让关键演示路线沿真实道路或步道显示，并继续保持课程图为 routing authority。

运行时边界不变：Web UI 只读取本地 JSON / GeoJSON，不调用高德 API、OSMnx、Overpass，也不重写 Dijkstra、Floyd、多目标路线等核心路由算法。

## 数据变更摘要

| 项目 | M9 基线 | M10 当前 |
| --- | ---: | ---: |
| outdoor node | 39 | 39 |
| directed edge | 162 | 90 |
| undirected map edge | 81 | 45 |
| GeoJSON feature | 120 | 84 |
| osm matched edge | 13 | 43 |
| manual geometry edge | 1 | 2 |
| fallback edge | 67 | 0 |
| geometry coverage ratio | 0.1728 | 1.0000 |
| osm matched coverage ratio | 0.1605 | 0.9556 |

## 节点处理

公开地点节点保留业务 id，并按本地 OSM building / road / footway 校准坐标和显示名称：

- `gate_north` 保留兼容 id，显示为“北京大学西门”，坐标对齐西门内侧步道。
- `gate_east`、`gate_south` 对齐东门、南门道路接驳点。
- `library` 显示为常用名称“图书馆”，坐标对齐图书馆建筑与未名湖南侧步道。
- `teaching_building_1`、`teaching_building_2` 对齐第一教学楼、第二教学楼 OSM 建筑轮廓。
- `dormitory_1` 显示为“学生宿舍31楼”，位置对齐西南宿舍区 31 楼附近道路。
- `canteen` 对齐农园食堂建筑与南侧步道入口。
- `convenience_store` 显示为“中关新园超市”，位置对齐本地 OSM 超市标注。
- `sports_ground`、`square_center`、`parking_lot` 和两个洗手间接入点对齐附近真实道路或步道。

## 虚拟节点替换

补充指令要求不再把 `campus_service_*` 作为运行时课程图节点。M10 当前已将原 24 个旧网格 id 全部替换为语义化 `road_*` waypoint，例如：

- `road_west_gate_inner`：西门内侧步道口。
- `road_lake_southeast_footway`：未名湖东南步道。
- `road_library_south`：图书馆南侧步道口。
- `road_east_gate_south`：东门南侧路口。
- `road_nongyuan_west_south`：农园西路南口。
- `road_second_teaching_west`：二教西路南口。
- `road_yannan_east`：燕南路东口。

运行时 `outdoor.json` 和 `edge_osm_geometry_matches.json` 不再包含旧 `campus_service_*` id，也不再包含 `???` 名称。替换决策记录在：

```text
data/sites/PKU/geo/node_rebuild_decisions.json
```

## 边拓扑处理

M10 删除旧规则网格边，保留 45 条无向课程图边，并输出 90 条 directed edge 供现有 graph loader 使用：

- 北侧主线：西门、未名湖南侧步道、未名湖东南路口、成府园南路、东门。
- 中部主线：图书馆、五四体育场、第一教学楼、理教西路、科学路。
- 南侧主线：南门、农园食堂、第二教学楼、百讲广场、燕南路、宿舍区。
- 东侧支线：东门、停车场、科学路东口、中关新园超市。

所有 edge distance 按对应 geometry 折线长度重新计算；双向边距离保持一致。`gate_east <-> parking_lot` 保持 `vehicle_only`，继续覆盖交通方式过滤测试。

## Geometry 来源

`edge_osm_geometry_matches.json` 已从 M9 的 13 条扩展到 43 条 `osm_matched` 记录。两条洗手间短接入边没有明确 OSM toilet POI，保留为 `manual` geometry：

- `library <-> toilet_lib_area`
- `sports_ground <-> toilet_sports_area`

当前 `/api/map/geojson?site_id=PKU` stats：

```json
{
  "node_feature_count": 39,
  "edge_feature_count": 45,
  "feature_count": 84,
  "geometry_edge_count": 45,
  "osm_matched_edge_count": 43,
  "manual_geometry_edge_count": 2,
  "fallback_edge_count": 0,
  "geometry_coverage_ratio": 1.0,
  "osm_matched_coverage_ratio": 0.9556
}
```

## 关键路线验证

| Route | Path 摘要 | route_segment_count | osm_matched | manual | fallback |
| --- | --- | ---: | ---: | ---: | ---: |
| `gate_north -> library` | `gate_north -> road_west_gate_inner -> road_lake_southeast_footway -> road_lake_southeast -> road_library_south -> library` | 5 | 5 | 0 | 0 |
| `gate_north -> canteen` | 西门经未名湖东南、理教西路、农园西路到农园食堂 | 8 | 8 | 0 | 0 |
| `gate_east -> canteen` | 东门经成府园南路、理教西路、农园西路到农园食堂 | 8 | 8 | 0 | 0 |
| `gate_south -> teaching_building_1` | 南门经农园、二教西侧、理教西路、五四路到第一教学楼 | 8 | 8 | 0 | 0 |
| `library -> sports_ground` | 图书馆经未名湖南侧、理教北侧、五四路北侧到体育场 | 7 | 7 | 0 | 0 |
| `library -> canteen` | 图书馆经未名湖东南、理教西路、农园西侧到食堂 | 7 | 7 | 0 | 0 |
| multi `gate_north + library + canteen` | algorithm-optimized visit order | 20 | 20 | 0 | 0 |
| multi `gate_east + teaching_building_2 + dormitory_1 + canteen` | algorithm-optimized visit order | 23 | 23 | 0 | 0 |

## 高德数据策略

本阶段采用补充指令建议的方案 A：继续使用当前 Leaflet/OSM 架构，高德 API 只允许作为离线 POI、地理编码和步行路径参考。最终落库坐标仍按当前 Leaflet/OSM 图层校准，避免高德坐标与 OSM/WGS84 图层直接混用导致偏移。

仓库未写入任何高德 key；运行时 UI 不调用高德服务。

## 已知限制

- 本阶段仍是课程设计演示数据，不把完整 OSM road network 转成运行时路由图。
- 个别建筑入口和洗手间点为人工吸附到附近路段，后续可继续用实地 POI 或更完整 OSM POI 数据校准。
- 多目标路线仍由现有最短路 + DP 策略决定访问顺序，本阶段未改算法。

## 验证记录

已更新单元测试以覆盖 M10 统计、语义化 waypoint、核心路线无 fallback、反向 geometry 复用、缺失 match 文件时 manual geometry 兜底、以及 API 字段兼容。

实际执行：

```powershell
py -m pytest
```

结果：

```text
109 passed in 1.23s
```

API smoke check 使用临时内存 HTTP server 覆盖：

- `GET /api/health`
- `GET /api/bootstrap?site_id=PKU`
- `GET /api/map/geojson?site_id=PKU`
- `GET /api/map/osm-layers?site_id=PKU`
- `POST /api/route`：6 条核心路线，全部 fallback 0
- `POST /api/route/multi`：2 条多目标路线，全部 fallback 0
- `POST /api/search/scenic`
- `POST /api/search/places`
- `POST /api/recommend/catering`
- `POST /api/diaries/fulltext`

浏览器 smoke check 使用临时端口 `8895` 和系统 Chrome 验证：

- Leaflet 默认地图加载，状态条显示 `节点 39 · 道路 45 · OSM 43 · manual 2 · fallback 0 (100%)`。
- 本地 OSM 状态条显示 `本地 OSM 932 项 · 3 层开启`。
- `gate_north -> library` 单目标路线状态显示 `路线 OSM 5/5 · manual 0 · fallback 0`。
- Canvas 像素检查确认路线高亮已绘制。
- 切换无底图模式后，本地 OSM 图层仍保持开启。
- 切换 `SVG` 后 Leaflet 隐藏，SVG fallback 渲染出 91 个图形元素。
