# 地图方案 B 第十二阶段精细化真实地图打磨记录

## 阶段目标

M12 基于 M10 真实数据重制和 M11 穿楼边清理继续精修展示质量。目标不是重写 routing 算法，而是让运行时地图更像真实校园导览系统：用户第一眼看到 POI、真实道路和路线，内部路网点只作为低视觉权重的路线支撑点。

运行时边界保持不变：课程图仍是路径规划权威；Web UI 不调用高德、OSMnx 或 Overpass；API 旧字段只做 additive 扩展。

## 节点名称和显示规则

M10/M11 已将旧 `campus_service_*` 运行时节点替换为语义化 `road_*` waypoint。M12 继续采用“保留语义化 road id、弱化 waypoint 显示”的策略：

- 运行时 `outdoor.json` 和 `edge_osm_geometry_matches.json` 不包含 `campus_service_*`。
- 原 M11 新增的南门和农园南侧路网点改为自然中文名：`南门内侧五四路口`、`农园南路西口`、`农园南路东口`。
- 核心 POI 的 `tags`、`description` 重新整理为自然中文，不再保留乱码、`???` 或工程化占位说明。
- `road` 类节点统一作为 waypoint：用于路线贴合真实道路，但不作为普通搜索目的地。

后端 GeoJSON node properties 新增 additive 字段：

```json
{
  "display_role": "poi | waypoint",
  "is_waypoint": true,
  "label_priority": 10,
  "show_label": false,
  "is_searchable": false
}
```

当前统计：

| 项目 | 数量 |
| --- | ---: |
| POI node | 14 |
| waypoint node | 28 |
| undirected edge | 42 |
| OSM matched edge | 40 |
| manual edge | 2 |
| fallback edge | 0 |
| geometry coverage | 1.0000 |

## Geometry 审计

新增审计文件：

```text
data/sites/PKU/geo/M12_visual_audit.json
```

审计结果：

- 42 条无向 edge 均标记 `accepted`。
- `fallback_edge_count=0`。
- 当前 match 表中无 `confidence < 0.72` 的低置信度边。
- 两条 manual edge 仍为洗手间短接入边：`library -> toilet_lib_area` 路线中最后一段、`sports_ground -> toilet_sports_area`。

## 关键路线验收

| Route | segment | OSM | manual | fallback |
| --- | ---: | ---: | ---: | ---: |
| `gate_north -> library` | 5 | 5 | 0 | 0 |
| `gate_north -> canteen` | 11 | 11 | 0 | 0 |
| `gate_east -> canteen` | 11 | 11 | 0 | 0 |
| `gate_south -> teaching_building_1` | 7 | 7 | 0 | 0 |
| `library -> sports_ground` | 8 | 8 | 0 | 0 |
| `library -> canteen` | 10 | 10 | 0 | 0 |
| `gate_north -> sports_ground` | 9 | 9 | 0 | 0 |
| `gate_east -> parking_lot` | 1 | 1 | 0 | 0 |
| `library -> toilet_lib_area` | 8 | 7 | 1 | 0 |
| `sports_ground -> toilet_sports_area` | 1 | 0 | 1 | 0 |

多目标路线：

| Multi route | segment | OSM | manual | fallback |
| --- | ---: | ---: | ---: | ---: |
| `gate_north -> library -> canteen` | 26 | 26 | 0 | 0 |
| `gate_east -> teaching_building_2 -> dormitory_1 -> canteen` | 32 | 32 | 0 | 0 |
| `gate_south -> teaching_building_1 -> library -> sports_ground` | 26 | 26 | 0 | 0 |

## UI 打磨

- 地图区标题改为“校园真实地图”，去掉“实验层”措辞。
- 地图状态条显示 `POI 14 · 路网点 28 · 道路 42 · OSM 40 · manual 2 · fallback 0 (100%)`。
- Leaflet POI 使用较明显 marker 和 hover tooltip；waypoint 使用小半径、低透明度 marker，默认无标签。
- waypoint popup 不提供“从当前起点规划路线”按钮，只说明其为道路接驳点。
- 搜索和 route target 列表过滤 `road` / `waypoint`，避免路口点作为普通地点结果干扰用户。
- route caption 改为“室外路线已沿真实道路高亮”，并保留 OSM/manual/fallback 统计用于答辩解释。
- SVG fallback 保持可用，并同步弱化 waypoint 与隐藏 waypoint 标签。

## 验证记录

聚焦测试：

```powershell
py -m pytest tests/test_ui_demo.py -q
py -m pytest tests/test_routing.py -q
py -m pytest tests/test_search.py -q
py -m pytest tests/test_course_requirements.py -q
```

结果：

```text
27 passed
19 passed
23 passed
4 passed
```

完整测试：

```powershell
py -m pytest
```

结果：

```text
111 passed in 1.36s
```

API smoke check 使用临时内存 HTTP server 通过，覆盖：

- `GET /api/bootstrap`
- `GET /api/map/geojson?site_id=PKU`
- `GET /api/map/osm-layers?site_id=PKU`
- 10 条 M12 单目标路线，全部 `fallback_segment_count=0`
- 3 条 M12 多目标路线，全部 `fallback_segment_count=0`
- `POST /api/search/scenic`
- `POST /api/search/places`
- `POST /api/recommend/catering`
- `POST /api/diaries/fulltext`

浏览器验收使用临时端口 `8898` 和 Playwright CLI 通过：

- Leaflet 默认地图加载，状态条显示 POI / waypoint / OSM / manual / fallback 统计。
- `演示单目标` 后 route 状态显示 `路线真实线形 5/5 · OSM 5 · manual 0 · fallback 0`。
- 页面正文不包含 `campus_service` 或 `???`。
- Canvas / SVG 元素均非空，route overlay 可见。
- 切换 `无底图` 后 caption 显示无底图模式，本地 GeoJSON 图层继续可用。
- 切换 `SVG` fallback 后 Leaflet 隐藏，SVG 渲染 122 个图形元素，路线统计保留。

## 已知限制和后续建议

- M12 仍是课程设计演示数据，不把完整 OSM road network 作为运行时 routing graph。
- waypoint 在路线步骤中仍会以自然中文路口名出现，方便解释路线经过的真实道路；普通搜索和地图默认标签中已隐藏或弱化。
- 后续如需进一步贴近生产地图，可补充更精细的建筑入口 POI、无障碍通行标记和合规瓦片服务。
