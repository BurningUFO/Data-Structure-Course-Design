# 地图方案 B M8 Agent Goal 提示词

## 目标

在当前仓库 `C:\code\Data-Structure-Course-Design` 的 `experiment/map-plan-b` 分支上，完成地图方案 B M8：离线 OSM 数据抽取与本地化，生成并展示本地 OSM roads / buildings / water / landuse GeoJSON 图层。

## 开始前必须执行

1. `git status --short --branch`
2. 确认当前分支是 `experiment/map-plan-b`
3. 阅读 `AGENTS.md`
4. 阅读 `docs/地图方案B真实地图层总路线计划.md` 中“阶段 7：离线 OSM 数据抽取与本地化”和“M8”
5. 阅读 M7 新增或更新的底图说明文档
6. 阅读 `docs/references/map-plan-b/README.md`，确认 OSMnx、Overpass、Mapshaper、GeoJSON 资料位置
7. 运行 `py -m pytest`，确认当前基线通过

## 当前状态

1. M1-M6 已完成 Leaflet + GeoJSON、route geometry overlay、视觉包装、fallback。
2. M7 已完成真实瓦片底图和底图模式切换。
3. 现在要把 OSM 派生数据本地化，降低运行时网络依赖，并让地图更像真实校园地图。
4. 本阶段只做“数据准备 + 本地图层展示”，不做课程图 edge 与 OSM 道路线形匹配；匹配留到 M9。

## 本阶段目标

1. 在 `data/sites/PKU/geo/` 下建立本地 OSM 派生数据目录和元数据。
2. 获取或生成 PKU 周边 roads / buildings / water / landuse 的 GeoJSON 文件。
3. Web UI 运行时从本地文件读取这些 GeoJSON，不在请求时调用 OSMnx 或 Overpass。
4. Leaflet 增加可选本地 OSM 图层：道路、建筑、水域 / 绿地等。
5. 保留项目原有 map GeoJSON、route overlay、节点和路线高亮优先级。
6. 文档记录数据来源、查询方式、抽取日期、license / attribution、已知限制。
7. 测试保证本地 OSM GeoJSON 可解析、坐标顺序正确、不会破坏现有接口。

## 数据目录建议

```text
data/sites/PKU/geo/
  osm_roads_raw.geojson
  osm_roads_simplified.geojson
  osm_buildings.geojson
  osm_water_landuse.geojson
  osm_extract_metadata.json
```

## 数据获取策略

### 优先策略 A：使用网络一次性抽取并保存到本地文件

1. 可以使用 Overpass API 或 OSMnx 作为准备步骤。
2. 外部请求只允许发生在数据准备脚本或命令中。
3. Web UI 后端运行时不得实时请求 Overpass / OSMnx。
4. 如果网络失败，必须降级为手工创建一个最小可用本地样例 GeoJSON，用于证明数据层和 UI 图层机制可用。

### 备选策略 B：如果无法稳定访问 Overpass / OSMnx

1. 手工创建小范围 PKU 周边 roads / buildings / water / landuse 示例 GeoJSON。
2. 文档明确说明这是本地样例数据，后续可替换为正式 OSM 抽取结果。
3. 保证格式、图层加载、UI 控制和测试全部可用。

## 后端要求

1. 增加读取 `data/sites/PKU/geo/` 下 OSM 派生 GeoJSON 的服务函数。
2. 新增 API：

```text
GET /api/map/osm-layers?site_id=PKU
```

3. 推荐单独接口 `/api/map/osm-layers?site_id=PKU`，避免破坏现有 map GeoJSON 契约。
4. 返回结构建议：

```json
{
  "success": true,
  "site_id": "PKU",
  "layers": {
    "roads": {"type": "FeatureCollection", "features": []},
    "buildings": {"type": "FeatureCollection", "features": []},
    "water_landuse": {"type": "FeatureCollection", "features": []}
  },
  "metadata": {},
  "stats": {}
}
```

5. 读取失败时返回 `success=false` 或空图层，但不能影响 `/api/bootstrap`、`/api/map/geojson`、`/api/route`。
6. 不删除或改变现有字段。

## 前端要求

1. Leaflet 增加本地 OSM 图层控制：
   - OSM 道路
   - 建筑
   - 水域 / 绿地
2. 默认是否开启可由你判断，但不能遮挡项目路线高亮。
3. 图层顺序建议：
   - basemap tile 底层
   - water / landuse
   - buildings
   - OSM roads
   - 项目 roads / nodes
   - route overlay 顶层
4. 图层样式要克制，项目路线和节点仍最醒目。
5. 如果 `/api/map/osm-layers` 加载失败，UI 显示提示但不影响原地图。
6. 无底图模式下也能显示本地 OSM 图层。
7. `simple_svg` fallback 仍可用。

## 测试要求

1. 运行 `py -m pytest`。
2. 新增或更新 `tests/test_ui_demo.py`：
   - `/api/map/osm-layers` 返回 `success=true` 或可解释的空图层。
   - 本地 OSM GeoJSON 是 `FeatureCollection`。
   - 坐标顺序为 `[lng, lat]`。
   - `stats` 中包含 roads / buildings / water_landuse feature 数。
   - 缺失某个本地文件时不影响核心接口。
3. API smoke check：
   - `GET /api/bootstrap`
   - `GET /api/map/geojson?site_id=PKU`
   - `GET /api/map/osm-layers?site_id=PKU`
   - `POST /api/route gate_north -> library`
   - `POST /api/route/multi library + canteen`
4. 如果可行，用浏览器检查：
   - Leaflet 真实底图显示
   - 本地 OSM roads / buildings / water / landuse 图层可显示或切换
   - 项目路线高亮仍在最上层
   - 无底图模式仍能显示本地 OSM 图层
   - `simple_svg` fallback 可用

## 文档要求

1. 新增或更新 M8 记录文档，例如 `docs/地图方案B第八阶段OSM本地化记录.md`。
2. 文档必须说明：
   - 数据文件路径
   - 数据来源
   - 查询 / 生成方式
   - 抽取日期
   - license / attribution
   - 是否为正式 OSM 抽取数据或本地样例数据
   - 已知限制
   - 如何替换为新的 OSM 数据
3. 更新 `docs/地图方案B最终交付说明.md` 或总路线计划中的当前状态。

## 严禁

1. 不要在 Web UI 请求时实时调用 OSMnx 或 Overpass。
2. 不要把外部瓦片下载进仓库。
3. 不要做 M9 的 edge-to-OSM 路线匹配。
4. 不要重写 routing 算法。
5. 不要重写 graph loader 语义。
6. 不要破坏 `/api/bootstrap`、`/api/map/geojson`、`/api/route`、`/api/route/multi`。
7. 不要提交 `scripts/` 和 `工作进度/` 下已有无关未跟踪文件。
8. 不要异常终止；如果网络抽取失败，按备选策略 B 完成可用本地图层机制并记录原因。

## 子 agent 使用规则

1. 可以使用 explorer 子 agent 只读分析现有地图 API、Leaflet 图层结构和测试结构。
2. 可以使用一个 worker 只负责文档或测试，不要和主 agent 同时编辑同一文件。
3. 不要让多个 worker 同时修改 `app.js`、`demo_service.py` 或数据文件。
4. 主 agent 必须负责数据、后端、前端的最终集成、review 和验证。

## 完成标准

1. `py -m pytest` 通过。
2. `data/sites/PKU/geo/` 存在本地 OSM 派生 GeoJSON 和 metadata。
3. `/api/map/osm-layers?site_id=PKU` 可返回本地图层数据和 stats。
4. Leaflet 可加载本地 OSM roads / buildings / water / landuse 图层，且 route overlay 仍在最上层。
5. 文档记录数据来源、license / attribution 和替换方式。
6. `simple_svg` fallback 仍可用。
7. `git status` 不包含误 staged 的无关文件。
8. 验证通过后提交为：

```text
feat: add local osm map layers
```

