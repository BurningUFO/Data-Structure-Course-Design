# 地图方案 B M25D 多校园扩站规则与自检清单

## 范围

本文只执行 M25D：在 M25A/M25B/M25C 已有产物基础上，补齐后续单校复制 agent 可直接遵循的扩站规则、禁区说明和复制后自检清单。

本文不创建真实新校园数据，不修改运行时代码，不更新 `data/global_sites.json`，不进入 M26 或后续阶段。

上游产物：

- `docs/地图方案B_M25A_PKU多校园复制依赖审计.md`
- `docs/地图方案B_M25B_新校园最小必备字段清单.md`
- `docs/地图方案B_M25C_新校园模板脚手架说明.md`
- `scripts/scaffold_new_campus.py`

## 扩站总规则

### 1. 单校原子化

后续执行 M26/M27/M28 时，每个三级 agent 默认只处理一个明确的 `<SITE_ID>`。不要在同一次原子任务里同时扩多个校园、同时做室外和室内全量铺设，或把数据准备、后端接入、前端验收和答辩文档收口混成一次大改动。

单校任务开始前必须固定：

1. 当前阶段 ID，例如 `M26A`、`M26B`、`M26C`。
2. 目标校园 `<SITE_ID>`、中文名、城市。
3. 本次是否允许写 `data/sites/<SITE_ID>/`。
4. 本次是否允许修改 `data/global_sites.json`。
5. 本次是否允许新增室内图、用户样本或 OSM 派生文件。

任何未被当前阶段明确允许的内容，都按禁止处理。

### 2. 站点 ID 与目录

`SITE_ID` 是多校园隔离边界，必须同时满足：

1. 使用 M24A 注册表或 `data/global_sites.json` 中已冻结的 ID。
2. 目录名、API 请求 `site_id`、`global_sites.json` 的 `id` 完全一致。
3. 建议保持大写英文、数字或下划线，符合 `scripts/scaffold_new_campus.py` 的校验规则。
4. 不得重命名、迁移或重建既有 `PKU`。
5. 不得改变 `data/global_sites.json` 中 `PKU` 的默认站点地位，除非上层明确要求。

目录规则：

```text
data/sites/<SITE_ID>/
data/sites/<SITE_ID>/outdoor.json
data/sites/<SITE_ID>/geo/
data/sites/<SITE_ID>/indoor_*.json
```

`outdoor.json` 是室外主链路入口；`geo/` 和 `indoor_*.json` 是按能力启用的增强项。只创建空目录或占位文件不等于校园已经可运行。

### 3. 使用 M25C 脚手架的规则

`scripts/scaffold_new_campus.py` 只能作为起点，不能把生成结果直接当作真实校园交付。

安全用法：

1. 优先用 `--dry-run` 观察将要生成的文件。
2. 生成前确认目标目录不存在，或确认当前阶段明确允许覆盖。
3. 默认不要使用 `--overwrite`；只有上层明确要求重建该校园脚手架时才可使用。
4. `global_sites_entry.json` 只是人工合并片段，不会自动接入运行时。
5. 脚手架里的 placeholder 名称、坐标、距离、开放时间、描述和室内入口映射必须在后续真实校园阶段替换。

不得把 `.codex_tmp/`、`.playwright-cli/`、dry-run 输出、临时浏览器脚本或无关原始数据纳入提交。

### 4. 室外图数据规则

新增校园的最低运行目标是：可加载、可显示、可查询、可推荐、可规划路线。数据量可以少于 PKU，但字段契约必须与 PKU 兼容。

`outdoor.json` 顶层至少保持：

```text
graph_id
graph_type
nodes
edges
```

节点规则：

1. `nodes[].id` 在同一校园合并图内全局唯一，室外和室内共享命名空间。
2. `nodes[].name` 非空，用于搜索、地图标签和路线目标。
3. `nodes[].category` 使用 M25B 中列出的标准英文类别。
4. 需要出现在室外地图、起点下拉或路线叠加中的节点必须有 `location.lat/lng`。
5. 路网点使用 `category: road` 和 `type: waypoint`，不要把它当普通 POI。
6. 核心 POI 建议补 `tags/keywords/description/facilities/open_hours/heat/rating`，否则查询推荐可解释性会下降。

边规则：

1. `edges[].from/to` 必须引用同站点内存在的节点。
2. `edges[].distance` 是米，必须是非负数；普通道路不要用 0。
3. 当前图是有向图；双向可走道路必须写两条相反方向边。
4. `name/type/description/congestion/ideal_speed/vehicle_access/allowed_transports/transport_speeds` 应沿用 PKU 字段名。
5. `geometry` 可缺省；缺省时 GeoJSON 会退化为两端点直线。
6. 路由权威始终是课程图边，不是前端底图，也不是 OSM 上下文图层。

坐标规则：

1. 原始节点坐标使用对象形式 `{ "lat": number, "lng": number }`。
2. 边 `geometry` 使用点对象数组 `{ "lat": number, "lng": number }`。
3. API 输出 GeoJSON 时才转换为 RFC 7946 的 `[lng, lat]`。
4. 不要把 `[lat, lng]` 数组写进源数据冒充 GeoJSON 坐标。

### 5. 查询、推荐与用户样本规则

查询和推荐默认从当前站点图节点标准化生成，不需要额外 POI 表。

1. 综合查询要求非 `road/waypoint` 节点至少有 `id/name/category`。
2. 场所查询只支持 M25B 固定的 place 类别集合。
3. 餐饮推荐只筛选 `category == "catering"` 的当前站点节点。
4. 距离排序和附近查询要求候选节点在当前站点路由图内可达。
5. 用户样本必须通过 `home_site_id` 绑定到目标校园；没有样本时核心查询和路线仍应可用。
6. 不要为了某校园改全局兴趣词、类别别名或搜索算法，除非阶段明确要求做 M31 类校准。

### 6. 室内能力规则

室内不是新校园最小室外主链路的硬要求。只有当前阶段明确允许室内时，才创建或接入 `indoor_*.json`。

声明室内能力时，三处必须一致：

1. `geo/indoor_building_registry.json` 的 `entry_node_id/indoor_graph_id/template_id/floor_ids/default_floor_id`。
2. `outdoor.json` 中对应入口节点的 `sub_graph_id/indoor_supported/indoor_graph_id/indoor_entry_node_id`。
3. `indoor_*.json` 顶层建筑字段、至少一个 `is_gate=true` 室内入口节点，以及室内边连通性。

只要其中一处缺失，就不要在 bootstrap、前端文案或验收说明里宣称该校园已支持室内导航。

### 7. 本地 OSM 与真实地图层规则

OSM 派生数据只能作为本地上下文图层或边几何增强，不能替代课程图。

允许的本地增强文件名：

```text
geo/osm_roads_simplified.geojson
geo/osm_buildings.geojson
geo/osm_water_landuse.geojson
geo/edge_osm_geometry_matches.json
geo/osm_extract_metadata.json
```

规则：

1. 运行时 UI 和 API 不得调用 OSMnx、Overpass 或外部地图抓取接口。
2. 外部数据提取必须放在准备脚本、离线步骤或明确文档中。
3. 缺失 OSM 图层时，`/api/map/osm-layers` 应保持空图层加 warnings，不应影响核心地图。
4. 不得把 PKU 的 OSM 匹配几何复制到其他校园。
5. 不得把大体积原始抓取文件混入单校运行数据，除非阶段明确要求并记录来源、许可和用途。

### 8. API 与前端规则

稳定 API 只能 additive 扩展，不能删除、重命名或改变旧字段含义：

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

站点切换规则：

1. 前端和 API 请求必须按当前 `site_id` 读取数据。
2. 不得在共享前端逻辑里硬编码某个新校园的节点 ID。
3. 如果为了兼容演示按钮保留 `library/canteen/gate_north` 等通用 ID，只能保证这些 ID 在单站点内唯一，不能跨站点混用状态。
4. 站点切换后必须清空路线、焦点、地图 GeoJSON/OSM 缓存和室内缓存。

## 禁区说明

| 禁区 | 禁止内容 | 安全替代 |
| --- | --- | --- |
| PKU 基线 | 为了接入新校园修改、删减或重命名 `PKU` 节点、边、室内图、OSM 图层或默认站点位置。 | 只在目标校园目录内工作；回归时确认 PKU API 仍通过。 |
| 稳定 API | 删除响应字段、改字段含义、让旧请求体失效。 | 需要新信息时只添加字段，并保留旧字段。 |
| 路由核心 | 重写 Dijkstra、改 `Router` 主语义、把 OSM 图层当路由权威。 | 用现有边字段、交通字段和课程图连通性解决。 |
| 图加载语义 | 改 `GraphLoader` 的目录约定、`sub_graphs` 语义或 gate_link 规则来适配单一新校园。 | 修正该校园数据，让它符合现有契约。 |
| 运行时外部依赖 | 在 Web UI、API 请求或用户操作中调用 OSMnx、Overpass、地图抓取脚本或 CDN-only 资源。 | 离线准备本地文件，运行时只读仓库内数据。 |
| 跨阶段扩张 | 在 M26 单校室外阶段顺手做 M29/M30 室内全量、M31 推荐校准或 M32 总验收。 | 记录后续任务，交给对应阶段处理。 |
| 占位冒充真实 | 把 M25C placeholder 坐标、名称、距离或开放时间当作真实校园数据。 | 用核验过的坐标和校园语义替换后再接入。 |
| 脚手架覆盖 | 未确认目标目录状态就覆盖 `data/sites/<SITE_ID>/`。 | 先 `git status` 和目录检查；必要时请上层明确授权。 |
| 原始数据污染 | 删除、移动、重写无关 `scripts/`、`工作进度/`、raw Geo 数据或其他 agent 的未提交文件。 | 只改当前阶段允许的目标文件，提交前只 stage 本任务文件。 |
| 跨站状态污染 | 查询、推荐、日记、用户或地图缓存读取到其他校园数据。 | 所有入口显式传递并校验当前 `site_id`。 |

## 单校复制后自检清单

后续单校 agent 完成一次校园复制后，应按下列清单逐项打勾。`<SITE_ID>` 替换为当前校园 ID。

### A. 工作区与范围

- [ ] 已运行 `git status --short --branch`，当前分支是 `experiment/map-plan-b`。
- [ ] 已运行 `git branch --show-current`，确认不是其他分支。
- [ ] 本次只修改当前阶段允许的文件。
- [ ] 没有 stage、删除、移动或重写无关未跟踪文件。
- [ ] 没有创建 `.codex_tmp/`、`.playwright-cli/` 等临时目录残留，或已在验收后清理。
- [ ] 没有进入 M26 之后的阶段外工作。

### B. 注册与目录

- [ ] `data/global_sites.json` 中存在 `<SITE_ID>`，且 `id/name/description/location/sub_graphs` 完整。
- [ ] `data/sites/<SITE_ID>/` 存在。
- [ ] `sub_graphs` 中每个条目都有对应 `data/sites/<SITE_ID>/<name>.json`。
- [ ] `outdoor` 已在 `sub_graphs` 中，且 `data/sites/<SITE_ID>/outdoor.json` 存在。
- [ ] 未改变 `PKU` 注册项、默认顺序和既有 `sub_graphs`。

### C. JSON 与字段完整性

- [ ] `data/global_sites.json` 可被 `python -m json.tool` 解析。
- [ ] `data/sites/<SITE_ID>/outdoor.json` 可被 `python -m json.tool` 解析。
- [ ] 所有已声明室内图和 `geo/*.json` 文件均可解析。
- [ ] `outdoor.json` 顶层包含 `graph_id/graph_type/nodes/edges`。
- [ ] `graph_type` 对室外图是 `outdoor`。
- [ ] 节点 `id` 在当前校园合并图内无重复。
- [ ] 每个非路网核心 POI 有 `id/name/category/location.lat/location.lng`。
- [ ] 每个路网点使用 `category: road` 与 `type: waypoint`。
- [ ] 每条边有 `from/to/distance`。
- [ ] 每条边端点都能在当前校园节点集中找到。
- [ ] `distance` 为数字且不为负。
- [ ] 双向道路已写成两条相反方向边。

### D. 坐标与地图数据

- [ ] 所有室外可展示节点的 `location.lat/lng` 是 WGS84 数值。
- [ ] 没有把 `[lat, lng]` 数组写入源数据。
- [ ] 边 `geometry` 如存在，点格式为 `{ "lat": number, "lng": number }`。
- [ ] `GET /api/map/geojson?site_id=<SITE_ID>` 成功，并且 GeoJSON 坐标为 `[lng, lat]`。
- [ ] GeoJSON 中节点 Feature 带 `kind/id/name/category/category_label`。
- [ ] GeoJSON 中边 Feature 带 `kind/from/to/name/edge_type/distance_m`。
- [ ] 缺失 OSM 图层时 `/api/map/osm-layers?site_id=<SITE_ID>` 不影响核心地图。

### E. 图连通与路线

- [ ] 至少一个默认起点可用，优先校门或主入口。
- [ ] 核心 POI 已通过边接入道路网络。
- [ ] 搜索可命中的核心 POI 也是可路由目标。
- [ ] 至少一条校门到图书馆或教学区路线成功。
- [ ] 至少一条校门到食堂路线成功。
- [ ] 如有交通字段，`walk/bike/mixed` 不会把核心路线误判为不可达。
- [ ] 路线响应仍包含 `ui.route_geojson` 或 `ui.mappable_path_node_ids` 等前端叠加字段。

### F. 查询、推荐与站点隔离

- [ ] `POST /api/search/scenic` 带 `<SITE_ID>` 时只返回当前校园数据。
- [ ] `POST /api/search/places` 的类别过滤只使用现有 place 类别集合。
- [ ] `POST /api/recommend/catering` 至少能返回当前校园餐饮节点，或明确记录当前校园暂缺餐饮数据。
- [ ] 用户样本如有新增，`home_site_id` 等于 `<SITE_ID>`。
- [ ] 日记、兴趣推荐和附近查询没有混入其他校园数据。
- [ ] 使用 `site_id=PKU` 重跑核心查询和路线，确认 PKU 未回退。

### G. 室内能力

仅当当前阶段声明室内能力时检查：

- [ ] `geo/indoor_building_registry.json` 与 `outdoor.json` 入口节点一致。
- [ ] 室外入口节点的 `sub_graph_id` 指向实际存在且已在 `sub_graphs` 声明的室内图。
- [ ] 室内图至少有一个 `is_gate=true` 节点。
- [ ] 室内图节点 ID 不与室外节点或其他室内图节点冲突。
- [ ] `GET /api/map/indoor?site_id=<SITE_ID>&building_id=<BUILDING_ID>` 成功。
- [ ] 室内外路线可从室外入口进入室内目标，且室内段只使用步行语义。

### H. API 烟测

启动服务前先检查默认端口，避免命中旧服务：

```powershell
netstat -ano | findstr :8765
```

若 8765 已被占用，确认是否为自己启动的旧进程；不确定时使用临时端口。

服务启动命令：

```powershell
py -B -m src.ui.demo_server --host 127.0.0.1 --port <PORT>
```

最低烟测：

- [ ] `GET /api/health?site_id=<SITE_ID>` 返回 `success=true` 和当前 `site_id`。
- [ ] `GET /api/bootstrap?site_id=<SITE_ID>` 返回站点、起点、目标、地图能力和稳定字段。
- [ ] `GET /api/map/geojson?site_id=<SITE_ID>` 返回 `FeatureCollection`。
- [ ] `POST /api/search/scenic` 使用当前校园关键词成功。
- [ ] `POST /api/search/places` 使用一个当前校园类别成功。
- [ ] `POST /api/recommend/catering` 成功返回结果或清晰的空结果。
- [ ] `POST /api/route` 对当前校园两个可达节点成功。
- [ ] `POST /api/route/multi` 对当前校园 2 到 3 个目标成功。
- [ ] 同一组 PKU 基线接口仍成功。

### I. 前端烟测

- [ ] 打开 `http://127.0.0.1:<PORT>` 页面无启动错误。
- [ ] 站点切换到 `<SITE_ID>` 后，起点和目标下拉来自当前校园。
- [ ] 地图显示当前校园节点和道路，不显示 PKU 的路线残留。
- [ ] 执行一次路线规划后，Leaflet 或 SVG 叠加更新正常。
- [ ] 切回 `PKU` 后，PKU 地图、查询和路线仍可用。
- [ ] 若 Leaflet 或 GeoJSON 失败，页面仍能回退到 SVG 简图。

### J. 收尾交接

- [ ] 记录本次修改的文件清单。
- [ ] 记录验证命令和结果。
- [ ] 记录任何空结果、降级行为或待后续阶段处理的问题。
- [ ] `git diff --cached --name-status` 为空，除非上层明确要求当前 agent staging。
- [ ] 未创建提交；由对应二级经理负责 staging、提交和台账更新。

## M25D 结论

后续多校园复制的核心不是复制 PKU 的具体坐标和文案，而是复制 PKU 已经稳定下来的目录、字段、加载、查询、推荐、路由、地图和站点隔离契约。单校 agent 应先保证一个校园在现有契约下独立跑通，再逐步补充真实地图观感、室内模板和兴趣推荐校准；任何跨校园批量铺设都必须交给对应经理阶段拆分执行。
