# 地图方案 B 第三阶段 geometry 覆盖记录

## 范围

本阶段继续沿用第二阶段的 Leaflet + GeoJSON + route overlay 架构，不重写 routing、graph loader 或前端 UI。道路 geometry 仍维护在 `data/sites/PKU/outdoor.json` 的 edge 上，格式为：

```json
[
  {"lat": 39.9929, "lng": 116.3055},
  {"lat": 39.9917, "lng": 116.3065}
]
```

GeoJSON 输出继续转换为 RFC 7946 的 `[lng, lat]`。

## 本阶段补齐区域

第二阶段基线为 8/81 条去重可绘制 edge 具备 geometry，覆盖率约 9.88%。第三阶段新增了以下优先区域：

1. 东门到中心路口：`gate_east -> road_cross`。
2. 南门到第一教学楼：`gate_south -> teaching_building_1`。
3. 体育场到西门方向服务路径：`sports_ground -> gate_north`。
4. 东门停车服务路径：`parking_lot -> gate_east`。
5. 图书馆区洗手间短便道：`toilet_lib_area -> library`，并补齐反向数据质量。
6. 体育场洗手间短便道：`toilet_sports_area -> sports_ground`。

已有第二阶段 geometry 继续保留：

1. `gate_north -> square_center`
2. `library -> square_center`
3. `square_center -> road_cross`
4. `road_cross -> teaching_building_1`
5. `road_cross -> teaching_building_2`
6. `road_cross -> canteen`
7. `road_cross -> convenience_store`
8. `road_cross -> dormitory_1`

## 当前覆盖率

统计口径与 `/api/map/geojson` 一致，使用服务层去重后的 81 条可绘制 outdoor edge：

```text
edge_feature_count: 81
geometry_edge_count: 14
fallback_edge_count: 67
geometry_coverage_ratio: 0.1728
```

`/api/map/geojson` 的 `stats` 和 `/api/bootstrap` 的 `map` 对象均暴露：

```text
geometry_edge_count
fallback_edge_count
geometry_coverage_ratio
```

## 仍然 fallback 的 edge

以下 edge 当前仍使用 from/to 节点直线 fallback。它们保留为后续阶段继续补齐或答辩说明使用：

```text
gate_north -> campus_service_01
square_center -> campus_service_02
library -> campus_service_03
teaching_building_1 -> campus_service_04
teaching_building_2 -> campus_service_05
road_cross -> campus_service_06
canteen -> campus_service_07
convenience_store -> campus_service_08
dormitory_1 -> campus_service_09
sports_ground -> campus_service_10
gate_east -> campus_service_11
gate_south -> campus_service_12
toilet_lib_area -> campus_service_14
toilet_sports_area -> campus_service_15
square_center -> campus_service_16
road_cross -> campus_service_17
library -> campus_service_18
canteen -> campus_service_19
dormitory_1 -> campus_service_20
sports_ground -> campus_service_21
gate_north -> campus_service_22
gate_east -> campus_service_23
gate_south -> campus_service_24
campus_service_01 -> campus_service_02
campus_service_02 -> campus_service_03
campus_service_03 -> campus_service_04
campus_service_04 -> campus_service_05
campus_service_05 -> campus_service_06
campus_service_06 -> campus_service_07
campus_service_07 -> campus_service_08
campus_service_08 -> campus_service_09
campus_service_09 -> campus_service_10
campus_service_10 -> campus_service_11
campus_service_11 -> campus_service_12
campus_service_12 -> campus_service_13
campus_service_13 -> campus_service_14
campus_service_14 -> campus_service_15
campus_service_15 -> campus_service_16
campus_service_16 -> campus_service_17
campus_service_17 -> campus_service_18
campus_service_18 -> campus_service_19
campus_service_19 -> campus_service_20
campus_service_20 -> campus_service_21
campus_service_21 -> campus_service_22
campus_service_22 -> campus_service_23
campus_service_23 -> campus_service_24
campus_service_01 -> campus_service_05
campus_service_02 -> campus_service_06
campus_service_03 -> campus_service_07
campus_service_04 -> campus_service_08
campus_service_05 -> campus_service_09
campus_service_06 -> campus_service_10
campus_service_07 -> campus_service_11
campus_service_08 -> campus_service_12
campus_service_09 -> campus_service_13
campus_service_10 -> campus_service_14
campus_service_11 -> campus_service_15
campus_service_12 -> campus_service_16
campus_service_13 -> campus_service_17
campus_service_14 -> campus_service_18
campus_service_15 -> campus_service_19
campus_service_16 -> campus_service_20
campus_service_17 -> campus_service_21
campus_service_18 -> campus_service_22
campus_service_19 -> campus_service_23
campus_service_20 -> campus_service_24
gate_east -> campus_service_13
```

## 质量约束

新增测试覆盖以下约束：

1. geometry 坐标必须为数字。
2. geometry 至少包含 2 个点。
3. geometry 首点接近 `from` 节点，末点接近 `to` 节点。
4. geometry 坐标落在 PKU 当前地图 bounds 附近。
5. GeoJSON 输出坐标顺序为 `[lng, lat]`。
6. 缺失 geometry 的 edge 继续 fallback，不中断 route overlay。
