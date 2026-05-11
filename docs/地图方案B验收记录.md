# 地图方案 B 验收记录

## 1. 验收范围

- 验收日期：2026-05-11
- 当前分支：`experiment/map-plan-b`
- 验收代码基线提交：`3be0027 feat: polish leaflet map demo experience`
- M4 相关提交已存在：`0051913 feat: add route geometry overlay for leaflet map`、`440bded data: expand map road geometry coverage`、`3be0027 feat: polish leaflet map demo experience`
- 本阶段目标：M5 验收级稳定化、最终演示材料、回退验证与合并前检查。

本记录只确认地图方案 B 已具备验收展示条件，不扩大功能范围，不接入 OSMnx、Overpass 或外部真实路网下载。

## 2. 完成内容

1. 默认地图渲染器为 `leaflet_geo`，可在页面地图区切换到 `simple_svg`。
2. `GET /api/map/geojson?site_id=PKU` 返回当前室外节点和道路的 GeoJSON `FeatureCollection`。
3. `/api/bootstrap` 保留旧字段，并新增 `map_renderer`、`map_capabilities` 和地图 geometry 覆盖统计。
4. `/api/route` 和 `/api/route/multi` 返回 `route_geojson`、`route_line_coordinates` 和 `route_geometry_stats`。
5. Leaflet 使用本地 vendored 资源：`src/ui/static/vendor/leaflet/leaflet.css`、`src/ui/static/vendor/leaflet/leaflet.js`。
6. 前端保留 `renderMap()` 入口，并拆分 `renderSvgMap()`、`renderLeafletMap()`、`ensureLeafletMap()`、`syncLeafletRouteLayer()`、`fallbackToSvgMap()`。
7. 地图区提供 legend、renderer 状态、GeoJSON 统计、route geometry 统计和固定演示按钮。
8. 首页、查询、推荐、路线、日记中心、AIGC 演示入口均在回归检查中保持可用。

## 3. 架构说明

地图方案 B 采用“算法图不变、表现层增强”的架构：

1. 路由算法仍使用现有图结构和路径规划实现。
2. 后端把 outdoor 节点输出为 GeoJSON `Point`，把 outdoor edge 输出为 GeoJSON `LineString`。
3. GeoJSON 坐标顺序统一为 RFC 7946 要求的 `[lng, lat]`。
4. edge 有 `geometry` 时使用手工道路折线；没有 `geometry` 时用 from/to 节点坐标生成两点 fallback line。
5. 前端 Leaflet 只负责展示道路、节点、路线和交互高亮，不改变搜索、推荐、日记或路由核心语义。
6. `simple_svg` 渲染器完整保留，作为现场切换、弱网或 Leaflet 初始化失败时的稳定回退。

## 4. Geometry 覆盖率

统计口径与 `/api/map/geojson?site_id=PKU` 一致：

```text
node_feature_count: 39
edge_feature_count: 81
geometry_edge_count: 14
fallback_edge_count: 67
feature_count: 120
geometry_coverage_ratio: 0.1728
```

当前覆盖率优先保障答辩路线，而不是追求全校园真实路网。剩余 67 条 fallback edge 会以直线段渲染，保证系统不断链。

## 5. 关键演示路线

已验证路线如下：

| 场景 | 验证结果 | route geometry 统计 |
| --- | --- | --- |
| `gate_north -> library` | 通过，路径为 `gate_north -> square_center -> library` | 2/2 段使用 geometry，0 段 fallback |
| `gate_north -> canteen` | 通过，路径为 `gate_north -> square_center -> road_cross -> canteen` | 3/3 段使用 geometry，0 段 fallback |
| `library + canteen` 多目标 | 通过，访问顺序为 `gate_north -> canteen -> library -> gate_north` | 8/8 段使用 geometry，0 段 fallback，3 个 leg feature |
| `gate_east -> canteen` | 通过，路径为 `gate_east -> road_cross -> canteen` | 2/2 段使用 geometry，0 段 fallback |
| `gate_north -> campus_service_01` | 通过，用于证明 fallback 路径不崩 | 0/1 段使用 geometry，1 段 fallback |

## 6. Fallback 含义

本项目有两层 fallback：

1. renderer fallback：Leaflet 或 GeoJSON 加载失败时，前端调用 `fallbackToSvgMap()` 并切回 `simple_svg`。
2. geometry fallback：edge 暂无 `geometry` 时，后端用 source/target 节点生成两点 `LineString`，并在 properties 中标记 `geometry_source=fallback_line`、`is_fallback_geometry=true`。

fallback 不是路径算法失败。它表示当前阶段没有为该 edge 补齐道路折线，但路径规划、步骤列表和地图高亮仍保持可用。

## 7. 演示流程

建议答辩现场按以下顺序展示：

1. 打开 `http://127.0.0.1:8765`，确认首页和主要网站可加载。
2. 进入主要网站，说明默认地图为 Leaflet GeoJSON 实验层。
3. 点击 `SVG`，展示原稳定简图；再点击 `Leaflet`，展示真实地图实验层。
4. 点击 `演示单目标`，展示 `gate_north -> library` 的贴路路线。
5. 点击 `演示多目标`，展示 `library + canteen` 多目标路线和分段高亮。
6. 在综合查询中搜索“图书馆”，点击地图定位或从结果发起路线规划。
7. 打开日记中心做全文检索，确认结果仍能进入路线规划。
8. 打开 AIGC 演示入口，确认轻量分镜预览入口未受地图改动影响。
9. 说明 fallback 直线段和 `simple_svg` 回退方式。

## 8. 测试记录

### 8.1 单元与回归测试

命令：

```powershell
py -m pytest
```

结果：

```text
102 passed in 1.12s
```

覆盖重点：

1. 搜索、推荐、日记、全文检索、压缩、路由和 UI demo 服务均通过。
2. `tests/test_ui_demo.py` 覆盖 GeoJSON 输出、geometry 覆盖统计、route overlay、fallback edge、多目标 route GeoJSON、日记和 AIGC 静态入口。

### 8.2 API smoke check

使用临时本地 HTTP server handler 验证真实 GET/POST 路由分发，11 项全部通过：

| 接口或页面 | 结果 |
| --- | --- |
| `GET /api/bootstrap` | 通过，`map_renderer=leaflet_geo`，`fallback_renderer=simple_svg` |
| `GET /api/map/geojson?site_id=PKU` | 通过，120 个 feature，81 条 edge，14 条 geometry，67 条 fallback |
| `POST /api/search/scenic` | 通过，图书馆查询可返回 route target |
| `POST /api/search/places` | 通过，洗手间查询可返回 route target |
| `POST /api/recommend/catering` | 通过，美食推荐可返回 route target |
| `POST /api/route` `gate_north -> library` | 通过 |
| `POST /api/route` `gate_north -> canteen` | 通过 |
| `POST /api/route` `gate_east -> canteen` | 通过 |
| `POST /api/route` fallback edge | 通过，`fallback_segment_count=1` |
| `POST /api/route/multi` `library + canteen` | 通过 |
| `POST /api/diaries/fulltext` | 通过，日记结果可返回 route target |

### 8.3 浏览器检查

工具：Chrome + Playwright CLI，访问临时本地演示服务端口；正式演示入口仍为 `http://127.0.0.1:8765`。

已检查：

1. 首页加载。
2. 主要网站地图区显示。
3. Leaflet 地图模式显示。
4. `SVG` / `Leaflet` 切换可用。
5. 综合查询后地图定位可用。
6. 查询结果发起路线规划可用。
7. 单目标路线规划可用。
8. 多目标路线规划可用。
9. 日记中心入口可用。
10. AIGC 演示入口可用。

浏览器初检发现 `/favicon.ico` 404，已通过首页内联 favicon 修复，不影响业务功能。

## 9. 已知限制

1. 当前 geometry 覆盖率为 17.28%，优先覆盖答辩路线，非关键 edge 仍使用 fallback line。
2. 没有接入 OSMnx、Overpass 或外部路网下载。
3. 真实底图瓦片若受网络影响，Leaflet 仍可显示本地 GeoJSON 图层；如 Leaflet 初始化失败则回退 SVG。
4. 路由算法、图加载语义、搜索、推荐、日记和 AIGC 模块未因地图方案 B 改写。
5. `simple_svg` 仍是稳定回退，不应在合并前删除。

## 10. 合并前检查清单

- [ ] 确认分支仍是 `experiment/map-plan-b`。
- [ ] 再次运行 `py -m pytest`。
- [ ] 再次运行 API smoke check。
- [ ] 确认浏览器中 Leaflet 和 `simple_svg` 均可切换。
- [ ] 确认 `git status --short` 中没有误 staged 的 `scripts/` 或 `工作进度/` 未跟踪文件。
- [ ] 确认 `git diff --cached --name-status` 只包含本阶段文档和小型 UI 稳定性修复。
- [ ] 合并前保留本分支回退方式：功能级切回 `simple_svg`，分支级回退到 `main`。
