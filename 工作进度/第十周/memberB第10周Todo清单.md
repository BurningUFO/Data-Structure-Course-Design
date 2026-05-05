# memberB第10周Todo清单

## 本周执行主线

- [x] 按 `README.md` 完成启动流程：`git pull`、检查 `工作进度/第十周/`、确认本地环境
- [x] 对齐第十周总目标，明确 Member B 本周职责是“全文检索业务接入 + 统一输出深化 + 演示入口扩展”
- [x] 在统一响应结构中补 `results` 字段，同时保留 `data` 兼容第七至第九周调用方
- [x] 在 `src/diary/` 增加第十周全文检索业务入口，先提供可运行回退实现
- [x] 验证全文检索业务层已切换到 `src.compress.fulltext.search_diary_fulltext`
- [x] 扩展 `src/search/cli_demo.py`，补 `--week10` 演示入口
- [x] 在 `--week10` 演示入口中补压缩 / 解压摘要展示，完成与 C 侧压缩模块的最小预对接
- [x] 补 `tests/test_search.py`、`tests/test_diary.py`、`tests/test_integration.py` 的第十周断言
- [x] 等待 Member C 的正式倒排索引实现接入当前业务入口
- [x] 与 Member C 确认压缩模块第十周保持独立演示，并在 CLI 中提供摘要展示
- [x] 产出 `工作进度/第十周/memberB第10周工作内容陈述.md`

## 本周交付物

- `src/search/response.py`
- `src/search/fuzzy_search.py`
- `src/search/cli_demo.py`
- `src/diary/diary_service.py`
- `src/diary/fulltext_service.py`
- `docs/项目代码骨架与职责划分.md`
- `tests/test_search.py`
- `tests/test_diary.py`
- `tests/test_integration.py`

## 仍需组内协作确认

- [x] Member C 的全文检索正式返回结构已覆盖 `matched_terms`、`score`、`destination_node_id`
- [x] 缺失 `destination_node_id` 的日记全文检索结果，在业务层统一降级为“仅展示，不给路径提示”
- [x] 压缩 / 解压第十周继续保持命令级演示，第十一周再评估是否接入日记管理业务
