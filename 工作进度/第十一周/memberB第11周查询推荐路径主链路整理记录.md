# memberB第11周查询推荐路径主链路整理记录

## 1. 任务定位

第 9 项目标是确认第九周、第十周已有的查询、推荐、路径能力在第十一周新 Web 骨架下没有退化。

本阶段不再新增业务功能，重点做主链路梳理和防回归测试。

## 2. 检查范围

已检查的成员 B 主链路：

- 综合查询：`DemoUIService.scenic_search(...)`
- 场所查询：`DemoUIService.place_search(...)`
- 美食推荐：`DemoUIService.catering_search(...)`
- 单目标路径：`DemoUIService.plan_route(...)`
- 多目标路径：`DemoUIService.plan_multi_route(...)`

涉及底层能力：

- `src/search/search_service.py`
- `src/recommend/catering_service.py`
- `src/recommend/ranking.py`
- `src/routing/router.py`
- `src/ui/demo_service.py`
- `src/ui/static/app.js`

## 3. 主链路确认结果

综合查询链路：

- 输入 `图书馆` 和 `education`。
- 返回结果包含 `route_target_node_id = library`。
- 可继续调用单目标路径规划。
- `gate_north -> library` 路径距离为 `110.0 m`。
- 地图可绘制路径节点为 `gate_north -> square_center -> library`。

场所查询链路：

- 输入 `洗手间` 和 `restroom`。
- 仍按真实路径距离排序。
- 首个结果为 `toilet_sports_area`。
- 该结果可继续进入单目标路径规划。

美食推荐链路：

- 默认餐饮推荐仍支持 Top-K。
- `sort_field = distance_m` 时按真实路径距离排序。
- 首个结果为 `lib_cafe`。
- 该结果可继续进入单目标路径规划，路径中包含 `lib_cafe`。

多目标路径链路：

- 可把综合查询结果和美食推荐结果组合为多目标路线。
- 返回 `route_type = multi_target`。
- 返回目标数量、分段数量、可绘制地图路径和分段摘要。

## 4. 本次补充测试

在 `tests/test_ui_demo.py` 中新增：

- `test_demo_main_query_recommend_route_chains_remain_available`

该测试覆盖：

- 综合查询结果是否仍可路由。
- 场所查询是否仍按距离排序。
- 场所查询结果是否仍可进入路径规划。
- 美食推荐是否仍按距离排序。
- 美食推荐结果是否仍可进入路径规划。
- 多目标路径是否可复用查询和推荐产生的目标节点。

## 5. 结论

第九周、第十周主链路在第十一周 Web 骨架、日记中心和 AIGC 入口加入后没有退化。

当前不需要修改成员 A 路由接口，也不需要成员 C 继续补数据才能完成第 9 项。

## 6. 验证结果

已通过：

- `python -B tests/test_ui_demo.py`
- `python -B tests/test_search.py`
- `python -B tests/test_recommend.py`
- `python -B tests/test_routing.py`
- `python -B tests/test_integration.py`

## 7. 修改范围

测试：

- `tests/test_ui_demo.py`

文档：

- `工作进度/第十一周/memberB第11周查询推荐路径主链路整理记录.md`
- `工作进度/第十一周/memberB第11周任务推进清单.md`
