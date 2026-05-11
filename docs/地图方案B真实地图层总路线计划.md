# 地图方案 B：准真实地图层总路线计划

## 1. 背景与目标

当前 Web UI 地图区仍是自绘 SVG 简图，普通道路用 `from/to` 两个节点之间的直线表示，路径高亮也按节点序列直接连线。这个实现满足“图形化地图展示与路径高亮”的最低验收要求，但视觉上不像真实校园地图，也无法体现园区道路弯折、道路层级和真实底图。

方案 B 的目标是在实验分支 `experiment/map-plan-b` 上验证一条更高上限的路线：引入准真实地图层，用开源地图能力承载底图、GeoJSON 路网、节点标注和路线高亮，同时保留原 SVG 简图作为稳定回退。

核心目标如下：

1. 让地图底图接近真实校园空间，而不是抽象节点连线图。
2. 让道路和路线高亮沿真实道路几何展示，减少直线穿楼、穿湖、穿绿地的问题。
3. 保持现有查询、推荐、单目标路径、多目标路径、室内外导航接口不被破坏。
4. 支持离线或弱网演示时降级到本地 Leaflet 资源和现有 SVG 简图。
5. 把方案 B 控制为可试验、可回退、可度量的产品增强，而不是一次性重写地图系统。

## 2. 技术结论

推荐采用“Leaflet + GeoJSON + 可选 OSM 路网抽取”的轻量方案 B。

主选技术栈：

1. Leaflet：负责地图容器、瓦片底图、GeoJSON 图层、标注、缩放和平移。
2. GeoJSON：作为后端到前端的地图数据契约，表达节点、道路、路径高亮和兴趣点。
3. OpenStreetMap / Overpass / OSMnx：用于尝试抽取北京大学校园及周边道路几何。
4. Mapshaper：用于必要时裁剪、简化和检查 GeoJSON。
5. 原 SVG 地图：作为 fallback，不删除、不破坏。

暂不把 MapLibre GL JS 作为第一实现目标。它的视觉上限更高，但 WebGL、样式、瓦片、坐标校准和调试成本更高，不适合在课程最后冲刺阶段作为主路径。

## 3. 本地资料与资源位置

已下载的资料分为两类。

文档资料位于：

```text
docs/references/map-plan-b/
```

前端 Leaflet 运行资源位于：

```text
src/ui/static/vendor/leaflet/
```

关键资料用途如下：

| 文件 | 用途 |
| --- | --- |
| `docs/references/map-plan-b/leaflet-geojson-example.html` | Leaflet GeoJSON 图层写法、样式和交互参考 |
| `docs/references/map-plan-b/leaflet-reference.html` | Leaflet API 完整参考 |
| `docs/references/map-plan-b/rfc7946-geojson.txt` | GeoJSON 标准，确认 `FeatureCollection`、`LineString`、坐标顺序 |
| `docs/references/map-plan-b/osmnx-getting-started.html` | OSMnx 获取路网、构图、保存数据的参考 |
| `docs/references/map-plan-b/overpass-command-line.html` | Overpass 命令行查询参考 |
| `docs/references/map-plan-b/overpass-official-doc-index.html` | Overpass 官方文档入口 |
| `docs/references/map-plan-b/mapshaper-command-reference.html` | Mapshaper 命令参考，用于裁剪和简化 GeoJSON |
| `docs/references/map-plan-b/mapshaper-cli-command-line.html` | Mapshaper 命令行使用方式 |
| `docs/references/map-plan-b/maplibre-add-geojson-line.html` | MapLibre 备选路线参考，不作为第一实现目标 |
| `src/ui/static/vendor/leaflet/leaflet.js` | 本地 Leaflet JS，支持离线加载 |
| `src/ui/static/vendor/leaflet/leaflet.css` | 本地 Leaflet CSS |
| `src/ui/static/vendor/leaflet/images/` | Leaflet 默认 marker 图片 |
| `src/ui/static/vendor/leaflet/LICENSE` | Leaflet MIT 许可证 |

## 4. 总体架构

方案 B 不直接替换现有地图，而是增加一个可切换的地图渲染器。

建议渲染器开关：

```text
simple_svg   当前稳定 SVG 简图
leaflet_geo  方案 B 准真实地图层
```

建议接口结构：

```text
GET /api/bootstrap
  返回原有页面启动数据，并增加 map_renderer 默认值和地图能力声明

GET /api/map/geojson?site_id=PKU
  返回当前站点地图 GeoJSON，包括节点、道路和基础元数据

POST /api/route
  保持现有路径规划结果，同时 ui 中增加 route_geojson 或 route_line_points

POST /api/route/multi
  保持现有多目标结果，同时 ui 中增加多段路线 GeoJSON
```

前端结构建议：

```text
src/ui/static/app.js
  保留 renderMap()
  新增 renderSvgMap()
  新增 renderLeafletMap()
  新增 syncLeafletRouteLayer()
  新增 renderer fallback 判断

src/ui/static/index.html
  引入本地 Leaflet CSS/JS
  地图容器允许 SVG 和 Leaflet div 共存或互斥显示

src/ui/static/styles.css
  增加 Leaflet 容器高度、图层按钮、legend、route overlay 样式
```

后端结构建议：

```text
src/ui/demo_service.py
  新增 build_map_geojson()
  新增 build_route_geojson()
  扩展 _build_map_edges()，读取 geometry 或生成 fallback line

src/ui/demo_server.py
  新增 /api/map/geojson endpoint

data/sites/PKU/outdoor.json
  给 edge 增加可选 geometry 字段

data/sites/PKU/geo/
  可新增 osm_raw.geojson、roads_simplified.geojson、roads_matched.json 等派生数据
```

## 5. 数据契约设计

### 5.1 道路边 geometry 字段

在现有 `edges[]` 上增加可选字段：

```json
{
  "from": "gate_north",
  "to": "square_center",
  "distance": 80,
  "type": "outdoor_road",
  "name": "西门大道",
  "geometry": [
    {"lat": 39.9929, "lng": 116.3055},
    {"lat": 39.9927, "lng": 116.3060},
    {"lat": 39.9924, "lng": 116.3064}
  ]
}
```

约束：

1. `geometry` 是可选字段，缺失时前端用 `from/to` 节点位置生成直线。
2. `geometry[0]` 应接近 `from` 节点坐标，最后一点应接近 `to` 节点坐标。
3. 内部仍使用 `{"lat": ..., "lng": ...}` 便于人工维护。
4. 转成 GeoJSON 时必须输出 `[lng, lat]`，符合 RFC 7946。
5. 对双向边可以复用同一条 geometry，反向边由服务层自动 reverse，减少数据维护量。

### 5.2 地图 GeoJSON 输出

建议 `/api/map/geojson` 返回：

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [[116.3055, 39.9929], [116.3060, 39.9927]]
      },
      "properties": {
        "kind": "edge",
        "from": "gate_north",
        "to": "square_center",
        "name": "西门大道",
        "edge_type": "outdoor_road",
        "distance_m": 80
      }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [116.3070, 39.9915]
      },
      "properties": {
        "kind": "node",
        "id": "library",
        "name": "图书馆",
        "category": "education"
      }
    }
  ]
}
```

### 5.3 路线高亮 GeoJSON

单目标路线建议返回一条 `LineString`：

```json
{
  "type": "Feature",
  "geometry": {
    "type": "LineString",
    "coordinates": [[116.3055, 39.9929], [116.3060, 39.9927], [116.3070, 39.9915]]
  },
  "properties": {
    "kind": "route",
    "route_type": "single_target",
    "distance_m": 110,
    "estimated_time_s": 75
  }
}
```

多目标路线建议返回 `FeatureCollection`，每一段 leg 是独立 `LineString`，同时给每段设置 `leg_index`、`from_node_id`、`to_node_id`，便于 UI 用不同透明度或编号展示。

## 6. 实施阶段

### 阶段 0：安全基线

目标：保证方案 B 可回退。

任务：

1. 确认当前分支为 `experiment/map-plan-b`。
2. 保留当前 SVG 地图逻辑，不删除 `renderMap()` 的稳定路径。
3. 新增 `map_renderer` 开关，默认仍可设为 `simple_svg`。
4. 新增回归测试，确认现有 `/api/bootstrap`、`/api/route`、`/api/route/multi` 仍能运行。

验收标准：

1. 切换开关为 `simple_svg` 时，现有 UI 行为完全不变。
2. 任何 Leaflet 初始化失败，都能回退到 SVG 地图。

### 阶段 1：Leaflet 静态接入

目标：先让真实地图容器稳定显示。

任务：

1. 在 `index.html` 引入 `src/ui/static/vendor/leaflet/leaflet.css` 和 `leaflet.js`。
2. 增加 Leaflet 容器，例如 `#leaflet-map`。
3. 初始化 Leaflet map，中心点默认使用 PKU 节点 bounds 的中心。
4. 优先使用公开瓦片源进行实验，同时保留无底图模式。
5. 加入地图图层状态文案，例如“真实底图实验模式”。

验收标准：

1. 页面加载后 Leaflet 地图可缩放、拖动。
2. 无网络或瓦片失败时，至少节点和道路 GeoJSON 仍能显示在空白底图上。
3. 不影响其他功能页提交表单和状态反馈。

### 阶段 2：现有图数据转 GeoJSON

目标：先不用 OSM 数据，直接把现有节点和边转换成 GeoJSON，让前后端链路跑通。

任务：

1. 后端新增 `build_map_geojson()`。
2. 节点输出为 `Point`。
3. 边输出为 `LineString`，有 `geometry` 用 geometry，没有则用 from/to 坐标。
4. 前端用 `L.geoJSON()` 渲染 roads layer 和 nodes layer。
5. 节点点击后复用现有地图定位和路线规划入口。

验收标准：

1. Leaflet 上能看到所有室外节点。
2. Leaflet 上能看到所有室外边。
3. 道路点击能展示名称、距离、边类型。
4. 节点点击能展示名称、类别，并支持规划路线入口。

### 阶段 3：路线高亮贴路

目标：让单目标和多目标路线沿 edge geometry 拼接。

任务：

1. 服务层根据 `route.path` 找相邻节点对应的 edge。
2. 每段 edge 有 geometry 时使用 geometry。
3. edge 方向与路径方向相反时 reverse geometry。
4. 拼接时去重相邻段重复端点。
5. 前端新增 route layer，规划成功后更新路线高亮。

验收标准：

1. 单目标路径高亮不再直接穿过非道路区域。
2. 多目标路径能按 leg 分段展示。
3. 路线摘要、步骤列表、地图高亮三者一致。
4. geometry 缺失时仍能用直线段补齐，不报错。

### 阶段 4：抽取或补齐真实道路几何

目标：把关键演示路径升级为真实道路几何。

候选路径：

1. 使用 OSMnx 按北京大学边界或中心点半径抽取道路/步道。
2. 使用 Overpass 查询 `highway=footway/path/service/residential/pedestrian` 等要素。
3. 用 Mapshaper 裁剪和简化 GeoJSON。
4. 人工将 OSM 路段与现有 `outdoor.json` 的 edge 对齐。

建议先覆盖演示主路径：

1. 西门到百周年纪念广场。
2. 百周年纪念广场到图书馆。
3. 图书馆到农园食堂。
4. 东门到十字路口。
5. 南门到第一教学楼。
6. 十字路口到宿舍区。
7. 食堂到便利店。
8. 图书馆到室内图入口。

验收标准：

1. 关键演示路线明显沿真实道路或近似真实道路展示。
2. 至少 80% 演示路径边具备 geometry。
3. 所有 geometry 坐标落在 PKU bounds 附近，无明显漂移。
4. 路线距离与 geometry 形状不存在明显矛盾。

### 阶段 5：视觉与验收包装

目标：让方案 B 在答辩中有明显加分点。

任务：

1. 道路分层样式：主路、步道、服务路采用不同颜色和线宽。
2. 路线高亮样式：外层半透明描边，内层亮色路径，增强可读性。
3. 节点样式：入口、教学、餐饮、宿舍、服务设施使用不同 icon 或颜色。
4. Legend：说明底图、道路层、当前路径、室内节点。
5. Debug 面板：显示当前渲染器、GeoJSON feature 数、geometry 覆盖率。
6. 帮助页文案：说明“真实底图实验模式”和 fallback 策略。

验收标准：

1. 答辩现场能清楚解释数据结构从图到 GeoJSON 的映射。
2. 能展示直线 SVG 与 Leaflet 真实地图层的对比。
3. 能解释为什么 GeoJSON 坐标顺序是 `[lng, lat]`。
4. 能现场切换或回退到稳定 SVG 模式。

## 7. 路网数据获取方案

### 7.1 OSMnx 路线

优点：

1. Python 生态，适合放进项目脚本。
2. 可直接获取道路图、节点、边和几何。
3. 可保存为 GraphML、GeoPackage 或 GeoJSON。

风险：

1. 需要联网访问 OpenStreetMap/Overpass。
2. 校园内部步道数据可能不完整。
3. 抽取到的是 OSM 路网，和当前课程图节点 ID 不会天然一致，需要匹配。

建议用途：

1. 生成候选真实道路 geometry。
2. 不直接替换课程图算法结构。
3. 人工或半自动映射到 `outdoor.json` 的 edge geometry。

### 7.2 Overpass 路线

优点：

1. 查询更直接，可精确过滤 `highway` 类型。
2. 输出可控，适合小范围校园路网抽取。

风险：

1. 查询语言需要调试。
2. API 稳定性受公共服务影响。
3. 数据清洗仍需要额外步骤。

建议用途：

1. 用作 OSMnx 的备选或验证。
2. 保存原始查询和原始 GeoJSON，保证数据来源可追溯。

### 7.3 手工补 geometry 路线

优点：

1. 最稳定，能保证演示路径效果。
2. 不依赖外部 API。
3. 容易和现有节点 ID 对齐。

风险：

1. 工作量较大。
2. 几何精度取决于人工采点质量。

建议用途：

1. 关键演示路线必须手工兜底。
2. 非关键边可先用直线 fallback。

## 8. 测试计划

后端测试：

1. `build_map_geojson()` 返回合法 `FeatureCollection`。
2. 所有 GeoJSON 坐标均为 `[lng, lat]`。
3. 所有 edge feature 都有 `from`、`to`、`distance_m`。
4. geometry 缺失时能生成 fallback LineString。
5. route path 中相邻节点可以找到对应 edge 或生成 fallback。
6. 反向 edge geometry 能正确 reverse。

前端测试：

1. Leaflet 资源能从本地路径加载。
2. 地图初始化失败时显示 SVG fallback。
3. 查询结果定位节点后，Leaflet marker/layer 能高亮。
4. 单目标路线规划后 route layer 更新。
5. 多目标路线规划后分段 route layer 更新。
6. 切换站点或清空路线后 route layer 清除。

人工验收：

1. 打开首页，进入应用页，地图不报错。
2. 执行“去图书馆”预设，路径高亮正确。
3. 执行“图书馆 + 食堂”多目标预设，分段路径正确。
4. 断网或瓦片失败时，系统仍可演示核心功能。
5. 切换回 `simple_svg` 后，旧地图可用。

## 9. 风险与回退策略

| 风险 | 影响 | 处理 |
| --- | --- | --- |
| 瓦片源加载失败 | 底图空白 | 本地 Leaflet + GeoJSON 空白底图继续显示，或回退 SVG |
| OSM 数据不完整 | 路线仍有直线段 | 关键路线手工补 geometry |
| 坐标顺序错误 | 地图点位漂移 | 后端集中转换 `[lng, lat]`，测试覆盖 |
| Leaflet 与现有 SVG 状态冲突 | 地图显示异常 | 用 renderer 开关隔离两个渲染器 |
| 多目标路线拼接复杂 | 高亮和步骤不一致 | 先单目标稳定，再接多目标 |
| 第 14-15 周时间不足 | 影响验收稳定性 | 只合并阶段 0-3，阶段 4-5 作为增强 |

回退方式：

1. 功能级回退：前端切回 `simple_svg`。
2. 分支级回退：放弃 `experiment/map-plan-b`，回到 `main`。
3. 文件级回退：保留 Leaflet 资源和文档，撤销业务代码改动。
4. 演示级回退：答辩时只展示方案 B 对比截图和稳定 SVG 主链路。

## 10. 里程碑安排

### M1：方案资料与数据契约完成

产出：

1. 本路线计划文档。
2. 本地官方资料和 Leaflet 资源。
3. GeoJSON 数据契约。
4. 风险和回退说明。

状态：已完成资料下载，待后续进入实现。

### M2：Leaflet 空地图跑通

预计工作量：0.5 到 1 人日。

产出：

1. Leaflet 容器。
2. 本地 JS/CSS 加载。
3. 地图初始化和 fallback。

### M3：现有地图数据 GeoJSON 化

预计工作量：1 到 2 人日。

产出：

1. `/api/map/geojson`。
2. roads layer。
3. nodes layer。
4. 后端测试。

### M4：路线高亮贴路

预计工作量：1 到 2 人日。

产出：

1. 单目标 route GeoJSON。
2. 多目标 leg GeoJSON。
3. 前端 route layer。
4. 关键路线回归测试。

### M5：真实 geometry 补齐

预计工作量：2 到 4 人日。

产出：

1. OSM/Overpass 候选数据。
2. 关键路线 geometry。
3. geometry 覆盖率统计。

### M6：视觉包装与答辩材料

预计工作量：1 到 2 人日。

产出：

1. 图层 legend。
2. 调试信息。
3. 新旧地图对比截图。
4. 用户说明和验收文案更新。

## 11. 是否值得继续推进

建议继续推进，但必须按阶段验收。最小可合并版本是 M2 + M3 + 单目标 M4；如果这三个阶段不稳定，就不进入 M5 的真实路网数据抽取。

对高分最有价值的讲法不是“我们接了一个地图插件”，而是：

1. 图算法仍使用课程图结构和 Dijkstra / 多目标路径规划。
2. UI 表现层通过 GeoJSON 把算法结果映射到真实地图空间。
3. 道路 geometry 让路径高亮从“节点连线”升级为“贴近真实道路”。
4. 系统保留 fallback，因此不是脆弱的演示工程。

