# 地图方案 B M25B 新校园最小必备字段清单

## 范围

本文只执行 M25B：基于当前 `PKU` 基线和 `docs/地图方案B_M25A_PKU多校园复制依赖审计.md`，整理后续新增校园所需的最小数据字段清单。

本文不创建具体新校园数据，不生成脚本、模板或脚手架，不进入 M25C、M25D、M26 或后续阶段。

## 最小可运行口径

新增校园的最小数据目标不是复制 PKU 的全部数据量，而是让该校园在现有代码契约下可以被独立加载、显示、查询、推荐和规划路线。

最小可运行校园至少需要：

1. `data/global_sites.json` 中存在该校园注册项。
2. `data/sites/<SITE_ID>/outdoor.json` 存在，并包含可加载的 `nodes` 与 `edges`。
3. 室外 POI、校门、道路节点都有可用于地图展示的 `location.lat/lng`。
4. 主要 POI 与道路网络通过边连通，且每条边有 `from/to/distance`。
5. 查询、推荐和路由所依赖的字段名保持与 PKU 兼容。

室内图、OSM 背景层、兴趣用户样本和精细 POI 文案是按能力启用的条件项；如果某校园不声明这些能力，它们不是新增校园的硬性最小字段。

## 必须保持兼容的 PKU 固定契约

下表列出字段名、文件名和语义必须与 PKU 保持兼容的部分。新增校园可以更换字段值，但不能更换这些字段名、目录位置或基本类型。

| 范围 | 固定契约 | 最小要求 |
| --- | --- | --- |
| 站点目录 | `data/sites/<SITE_ID>/` | `<SITE_ID>` 必须与 `global_sites.json` 中的 `id` 完全一致。 |
| 全局注册 | `data/global_sites.json` 顶层 `sites[]` | 每个站点项保留 `id/name/description/location/sub_graphs`。 |
| 子图声明 | `sub_graphs` | 条目是图文件 stem，例如 `outdoor` 对应 `outdoor.json`；声明的图必须存在才会被加载。 |
| 室外图入口 | `data/sites/<SITE_ID>/outdoor.json` | 文件名固定为 `outdoor.json`；后端和 UI 按这个入口构建室外地图。 |
| 图文件顶层 | `graph_id/graph_type/nodes/edges` | `nodes`、`edges` 必须是数组；`graph_type` 对室外图应为 `outdoor`。 |
| 节点主键 | `nodes[].id` | 同一校园合并图内全局唯一，非空字符串。室外和室内节点共享命名空间。 |
| 节点名称 | `nodes[].name` | 用于搜索结果、路线目标、地图标签和 UI 下拉。 |
| 节点类别 | `nodes[].category` | 使用现有标准英文类别；`road` 或 `type=waypoint` 会被视为路网点并从普通查询结果弱化。 |
| 节点坐标 | `nodes[].location.lat/lng` | 所有要显示在室外地图、作为起点或参与室外路线叠加的节点都必须有坐标。 |
| 边端点 | `edges[].from/to` | 必须引用同一校园图内存在的节点 ID。 |
| 边距离 | `edges[].distance` | 数值，单位为米；路由最短距离和最短时间都依赖它。 |
| 边方向 | 每条 `edge` 是有向边 | 双向可走道路需要写入两条相反方向边。 |
| 路由时间字段 | `congestion/ideal_speed` | 可缺省，但字段名必须保持；缺省时 loader/router 使用默认值。 |
| 交通限制字段 | `vehicle_access/allowed_transports/transport_speeds` | 字段名沿用 PKU；用于 `walk/bike/mixed` 交通方式过滤和时间估计。 |
| 地图 GeoJSON | `/api/map/geojson` 输出 `Point` 和 `LineString` | 坐标输出必须是 RFC 7946 顺序 `[lng, lat]`；源数据仍使用 `location.lat/lng` 或边 `geometry[].lat/lng`。 |
| 查询来源 | `load_site_records(site_id)` 从图节点生成记录 | 不需要另建 POI 查询表；节点字段要能被标准化为搜索记录。 |
| 餐饮推荐 | `category == "catering"` | 餐饮推荐只从当前站点图中筛选餐饮节点。 |
| 室内入口 | 室外节点 `sub_graph_id` + 室内节点 `is_gate=true` | 只有两端匹配时，loader 才会自动补 `gate_link`。 |
| 室内注册表 | `geo/indoor_building_registry.json` | 若声明室内能力，注册表字段名必须与 PKU 保持一致。 |
| 本地 OSM 层 | `geo/osm_roads_simplified.geojson` 等固定文件名 | 这些是可选增强；若提供，文件名和 GeoJSON `FeatureCollection` 契约保持不变。 |
| 稳定 API | 既有 GET/POST 接口和响应字段 | 新校园只能添加数据，不能要求删除、重命名或改变稳定接口字段含义。 |

稳定 API 包括：

```text
GET /api/bootstrap
GET /api/map/geojson
GET /api/map/osm-layers
GET /api/map/indoor
POST /api/search/scenic
POST /api/search/places
POST /api/recommend/catering
POST /api/diaries/fulltext
POST /api/route
POST /api/route/multi
```

## 允许按站点自定义的字段和值

下表列出允许随校园变化的内容。这些内容可以不同于 PKU，但必须落在上面的固定契约内。

| 范围 | 可变内容 | 兼容限制 |
| --- | --- | --- |
| `SITE_ID` | `THU`、`WHU` 等站点缩写 | 建议使用大写英文；必须与目录名、API `site_id`、注册表 `id` 一致。 |
| 站点元信息 | `name/description/location` | 可使用本校中文名、城市和说明文本。 |
| `sub_graphs` | 室内图数量和顺序 | 只声明实际存在的图文件；室外主链路至少包含 `outdoor`。 |
| `graph_id` | 图 ID 字符串 | 推荐 `<SITE_ID>_outdoor`、`<SITE_ID>_indoor_XXX`，但代码只要求稳定可读。 |
| 节点 ID | 校门、POI、道路、室内房间 ID | 可按站点命名；必须同站点唯一。若要兼容现有演示预设，可保留通用 ID 如 `gate_north/library/canteen`。 |
| 节点名称 | 本校真实或演示名称 | 可用中文、英文或混合；搜索和 UI 展示会直接使用。 |
| 坐标 | 每个节点的 `lat/lng` | 必须是 WGS84 经纬度数值；不要写成 `[lat,lng]` 数组。 |
| 道路密度 | 道路节点和边数量 | 可少于 PKU，但核心 POI 必须连通，否则搜索可命中但路线不可达。 |
| 类别组合 | 本校 POI 使用的标准类别 | 可不用 PKU 全部类别；场所查询仅支持固定 place 类别集合。 |
| `tags/keywords/facilities` | 本校特色标签、设施和关键词 | 可站点化；保持数组类型，缺失时搜索推荐信息会变弱。 |
| `heat/rating` | 热度和评分 | 可站点化；缺失时会估算，但推荐排序可解释性会下降。 |
| `open_hours` | 开放时间文本 | 可省略或写本校时间；餐饮、建筑展示会直接透传。 |
| 边 `name/description/type` | 道路名称、说明、边类型 | 可站点化；字段名保持不变。 |
| 边 `geometry` | 手工或匹配后的道路折线 | 可缺省；缺省时地图 GeoJSON 使用两端节点直线 fallback。 |
| OSM 来源字段 | `source_osm_id/source_highway/source_osm_ids` 等 | 可缺省；若提供，只作为地图和审计增强，不作为路由权威。 |
| 室内建筑集合 | 哪些建筑支持室内导航 | 可按校园选择；声明室内时必须保证注册表、室外入口和室内图一致。 |
| 用户样本 | `data/users.json` 中 `home_site_id` 对应用户 | 可为空；无用户样本时核心查询路线仍可用，但兴趣选项会减少。 |

## 文件级字段清单

### 1. `data/global_sites.json`

每个新增校园至少需要一个 `sites[]` 项：

| 字段 | 是否必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `id` | 必需 | string | 站点 ID；与 `data/sites/<SITE_ID>/` 目录一致。 |
| `name` | 必需 | string | UI 站点切换和 bootstrap `site.name` 使用。 |
| `description` | 必需 | string | bootstrap 透传；可为简短校园说明。 |
| `location` | 必需 | string | 校园地址或城市位置说明。 |
| `sub_graphs` | 必需 | string[] | 图加载顺序；最小室外校园为 `["outdoor"]`。 |

兼容注意：

1. `sub_graphs` 中的每个值必须对应 `data/sites/<SITE_ID>/<value>.json`。
2. 若 `sub_graphs` 声明了不存在的室内图，该图不会加载，后续室内或路由目标会缺失。
3. 默认站点仍由 `sites[0]` 决定；新增校园不要改变 PKU 默认行为，除非上层明确要求。

### 2. `data/sites/<SITE_ID>/outdoor.json`

顶层字段：

| 字段 | 是否必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `graph_id` | 必需 | string | 建议 `<SITE_ID>_outdoor`。 |
| `graph_type` | 必需 | string | 室外图固定为 `outdoor`。 |
| `nodes` | 必需 | object[] | 室外校门、POI、道路节点。 |
| `edges` | 必需 | object[] | 有向路由边。 |

最小数据内容：

1. 至少包含一个可作为默认起点的校门或入口节点。
2. 至少包含若干核心 POI：图书馆或学习建筑、教学区、食堂、宿舍或生活区、服务设施。
3. 至少包含能连接这些 POI 的道路/接驳节点。
4. 每个可搜索 POI 都需要通过边接入道路网络。

### 3. `outdoor.json` 的 `nodes[]`

所有室外可展示或可路由节点的最低字段：

| 字段 | 是否必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `id` | 必需 | string | 同一校园唯一；路由、搜索、地图都使用它。 |
| `name` | 必需 | string | UI 展示和搜索文本。 |
| `category` | 必需 | string | 标准英文类别。 |
| `location.lat` | 地图/室外路由必需 | number | WGS84 纬度。 |
| `location.lng` | 地图/室外路由必需 | number | WGS84 经度。 |
| `type` | 条件必需 | string | 路网点应为 `waypoint`；普通 POI 可使用 `building/facility/entrance/poi` 等。 |
| `is_gate` | 条件必需 | boolean | 校门、建筑入口或室内入口应显式标记。 |
| `tags` | 推荐 | string[] | 查询、兴趣推荐和关键词补充。 |
| `keywords` | 推荐 | string[] | 可补充别名；缺失时会由名称、类别、设施等估算。 |
| `description` | 推荐 | string | 搜索结果和推荐卡片说明。 |
| `facilities` | 推荐 | string[] | 设施能力；可为空数组。 |
| `open_hours` | 可选 | string | 食堂、图书馆等开放时间。 |
| `heat` | 可选 | number | 推荐排序使用；缺失时估算。 |
| `rating` | 可选 | number | 推荐排序使用；缺失时估算。 |

标准类别使用口径：

| 用途 | 类别 |
| --- | --- |
| 校门/入口 | `entrance` |
| 教学/学习建筑 | `education` |
| 地标 | `landmark` |
| 宿舍 | `dormitory` |
| 餐饮 | `catering` |
| 便利店/购物 | `shopping` |
| 运动 | `sports` |
| 洗手间 | `restroom` |
| 停车 | `parking` |
| 普通建筑 | `building` |
| 建筑入口 | `building_entrance` |
| 服务设施 | `service` |
| 路网点 | `road` |

场所查询 `POST /api/search/places` 当前只支持这些 place 类别：

```text
restroom
catering
shopping
parking
education
building
building_entrance
sports
service
landmark
```

因此 `entrance`、`dormitory`、`road` 可以作为校园节点类别，但不要期待它们通过 places 接口的类别过滤直接命中。综合查询仍可按关键词命中非 road 节点。

路网点字段口径：

1. `category` 使用 `road`。
2. `type` 使用 `waypoint`。
3. `name` 可以是生成名，但必须非空。
4. `location.lat/lng` 必须存在，否则该路网点无法参与室外地图和路线叠加。
5. `road` 或 `type=waypoint` 节点会被普通搜索结果弱化，不应用作核心 POI。

室内入口相关字段只在该建筑声明室内能力时需要：

| 字段 | 是否必需 | 说明 |
| --- | --- | --- |
| `sub_graph_id` | 室内联通必需 | 指向对应室内图 stem，例如 `indoor_LIB`。 |
| `indoor_supported` | UI 识别推荐 | 建议为 `true`。 |
| `indoor_graph_id` | UI 识别推荐 | 与 `sub_graph_id` 保持一致。 |
| `indoor_entry_node_id` | UI 识别推荐 | 对应室内图中的入口节点 ID。 |

### 4. `outdoor.json` 的 `edges[]`

每条边的硬性最低字段：

| 字段 | 是否必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `from` | 必需 | string | 起点节点 ID。 |
| `to` | 必需 | string | 终点节点 ID。 |
| `distance` | 必需 | number | 米；用于路由权重。 |

为保持 PKU 当前 UI、路线说明和交通方式兼容，建议每条边同时补齐：

| 字段 | 是否必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `name` | 推荐 | string | 路线步骤和地图属性使用。 |
| `description` | 推荐 | string | 审计和路线说明可读性。 |
| `type` | 推荐 | string | 例如 `white_road`、`poi_access`、`bike_lane`。 |
| `congestion` | 推荐 | number | 缺省为 `1.0`。 |
| `ideal_speed` | 推荐 | number | 米/秒；缺省为 `1.0`。 |
| `vehicle_access` | 推荐 | string | `all`、`pedestrian_only`、`vehicle_only`。 |
| `allowed_transports` | 条件推荐 | string[] | 需要精确控制 `walk/bike/mixed` 时填写。 |
| `transport_speeds` | 条件推荐 | object | 不同交通方式速度。 |
| `transport_semantics` | 可选 | string | 交通语义说明。 |
| `geometry` | 可选 | object[] | 折线点数组，点字段为 `{ "lat": number, "lng": number }`。 |
| `source_osm_id` | 可选 | string | OSM 来源增强。 |
| `source_highway` | 可选 | string | OSM 道路类型增强。 |

兼容注意：

1. `Graph.add_edge(...)` 当前按有向边加载；双向道路必须写两条边。
2. `distance` 不应为负数；零距离只适合入口桥接或投影重合点。
3. 室外路线 GeoJSON 会优先使用 OSM 匹配几何，其次使用边 `geometry`，最后回退到两端节点直线。
4. 前端地图不是路由权威；路由权威始终是 `outdoor.json` 和已加载室内图组成的课程图。

### 5. `geo/` 下的可选本地图层字段

新增校园最小室外主链路不强制要求 OSM 派生文件。缺失时 `/api/map/osm-layers` 应返回空图层和 warnings，不应破坏核心地图。

如果提供本地 OSM 图层，文件名和基本结构保持固定：

| 文件 | 是否必需 | 固定结构 |
| --- | --- | --- |
| `geo/osm_roads_simplified.geojson` | 可选 | GeoJSON `FeatureCollection`，道路 `LineString`。 |
| `geo/osm_buildings.geojson` | 可选 | GeoJSON `FeatureCollection`，建筑 `Polygon`。 |
| `geo/osm_water_landuse.geojson` | 可选 | GeoJSON `FeatureCollection`，水域/绿地 `Polygon` 或 `LineString`。 |
| `geo/edge_osm_geometry_matches.json` | 可选 | 顶层 `metadata/matches`，匹配项指向课程图边。 |
| `geo/osm_extract_metadata.json` | 可选 | 记录来源、许可、阶段和运行策略。 |

`edge_osm_geometry_matches.json` 若存在，单条 `matches[]` 推荐保持这些字段名：

```text
edge_key
from
to
geometry_source
source_osm_id
source_highway
osm_way_ids
distance_m
confidence
geometry
coverage
notes
```

其中 `geometry` 仍使用 `{ "lat": ..., "lng": ... }` 点数组；API 输出 GeoJSON 时再转换为 `[lng, lat]`。

### 6. 室内能力的条件字段

如果新增校园当前只做室外能力，不需要创建室内图。若某校园声明室内能力，则以下三处必须同时一致。

`geo/indoor_building_registry.json`：

| 字段 | 是否必需 | 说明 |
| --- | --- | --- |
| `building_id` | 必需 | 建筑 ID；通常与室外入口节点相关。 |
| `building_name` | 必需 | UI 展示名称。 |
| `entry_node_id` | 必需 | 室外入口节点 ID。 |
| `indoor_graph_id` | 必需 | 室内图 stem，也必须出现在 `sub_graphs` 中。 |
| `template_id` | 必需 | 使用的室内模板 ID。 |
| `floor_ids` | 必需 | 楼层 ID 列表。 |
| `default_floor_id` | 必需 | 默认楼层，必须属于 `floor_ids`。 |
| `entry_mapping_reason` | 推荐 | 入口映射说明。 |

对应室外入口节点：

1. `id` 与注册表 `entry_node_id` 一致，或能被注册表明确反查。
2. `sub_graph_id` 等于注册表 `indoor_graph_id`。
3. 建议补 `indoor_supported=true`、`indoor_graph_id`、`indoor_entry_node_id`。

对应室内图 `data/sites/<SITE_ID>/<indoor_graph_id>.json`：

| 字段 | 是否必需 | 说明 |
| --- | --- | --- |
| `graph_id` | 必需 | 建议 `<SITE_ID>_<indoor_graph_id>`。 |
| `graph_type` | 必需 | 固定为 `indoor`。 |
| `building_id` | 必需 | 与注册表一致。 |
| `building_name` | 必需 | 与注册表一致。 |
| `template_id` | 必需 | 与注册表一致。 |
| `floor_ids` | 必需 | 与注册表一致。 |
| `default_floor_id` | 必需 | 与注册表一致。 |
| `nodes` | 必需 | 室内节点。 |
| `edges` | 必需 | 室内有向边。 |

室内节点最低字段：

| 字段 | 是否必需 | 说明 |
| --- | --- | --- |
| `id` | 必需 | 同一校园合并图内唯一。 |
| `name` | 必需 | UI 展示。 |
| `category` | 必需 | 例如 `hall`、`reading_room`、`service`、`passage`。 |
| `floor_id` | 必需 | 所属楼层。 |
| `floor_label` | 推荐 | 楼层展示名。 |
| `layout.x/y` | 室内可视化必需 | 室内 SVG 平面图坐标。 |
| `is_gate` | 入口节点必需 | 至少一个室内入口节点为 `true`。 |
| `is_indoor` | 推荐 | 建议为 `true`。 |
| `indoor_building` | 推荐 | 建筑名或建筑 ID。 |

室内边最低字段与室外一致：`from/to/distance` 必需；`name/type/congestion/ideal_speed/vehicle_access` 建议补齐。室内边和自动生成的 `gate_link` 应保持步行语义。

### 7. 查询、推荐和用户样本字段

查询和推荐记录由图节点标准化生成，不需要额外 POI 数据表。为了让新增校园结果可用且可解释，核心 POI 应优先补齐：

```text
id
name
category
location.lat
location.lng
tags
keywords
description
facilities
open_hours
heat
rating
```

不同业务的最低数据依赖：

| 能力 | 最低字段依赖 |
| --- | --- |
| 综合查询 | 非 `road/waypoint` 节点有 `id/name/category`，最好有 `tags/keywords/description`。 |
| 场所查询 | 节点 `category` 属于 place 类别集合。 |
| 附近查询 | `center_node_id` 和候选 POI 都存在于当前站点路由图，且图上可达。 |
| 餐饮推荐 | 至少一个节点 `category == "catering"`；距离排序需要该节点可达。 |
| 兴趣推荐 | 节点有可匹配的 `category/tags/facilities/keywords/description`。 |
| 用户兴趣选项 | `data/users.json` 中存在 `home_site_id == <SITE_ID>` 的用户。 |

`data/users.json` 中单个用户字段保持：

| 字段 | 是否必需 | 说明 |
| --- | --- | --- |
| `id` | 必需 | 用户 ID。 |
| `name` | 必需 | UI 展示。 |
| `role` | 推荐 | 用户角色。 |
| `home_site_id` | 必需 | 当前校园 ID；用于站点隔离加载。 |
| `interests` | 推荐 | 兴趣词数组。 |
| `created_at` | 可选 | 样本创建时间。 |

无用户样本时，新增校园仍可查询、推荐餐饮和规划路线，但 bootstrap 中用户和兴趣选项会减少。

## 新校园字段准备顺序

建议后续新增校园按以下顺序补字段，避免先写大量文案但主链路不可达：

1. 先补 `global_sites.json` 注册字段和 `data/sites/<SITE_ID>/outdoor.json` 顶层字段。
2. 再补校门、核心 POI 和道路节点的 `id/name/category/location`。
3. 再补有向边 `from/to/distance`，确保核心 POI 全部连通。
4. 再补 `type/is_gate/tags/keywords/description/facilities/heat/rating/open_hours`，提升查询推荐质量。
5. 如需交通方式演示，再补 `vehicle_access/allowed_transports/transport_speeds/congestion/ideal_speed`。
6. 如需真实地图观感，再补边 `geometry` 或 `geo/` 下本地 OSM 派生文件。
7. 如需室内能力，再补室内注册表、室外入口字段和 `indoor_*.json`。

## M25B 结论

新增校园必须复制的是 PKU 的字段契约和加载语义，不是 PKU 的具体节点、坐标、道路数量或文案。最小数据集应先保证 `global_sites` 注册、`outdoor.json` 可加载、核心节点有坐标、路由边连通、类别字段标准化；其余 OSM、室内、兴趣用户和精细文案均按声明能力逐步补齐。
