# memberA第8周Todo清单

## 今日收口任务
- [x] 明确 `site_id` 语义，并确定为接口末尾的可选参数
- [x] 明确 `shortest_time` 返回单位为秒
- [x] 让 `query_routing(...)` 同时返回总距离和总时间
- [x] 为 `data/sites/{site_id}/*.json` 提供 A 侧原生 loader
- [x] 修复 `query_multi_target(...)` 聚合字段不完整问题
- [x] 用真实 `PKU` 标准分层数据验证单目标、跨层、多目标相关逻辑
- [x] 更新接口文档与第八周工作陈述

## 仍需组内协作确认
- [ ] 若继续保留 `data/成员Cdata/scenic_spots.json`，成员 C 补 `node_id` 或 `map_node_id`
- [ ] 若后续完全切换到标准分层数据，A/C 持续在协作文档中维持“旧 scenic_spots.json 仅历史兼容”的统一口径
