# 地图方案 B M25A PKU 多校园复制依赖审计

## 范围

本文只执行 M25A：审计当前 `PKU` 实现中与后续多校园复制直接相关的依赖点。本文不是新校园最小字段清单、不是模板脚手架、也不创建任何真实新校园数据。

主要审计对象：

- `data/global_sites.json`
- `data/sites/PKU/outdoor.json`
- `data/sites/PKU/indoor_*.json`
- `data/sites/PKU/geo/`
- `src/graph/loader.py`
- `src/search/search_service.py`
- `src/recommend/catering_service.py`
- `src/recommend/interest.py`
- `src/routing/router.py`
- `src/ui/demo_service.py`
- `src/ui/demo_server.py`
- `src/ui/static/index.html`
- `src/ui/static/app.js`

## 复制依赖总览

后续校园复制不能只拷贝 `outdoor.json`。当前 PKU 可演示能力依赖七组契约同时成立：

1. 站点注册：`global_sites.json` 中的 `id/name/description/location/sub_graphs` 决定图文件加载顺序和前端站点列表。
2. 图加载：`GraphLoader.load_site_graph(site_id)` 将 `outdoor.json` 与 `indoor_*.json` 合并为一张路由图，并通过室外 `sub_graph_id` 与室内 `is_gate=true` 自动补 `gate_link`。
3. Bootstrap：`DemoUIService(site_id).get_bootstrap_payload()` 输出站点、地图、起点、目标、控件、室内建筑、用户、统计和能力声明。
4. 查询推荐：`load_site_records(site_id)` 从该站点所有图节点生成搜索记录，`DemoUIService` 再过滤掉 `road/waypoint` 类弱化路网点。
5. 路由：`Router` 只以合并后的课程图为权威，要求所有可规划起点和目标节点都在同一个站点图中。
6. 室内入口：`geo/indoor_building_registry.json`、室外入口节点、室内图 `is_gate=true` 节点三者必须互相指向。
7. 前端切换：前端以 `/api/bootstrap?site_id=...` 重建页面状态，并在所有 POST 请求中自动附加当前 `site_id`。

## 图加载契约

代码入口：

- `src/graph/loader.py`
- `src/search/search_service.py`
- `src/search/distance_adapter.py`
- `src/ui/demo_service.py`

必须保持的契约：

- 站点目录固定为 `data/sites/<SITE_ID>/`。
- `global_sites.json` 的 `sub_graphs` 是优先加载清单；若存在，loader 只加载清单中实际存在的 `<name>.json`。
- `outdoor` 图文件名必须是 `outdoor.json`，室内图通常是 `indoor_*.json`。
- 每个图文件顶层至少依赖 `nodes`、`edges`；`graph_type` 缺省时由文件名推断。
- 每个节点必须有唯一 `id`。loader 会把其他字段原样放入 `graph.nodes[node_id]`，并补充 `source_sub_graph_id` 和 `graph_type`。
- 每条边必须有 `from`、`to`、`distance`；可选但已被路由或 UI 使用的字段包括 `congestion`、`ideal_speed`、`type`、`vehicle_access`、`allowed_transports`、`transport_speeds`、`name`、`description`、`geometry`。
- 室外节点若有 `sub_graph_id`，会被视为室内入口候选；对应室内图中所有 `is_gate=true` 节点会自动与该室外节点建立双向 `gate_link`，距离为 0。

复制风险：

- `sub_graphs` 中声明了不存在的图文件时不会报错，但该子图不会进入路由图，可能导致前端站点显示可用而功能缺失。
- 室内图节点 ID 与室外节点 ID 共用同一个合并图命名空间，后续校园必须避免同站点内重复 ID。
- `GraphLoader` 不读取 `geo/indoor_building_registry.json`；它只看室外节点 `sub_graph_id` 和室内节点 `is_gate`。室内注册表只服务 UI 和室内地图接口。

## Bootstrap 契约

代码入口：

- `src/ui/demo_service.py`
- `src/ui/demo_server.py`

稳定输出字段必须只增不减：

- `product`
- `sites`
- `site`
- `users`
- `default_user_id`
- `navigation`
- `help`
- `state_policy`
- `feedback_messages`
- `default_start_node`
- `start_nodes`
- `route_targets`
- `controls`
- `presets`
- `map_renderer`
- `map_capabilities`
- `indoor_buildings`
- `map`
- `stats`

关键依赖：

- `sites` 来自 `load_global_sites()`，每个站点的 `is_available` 由 `get_site_graph_paths(site_id)` 是否找到图文件决定。
- `site` 来自 `global_sites.json`；找不到时会退化为只含 `id/name/description/location` 的空元信息。
- `default_start_node` 优先使用 `gate_north`、`gate_east`、`gate_south`、`library`，否则取第一个可用起点或任一图节点。
- `start_nodes` 来自有经纬度的室外非 `road` 节点。
- `route_targets` 来自合并图中所有非 `road/waypoint` 节点，包含室外和室内目标。
- `map.nodes/map.edges` 只来自 `outdoor.json` 且只包含有 `location.lat/lng` 的节点。
- `map_capabilities` 声明本地 GeoJSON、OSM 图层、Leaflet/SVG 渲染器、室内地图端点和室内支持建筑。

复制风险：

- 新站点即使只有 `outdoor.json` 也可能出现在站点列表中；若图节点过少，`default_start_node`、查询、路由会退化或失败。
- `DEFAULT_PRESETS` 目前仍包含 PKU 目标 ID，如 `library`、`canteen`、`dorm1_room_101`。后续复制阶段要么保证这些通用 ID 存在，要么改成站点化预设；M25A 不做此改动。

## 搜索与场所查询契约

代码入口：

- `src/search/search_service.py`
- `src/search/exact_search.py`
- `src/search/fuzzy_search.py`
- `src/ui/demo_service.py`

数据来源和转换：

- `load_site_records(site_id)` 读取当前站点 `sub_graphs` 对应的所有图 JSON。
- `normalize_site_graph_records(...)` 把每个图节点转为搜索记录，保留 `id/node_id/map_node_id/site_id/name/category/heat/rating/tags/keywords/description/type/graph_type/source_graph_id/source_graph_file/sub_graph_id/is_gate/is_indoor/indoor_building/building_name/facilities/open_hours`。
- `DemoUIService._filter_searchable_site_records(...)` 会过滤 `category == road` 或 `type == waypoint` 的弱化路网点。

查询入口：

- 综合查询：`POST /api/search/scenic` -> `DemoUIService.scenic_search()` -> `search_and_recommend(...)`。
- 场所查询：`POST /api/search/places` -> `DemoUIService.place_search()` -> `search_places(...)`。
- 附近查询：`search_places(...)` 在传入 `center_node_id` 时走 `search_nearby_places(...)`，距离来自当前站点路由图。

类别依赖：

- 场所查询只接受 `PLACE_CATEGORY_SET`：`restroom`、`catering`、`shopping`、`parking`、`education`、`building`、`building_entrance`、`sports`、`service`、`landmark`。
- 类别别名由 `exact_search.CATEGORY_ALIASES` 归一化，后续校园应复用现有英文标准类目。

复制风险：

- 搜索记录的 `site_id` 是加载时注入的，不来自原始节点；但用户、日记等独立数据源另有站点字段。
- 查询结果能否规划路线依赖 `node_id/map_node_id` 是否存在于当前站点图，且弱化路网点不会作为普通搜索结果出现。
- 附近查询要求 `center_node_id` 在当前 `self.graph.nodes` 中，否则服务层返回错误。

## 推荐契约

代码入口：

- `src/recommend/catering_service.py`
- `src/recommend/interest.py`
- `src/ui/demo_service.py`

餐饮推荐：

- `POST /api/recommend/catering` 固定筛选 `category == catering`。
- 可按 `keyword`、`cuisine`、`heat/rating/distance_m` 排序。
- 距离排序依赖 `DemoUIService._distance_provider()`，即当前站点 `Router.query_distance(...)`。

兴趣推荐：

- 用户样本来自 `data/users.json`，`load_users(site_id=...)` 只加载 `home_site_id` 等于当前站点的用户。
- `CATEGORY_INTEREST_TERMS` 将标准类目映射到兴趣词，综合查询和日记推荐会复用这些规则。
- 当前 PKU 用户全部是 `home_site_id: PKU`；后续校园如果没有用户样本，前端用户列表和兴趣选项会为空，但核心查询仍可运行。

复制风险：

- `CATEGORY_INTEREST_TERMS` 是全局语义表，不是按校园配置；后续校园应先复用标准类别，再逐校校准兴趣词。
- 餐饮结果需要 `tags/facilities/keywords/description` 中可匹配菜系或关键词，否则只能按全部餐饮排序。

## 路由契约

代码入口：

- `src/routing/router.py`
- `src/ui/demo_service.py`

稳定接口：

- `POST /api/route`
- `POST /api/route/multi`

请求依赖：

- 单目标至少需要 `start_node_id`、`target_node_id`；服务层会把空起点归一到当前站点默认起点。
- 多目标至少需要 `target_node_ids`；最多支持 12 个去重后的目标。
- `strategy` 支持 `shortest_distance`、`shortest_time`。
- `transport_mode` 支持 `walk`、`bike`、`mixed` 及若干别名。
- `site_id` 由 server 选中对应 `DemoUIService`；`Router` 还会校验传入 `site_id` 与当前图一致。

图边依赖：

- 最短距离直接使用 `distance`。
- 最短时间使用 `distance / ideal_speed / congestion`，并可读取 `transport_speeds`、`ideal_speeds`、`speed_by_transport`、`transport_congestion`、`congestion_by_transport`。
- 交通限制读取 `allowed_transports`、`transport_modes`、`transport_mode`、`blocked_transports`、`vehicle_access`。
- 室内边和 `gate_link` 强制只能步行。

UI 叠加依赖：

- 路线响应会被 `DemoUIService` 补充 `ui.route_geojson`、`ui.mappable_path_node_ids`、`ui.highlight_node_ids`、`ui.indoor_route_views`、`ui.available_route_views`、`ui.default_route_view`、`ui.route_geometry_stats`。
- 室外路线 GeoJSON 只拼接可映射的室外边；室内段会进入室内路线视图，不强行画到室外 Leaflet 层。

复制风险：

- 可搜索目标不等于可达目标；必须存在连接边，否则路由返回不可达。
- 室外 POI 若没有接入道路网络，搜索可命中但路线不可达。
- 交通方式校准依赖边字段，不能只调前端文案。

## 室内入口契约

数据入口：

- `data/sites/PKU/geo/indoor_building_registry.json`
- `data/sites/PKU/geo/indoor_template_catalog.json`
- `data/sites/PKU/indoor_*.json`
- `data/sites/PKU/outdoor.json`

注册表字段依赖：

- `building_id`
- `building_name`
- `entry_node_id`
- `indoor_graph_id`
- `template_id`
- `floor_ids`
- `default_floor_id`
- `entry_mapping_reason`

室外入口节点依赖：

- 节点 ID 通常等于 `building_id` 或注册表中的 `entry_node_id`。
- 若要让 loader 自动接通室内图，室外节点必须有 `sub_graph_id: <indoor_graph_id>`。
- 若要让前端识别室内能力，节点应带 `indoor_supported: true`、`indoor_graph_id`、`indoor_entry_node_id`，或能被注册表通过 `building_id/indoor_graph_id` 反查。

室内图依赖：

- 顶层字段包括 `graph_type: indoor`、`building_id`、`building_name`、`template_id`、`default_floor_id`、`floor_ids`、`nodes`、`edges`。
- 室内入口节点必须 `is_gate: true`，并通常带 `floor_id`、`floor_label`、`layout`。
- 室内可渲染区域依赖节点 `category`、`layout.x/y`、`facilities`、`tags`；跨楼层依赖边和节点的 `floor_id`。

复制风险：

- 注册表存在但室外节点没有 `sub_graph_id` 时，前端可能显示室内建筑，但路由图不会自动连通室内入口。
- 室内图存在但未列入 `global_sites.sub_graphs` 时，loader 不会加载该图，室内路径不可达。
- 注册表的 `entry_node_id`、室外入口节点、室内 `is_gate` 节点三者不一致时，室内地图、室内外路线视图和实际路由可能各自表现不同。

## 地图与 GeoJSON 契约

代码入口：

- `src/ui/demo_service.py`
- `src/ui/static/app.js`

后端输出：

- `GET /api/map/geojson?site_id=<SITE_ID>` 返回 `success/site_id/geojson/stats`。
- 节点 Feature 使用 `Point`，坐标顺序为 `[lng, lat]`，属性至少含 `kind/id/name/category/category_label`，并会扩展路线锚点、室内能力和 OSM 来源字段。
- 边 Feature 使用 `LineString`，坐标顺序为 `[lng, lat]`，属性至少含 `kind/from/to/name/edge_type/distance_m`，并会扩展交通、几何来源和 OSM 匹配字段。
- 边几何优先级：`edge_osm_geometry_matches.json` 匹配结果、`outdoor.json` 中的 `geometry`、源/目标节点直线 fallback。
- `GET /api/map/osm-layers?site_id=<SITE_ID>` 读取 `geo/osm_roads_simplified.geojson`、`geo/osm_buildings.geojson`、`geo/osm_water_landuse.geojson`；缺失时返回空 FeatureCollection 和 warnings，不应破坏核心地图。

前端依赖：

- Leaflet 静态资源必须来自 `/vendor/leaflet/leaflet.css` 和 `/vendor/leaflet/leaflet.js`。
- `renderMap()` 根据当前 `state.mapRenderer` 在 `leaflet_geo` 和 `simple_svg` 之间切换。
- `loadMapGeoJson()` 和 `loadOsmLayers()` 会按当前 `site_id` 缓存数据，站点切换会清空缓存。
- `syncLeafletRouteLayer()` 优先渲染 `route.ui.route_geojson`，失败或缺失时回退到 `ui.mappable_path_node_ids`。
- `fallbackToSvgMap()` 会在 Leaflet 初始化或 GeoJSON 加载失败时切回 SVG 简图。

复制风险：

- `map.nodes` 只接收有 `location.lat/lng` 的室外节点；缺坐标节点仍可进路由图，但不会显示在室外地图上。
- OSM 图层是本地上下文图层，不是路由权威；后续校园不能让前端直接调用 OSMnx/Overpass。
- `edge_osm_geometry_matches.json` 是可选增强；缺失时核心路线仍应走课程图与 fallback 几何。

## 前端站点切换契约

代码入口：

- `src/ui/static/index.html`
- `src/ui/static/app.js`
- `src/ui/demo_server.py`

切换流程：

- 页面启动或选择站点时调用 `loadSiteBootstrap(siteId)`。
- Bootstrap 成功后重建 `state.bootstrap`、地图 renderer、OSM/GeoJSON 缓存、室内状态、起点和表单选项。
- `apiPost()` 会自动把 `currentSiteId()` 写入请求体，除非请求体已经显式提供 `site_id`。
- server 的 `resolve_service(site_id)` 按站点缓存 `DemoUIService`，所有 GET/POST API 都在选中的站点服务实例上执行。

必须保持的状态重置：

- `current_results`
- `current_route`
- `focused_node`
- `forms`
- `map_highlight`
- `indoor` 状态和室内 payload 缓存
- `mapGeoJson/osmLayers` 缓存及其 `site_id`

复制风险：

- 如果某站点 `route_targets` 中不存在 PKU 预设 ID，前端下拉会正常按 bootstrap 填充，但演示预设按钮可能失效。
- 如果 `sites[].is_available=false`，前端会禁用该站点；只创建目录但没有可加载图文件不会进入可切换运行态。

## M25A 后续交接

后续阶段应在本文基础上继续拆分：

- M25B：把上述依赖整理成新校园最小必备字段清单，并区分固定契约与可自定义字段。
- M25C：基于 M25B 生成模板文件或脚手架脚本。
- M25D：整理单校复制自检清单和禁区说明。

M25A 明确禁止事项仍然适用：不创建真实新校园数据、不改稳定 API 契约、不改路由算法、不进入 M26 试点实现。
