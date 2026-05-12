# 地图方案 B 最终交付说明

## 1. 交付基线

- 当前分支：`experiment/map-plan-b`
- 文档编写时最新提交：`a586867 docs: finalize map plan b acceptance record`
- 交付阶段：M6 最终交付收口、答辩演示脚本、合并前检查与风险确认
- 启动命令：

```powershell
py -B -m src.ui.demo_server
```

- 访问地址：

```text
http://127.0.0.1:8765
```

本说明只做最终交付和合并准备，不继续扩大 geometry 数据，不接入 OSMnx、Overpass 或外部路网下载，不重写 routing、graph、search、recommend、diary、compress 模块。

## 2. 最终能力概述

地图方案 B 已具备以下最终演示能力：

1. 默认使用 `leaflet_geo` 渲染器展示 Leaflet + GeoJSON 地图实验层。
2. 保留 `simple_svg` 渲染器，可在页面中手动切换，也可作为 Leaflet 或 GeoJSON 加载失败时的稳定回退。
3. `GET /api/map/geojson?site_id=PKU` 输出当前室外节点和道路的 GeoJSON `FeatureCollection`。
4. `/api/bootstrap` 保留旧字段，并新增 `map_renderer`、`map_capabilities` 和地图 geometry 覆盖统计。
5. `/api/route` 和 `/api/route/multi` 返回 `route_geojson`、`route_line_coordinates`、`route_geometry_stats`，用于 Leaflet 路线高亮和 fallback 段说明。
6. 地图区展示 renderer 状态、GeoJSON 节点/道路/geometry 覆盖统计、route geometry 统计、legend 和固定演示按钮。
7. 首页、综合查询、场所查询、美食推荐、导航规划、日记中心、AIGC 演示入口继续保持可用。

## 3. 相比原 SVG 直线图的改进

1. 原 SVG 图仍可用，但默认展示升级为 Leaflet 地图层，支持拖动、缩放和 GeoJSON 图层管理。
2. 道路和节点由后端 GeoJSON 输出驱动，坐标顺序统一为 RFC 7946 的 `[lng, lat]`。
3. 已补充 geometry 的道路可以按折线贴路显示，不再只能在节点之间画直线。
4. 路线高亮优先使用 `route_geojson`，能展示单目标和多目标路线的实际室外折线。
5. 页面直接说明 geometry 覆盖率和 fallback 段数，答辩时可以解释当前阶段的数据覆盖边界。
6. Leaflet 运行库使用本地 vendored 文件，不依赖 CDN 才能加载核心地图渲染逻辑。

## 4. 架构说明

方案 B 采用“算法图不变、表现层增强”的结构：

1. 路由算法仍使用现有图结构、距离和路径规划实现。
2. 后端服务层从现有 outdoor 节点和 edge 生成 GeoJSON：
   - 节点输出为 `Point`。
   - 道路输出为 `LineString`。
   - 有 `geometry` 的 edge 使用手工道路折线。
   - 无 `geometry` 的 edge 使用 from/to 节点坐标生成两点 fallback line。
3. 前端通过 `renderMap()` 在 `leaflet_geo` 和 `simple_svg` 之间分发。
4. Leaflet 初始化由 `renderLeafletMap()` 和 `ensureLeafletMap()` 负责；SVG fallback 由 `renderSvgMap()` 和 `fallbackToSvgMap()` 保留。
5. 路线高亮由 `syncLeafletRouteLayer()` 同步，优先渲染 `route_geojson`；无法渲染真实 route geometry 时仍可回到已有节点路径高亮。
6. `simple_svg` 作为稳定回退，不参与后端算法语义变更。

## 5. 答辩演示脚本

建议现场按以下顺序操作：

1. 启动服务：`py -B -m src.ui.demo_server`。
2. 打开 `http://127.0.0.1:8765`，确认首页加载，说明当前站点和数据规模。
3. 点击“进入主要网站”，进入应用页。
4. 查看右侧地图区，确认默认是 Leaflet GeoJSON 实验层。
5. 说明地图状态条：节点数、道路数、geometry 覆盖数、覆盖率和路线状态。
6. 点击 `演示单目标`，规划 `gate_north -> library`，说明路线为 `gate_north -> square_center -> library`，2/2 段使用 geometry，0 段 fallback。
7. 在单目标路径表单中把目标切到 `canteen`，规划 `gate_north -> canteen`，说明路线为 `gate_north -> square_center -> road_cross -> canteen`，3/3 段使用 geometry，0 段 fallback。
8. 点击 `演示多目标`，规划 `library + canteen` 多目标路线，说明访问顺序为 `gate_north -> canteen -> library -> gate_north`，8/8 段使用 geometry，0 段 fallback。
9. 展示 legend 和 caption，解释 `fallback 直线段` 的含义：不是路径算法失败，只表示该 edge 尚无道路折线。
10. 点击 `SVG`，展示 `simple_svg` 稳定简图；再点击 `Leaflet` 可切回实验层。
11. 可选：进入综合查询搜索“图书馆”，从结果执行地图定位或发起路线规划，证明业务查询链路未受地图改动影响。
12. 可选：进入日记中心检索“图书馆 自习”，从日记结果说明仍可关联路线目标。

## 6. API 验证清单

合并前至少验证以下接口：

| 接口 | 验证重点 |
| --- | --- |
| `GET /api/bootstrap` | 保留原字段，返回 `map_renderer=leaflet_geo`、`map_capabilities.fallback_renderer=simple_svg` |
| `GET /api/map/geojson?site_id=PKU` | 返回 `FeatureCollection`，包含 39 个 node feature、81 条 edge feature、14 条 geometry edge、67 条 fallback edge |
| `POST /api/route` `gate_north -> library` | 成功返回路线、`route_geojson` 和 2/2 geometry 统计 |
| `POST /api/route` `gate_north -> canteen` | 成功返回路线、`route_geojson` 和 3/3 geometry 统计 |
| `POST /api/route/multi` `library + canteen` | 成功返回多目标访问顺序、leg 信息和 8/8 geometry 统计 |
| `POST /api/search/scenic` | 图书馆查询可返回 route target |
| `POST /api/search/places` | 洗手间查询可返回 route target，并可按距离排序 |
| `POST /api/recommend/catering` | 餐饮推荐可返回 route target |
| `POST /api/diaries/fulltext` | 日记全文检索可返回可规划目标 |

## 7. 测试结果

M6 收口前基线测试：

```powershell
py -m pytest
```

结果：

```text
102 passed in 0.87s
```

M6 API smoke check 已覆盖：

1. `GET /api/bootstrap`
2. `GET /api/map/geojson?site_id=PKU`
3. `POST /api/route`：`gate_north -> library`
4. `POST /api/route`：`gate_north -> canteen`
5. `POST /api/route/multi`：`library + canteen`
6. `POST /api/search/scenic`
7. `POST /api/search/places`
8. `POST /api/recommend/catering`
9. `POST /api/diaries/fulltext`

已确认 smoke check 返回 120 个 GeoJSON feature、81 条 edge、14 条 geometry edge、67 条 fallback edge。

M6 浏览器检查已使用 Playwright CLI 访问正式演示地址 `http://127.0.0.1:8765`，并确认：

1. 首页加载成功。
2. 可进入主要网站。
3. Leaflet 地图显示，状态条包含 39 个节点、81 条道路、14 条 geometry edge。
4. `gate_north -> library` 单目标路线高亮，状态为 2/2 段贴路、fallback 0 段。
5. `gate_north -> canteen` 单目标路线高亮，状态为 3/3 段贴路、fallback 0 段。
6. `library + canteen` 多目标路线高亮，状态为 8/8 段贴路、fallback 0 段。
7. 地图 legend 和 caption 可说明 geometry / fallback。
8. 可切换到 `simple_svg`，Leaflet 隐藏，SVG 稳定简图显示。

## 8. 已知限制

1. 当前 geometry 覆盖率为 17.28%，优先覆盖答辩路线，非关键道路仍使用 fallback line。
2. 未接入 OSMnx、Overpass、外部 OSM 数据或商业地图路网。
3. 真实底图瓦片可能受网络影响；Leaflet 本地运行库和 GeoJSON 图层仍可加载，Leaflet 初始化失败时回退 SVG。
4. 路线算法、图加载语义、搜索、推荐、日记和 AIGC 模块未在方案 B 中重写。
5. `simple_svg` 是正式回退能力，不应在合并前删除。
6. 当前 route geometry overlay 以现有图 path 为基础，未做真实路网级别的重新寻路。

## 9. 后续真实地图升级路线

如果目标从课程验收升级为“接近日常地图 App 的真实观感”，建议继续拆成三个阶段：

1. M7：真实瓦片底图接入。用 Leaflet `tileLayer` 加载真实底图，增加底图模式切换、attribution、网络失败回退和合规说明。
2. M8：离线 OSM 数据抽取与本地化。使用 OSMnx 或 Overpass 在准备阶段抽取 PKU 周边 roads / buildings / water / landuse，保存到 `data/sites/PKU/geo/`，运行时读取本地 GeoJSON。
3. M9：课程图 edge 与 OSM 道路线形匹配。课程图仍作为算法权威，OSM 数据只提供更真实的 route geometry；匹配失败时继续使用 `manual` geometry 或 `fallback_line`。

推进顺序必须是 M7 -> M8 -> M9，不建议一次性合并执行。M7 的视觉收益最大且风险最低；M9 最接近真实导航效果，但数据匹配和验证成本最高。

## 10. 回退策略

1. 功能级回退：在页面地图区点击 `SVG`，切换到 `simple_svg` 稳定简图。
2. 自动回退：Leaflet 运行库或 GeoJSON 请求异常时，前端调用 `fallbackToSvgMap()` 并显示错误说明。
3. 数据级回退：edge 缺少 `geometry` 时，后端输出 from/to 两点 `LineString`，并标记 `geometry_source=fallback_line`、`is_fallback_geometry=true`。
4. 分支级回退：合并前如发现不可接受风险，保留 `main` 不变，继续在 `experiment/map-plan-b` 修复。

## 11. 合并 main 前检查清单

- [ ] 确认当前分支仍为 `experiment/map-plan-b`。
- [ ] 运行 `git status --short --branch`，确认没有误 staged 的 `scripts/` 或 `工作进度/` 文件。
- [ ] 运行 `py -m pytest`。
- [ ] 执行 API smoke check 清单中的接口。
- [ ] 启动 `py -B -m src.ui.demo_server`，访问 `http://127.0.0.1:8765`。
- [ ] 浏览器确认首页、主要网站、Leaflet 地图、单目标路线、多目标路线、geometry/fallback 文案和 `simple_svg` 切换。
- [ ] 运行 `git diff --cached --name-status`，确认只 staged 本阶段交付文档或明确的小修复。
- [ ] 合并前确认评审方接受当前 17.28% geometry 覆盖率和 fallback 策略。
- [ ] 不直接合并到 `main`，除非用户明确要求。
