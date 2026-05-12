# 地图方案 B M9 Agent Goal 提示词

## 目标

在当前仓库 `C:\code\Data-Structure-Course-Design` 的 `experiment/map-plan-b` 分支上，完成地图方案 B M9：课程图 edge 与本地 OSM 道路线形匹配，让 route overlay 更贴近日常地图道路。

## 开始前必须执行

1. `git status --short --branch`
2. 确认当前分支是 `experiment/map-plan-b`
3. 阅读 `AGENTS.md`
4. 阅读 `docs/地图方案B真实地图层总路线计划.md` 中“阶段 8：课程图 edge 与 OSM 道路线形匹配”和“M9”
5. 阅读 M8 新增的 OSM 本地化记录文档
6. 检查 `data/sites/PKU/geo/` 下的本地 OSM GeoJSON 和 metadata
7. 运行 `py -m pytest`，确认当前基线通过

## 当前状态

1. M7 已完成真实瓦片底图。
2. M8 已完成本地 OSM roads / buildings / water / landuse 图层。
3. 当前 route geometry 仍主要来自手工 geometry 或 fallback。
4. 本阶段目标是把课程图 edge 映射到本地 OSM roads 的 `LineString`，提升路径贴真实道路的程度。
5. 本阶段不替换 routing 算法，课程图仍是路径规划权威；OSM 只作为可视化 geometry 来源。

## 本阶段目标

1. 建立课程图 edge 到 OSM road geometry 的匹配机制。
2. 为关键课程 edge 生成或保存 `osm_matched` geometry。
3. `route_geojson` 优先使用 `osm_matched` geometry，其次 manual geometry，最后 `fallback_line`。
4. `/api/map/geojson` 和 `/api/route` stats 能说明 geometry 来源。
5. Leaflet route overlay 在真实底图和本地 OSM 道路图层上更贴路。
6. 匹配失败不影响路径规划和 UI 展示。

## 建议新增数据文件

```text
data/sites/PKU/geo/
  edge_osm_geometry_matches.json
```

建议格式：

```json
{
  "metadata": {
    "site_id": "PKU",
    "source": "local_osm_roads",
    "created_at": "2026-05-12",
    "description": "Course graph edge to local OSM road geometry matches"
  },
  "matches": [
    {
      "edge_key": "gate_north->square_center",
      "from": "gate_north",
      "to": "square_center",
      "geometry_source": "osm_matched",
      "confidence": 0.85,
      "osm_way_ids": ["..."],
      "geometry": [
        {"lat": 39.9929, "lng": 116.3055},
        {"lat": 39.9927, "lng": 116.3060}
      ],
      "notes": "Matched to nearest local OSM footway/service road"
    }
  ]
}
```

## 匹配范围优先级

1. `gate_north -> square_center`
2. `square_center -> library`
3. `square_center -> road_cross`
4. `road_cross -> canteen`
5. `road_cross -> gate_east`
6. `road_cross -> teaching_building_1`
7. `road_cross -> teaching_building_2`
8. `road_cross -> dormitory_1`
9. `road_cross -> convenience_store`
10. `gate_south -> teaching_building_1`
11. 与 `sports_ground`、`parking`、`restroom` 相关的演示路线边

## 匹配策略

1. 读取 `data/sites/PKU/geo/osm_roads_simplified.geojson` 或 M8 生成的本地 OSM roads 文件。
2. 对每条课程 edge，使用 from / to 节点坐标，在 OSM roads 中找端点附近或路径附近的 `LineString`。
3. 可先采用半自动策略：对关键 edge 生成候选，并人工选择或直接保存最可信的一条 geometry。
4. 如果自动匹配复杂，允许为关键 edge 基于本地 OSM roads 手工整理 matched geometry，但必须记录 `source=osm_matched` 和 `confidence`。
5. 匹配失败的 edge 保留 manual geometry 或 `fallback_line`。
6. 不要修改 routing 算法，不要把 OSM 图作为路径搜索图。

## 后端要求

1. `DemoUIService` 读取 `edge_osm_geometry_matches.json`。
2. edge geometry 解析优先级：
   - `osm_matched`
   - manual geometry in `outdoor.json`
   - `fallback_line` from / to
3. `/api/map/geojson` 的 edge properties 增加 `geometry_source`、`geometry_confidence`、`osm_way_ids`，如有。
4. `/api/map/geojson` 的 stats 增加：
   - `osm_matched_edge_count`
   - `manual_geometry_edge_count`
   - `fallback_edge_count`
   - `osm_matched_coverage_ratio`
5. `/api/route` 和 `/api/route/multi` 的 `route_geometry_stats` 增加：
   - `osm_matched_segment_count`
   - `manual_geometry_segment_count`
   - `fallback_segment_count`
6. 保留旧字段，不破坏现有 map / route 契约。
7. 反向 edge 能复用正向 `osm_matched` geometry 并 reverse。

## 前端要求

1. Leaflet 普通 project roads 可按 `geometry_source` 做轻微区分。
2. route caption 或 stats 面板显示 route 中 `osm_matched` / `manual` / `fallback` 段数。
3. route overlay 仍保持最高视觉层级。
4. 如果 OSM match 数据缺失，UI 仍正常展示 manual 或 fallback。
5. 本地 OSM roads / buildings / water 图层、真实底图、无底图模式、`simple_svg` fallback 仍可用。

## 测试要求

1. 运行 `py -m pytest`。
2. 更新 `tests/test_ui_demo.py` 或新增测试，覆盖：
   - `edge_osm_geometry_matches.json` 可加载。
   - `/api/map/geojson` stats 包含 `osm_matched_edge_count`。
   - 至少一个关键 edge 使用 `geometry_source=osm_matched`。
   - route `gate_north -> library` 的 `route_geometry_stats` 中 `osm_matched_segment_count > 0`，或 manual fallback 明确可解释。
   - 反向 route 能 reverse 复用 `osm_matched` geometry。
   - 缺失 match 时 fallback 不报错。
3. API smoke check：
   - `GET /api/bootstrap`
   - `GET /api/map/geojson?site_id=PKU`
   - `GET /api/map/osm-layers?site_id=PKU`
   - `POST /api/route gate_north -> library`
   - `POST /api/route gate_east -> canteen`
   - `POST /api/route/multi library + canteen`
4. 如果可行，用浏览器检查：
   - 真实底图显示
   - 本地 OSM 图层显示
   - route overlay 更贴近 OSM roads
   - osm / manual / fallback 统计显示
   - `simple_svg` fallback 可用

## 文档要求

1. 新增或更新 M9 记录文档，例如 `docs/地图方案B第九阶段OSM路线匹配记录.md`。
2. 文档必须说明：
   - 匹配文件路径
   - 匹配策略
   - 已匹配 edge 列表
   - geometry 来源优先级
   - 覆盖率统计
   - 已知限制
   - 如何继续扩展匹配
3. 更新 `docs/地图方案B最终交付说明.md` 或总路线计划中的当前状态。

## 严禁

1. 不要重写 routing 算法。
2. 不要把 OSM 图替换为课程路径规划图。
3. 不要在 Web UI 请求时实时调用 OSMnx 或 Overpass。
4. 不要下载外部瓦片到仓库。
5. 不要破坏 `/api/bootstrap`、`/api/map/geojson`、`/api/map/osm-layers`、`/api/route`、`/api/route/multi` 旧字段。
6. 不要提交 `scripts/` 和 `工作进度/` 下已有无关未跟踪文件。
7. 不要异常终止；如果自动匹配失败，必须用人工匹配关键 edge 的方式完成可用闭环，并记录限制。

## 子 agent 使用规则

1. 可以使用 explorer 子 agent 只读分析 OSM roads GeoJSON、outdoor edge、route overlay 和测试结构。
2. 可以使用一个 worker 只负责文档或测试，不要和主 agent 同时编辑同一文件。
3. 不要让多个 worker 同时修改 `demo_service.py`、`app.js`、`edge_osm_geometry_matches.json`。
4. 主 agent 必须负责匹配数据、后端、前端、测试的最终集成和验证。

## 完成标准

1. `py -m pytest` 通过。
2. `data/sites/PKU/geo/edge_osm_geometry_matches.json` 存在。
3. `/api/map/geojson` 能报告 `osm_matched_edge_count`、`manual_geometry_edge_count`、`fallback_edge_count`。
4. 至少关键演示路线中有 `osm_matched` geometry 被 route overlay 使用。
5. route overlay 在真实底图 + 本地 OSM roads 上更接近日常地图道路。
6. manual geometry 和 `fallback_line` 仍可用。
7. 文档记录匹配策略、覆盖率、限制和扩展方式。
8. `git status` 不包含误 staged 的无关文件。
9. 验证通过后提交为：

```text
feat: match course routes to local osm geometry
```

