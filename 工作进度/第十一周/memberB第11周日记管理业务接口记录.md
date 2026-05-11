# memberB第11周日记管理业务接口记录

## 1. 任务定位

第 6 项目标是把日记模块从“只能查询”推进到“可管理”，但暂不做完整浏览器页面。页面表单和日记中心交互留到第 7 项完成。

本阶段实现的是业务接口与 HTTP API 的最小闭环，覆盖创建、编辑、删除、评分和媒体占位字段。

## 2. 完成内容

已完成日记业务服务接口：

- `DiaryService.create_diary(payload)`
- `DiaryService.update_diary(diary_id, updates)`
- `DiaryService.delete_diary(diary_id)`
- `DiaryService.rate_diary(diary_id, rating)`

已完成快捷调用入口：

- `create_diary(...)`
- `update_diary(...)`
- `delete_diary(...)`
- `rate_diary(...)`

已完成 Web 服务层接口：

- `DemoUIService.create_diary(payload)`
- `DemoUIService.update_diary(payload)`
- `DemoUIService.delete_diary(payload)`
- `DemoUIService.rate_diary(payload)`

已完成 HTTP 路由：

- `POST /api/diaries`
- `POST /api/diaries/create`
- `POST /api/diaries/update`
- `POST /api/diaries/delete`
- `POST /api/diaries/rate`

## 3. 字段与口径

日记管理接口支持字段：

- `title`
- `content`
- `author_id`
- `author_name`
- `destination`
- `destination_node_id`
- `heat`
- `rating`
- `tags`
- `views`
- `created_at`
- `images`
- `videos`

统一输出字段继续保留：

- `success`
- `message`
- `query_type`
- `filters`
- `metadata`
- `total`
- `data`
- `results`

Web 服务层额外补充：

- `route_target_node_id`
- `route_target_name`
- `has_map_location`
- `ui.source`
- `ui.storage_mode`
- `ui.record_count`
- `metadata.ui_contract.media_fields`

## 4. 存储策略

当前采用内存态管理，不直接写回 `data/diary_data.json`。

这样做的原因是标准样例数据属于多人共享数据源，第 6 项只需要证明业务管理链路可用，不应在演示过程中破坏基线数据。

接口返回中已明确：

- `metadata.storage_mode = memory_only`
- `metadata.data_source.write_back = false`
- `metadata.ui_contract.write_back = false`

后续如果课程要求必须持久化，可在当前接口外层增加受控写回或临时用户数据文件，不需要推翻本次业务接口。

## 5. 校验规则

已补充的基础校验：

- 创建日记时 `title` 不能为空。
- 编辑日记时如果传入 `title`，则新标题不能为空。
- 重复 `id` 创建会返回失败。
- 删除、编辑、评分不存在的日记会返回失败。
- 评分必须是数字，最终限制在 `0` 到 `5` 之间。

## 6. 与后续任务关系

第 6 项已经完成业务接口闭环。

第 7 项需要继续完成：

- 在日记中心页面接入创建表单。
- 在日记中心页面接入编辑入口。
- 在日记中心页面接入评分入口。
- 在日记中心页面展示 `images` 和 `videos` 媒体占位字段。
- 在日记中心页面接入删除演示入口。

## 7. 验证结果

已通过：

- `python -B tests/test_diary.py`
- `python -B tests/test_ui_demo.py`
- `python -B -m py_compile src/diary/diary_service.py src/diary/__init__.py src/ui/demo_service.py src/ui/demo_server.py`

## 8. 修改范围

代码：

- `src/diary/diary_service.py`
- `src/diary/__init__.py`
- `src/ui/demo_service.py`
- `src/ui/demo_server.py`

测试：

- `tests/test_diary.py`
- `tests/test_ui_demo.py`

文档：

- `工作进度/第十一周/memberB第11周日记管理业务接口记录.md`
- `工作进度/第十一周/memberB第11周任务推进清单.md`
