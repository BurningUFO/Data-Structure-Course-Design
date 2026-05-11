# memberB第11周AIGC轻量演示入口记录

## 1. 任务定位

第 8 项目标是把 AIGC 从文档计划项变成 Web 中可见、可触发、可测试的轻量演示入口。

当前阶段不接真实生成模型，只完成“图片占位 + 文字描述 -> 模板化预览结果”的最小闭环。

## 2. 数据来源

默认读取：

- `data/aigc_media_samples.json`

当前样例字段：

- `sample_id`
- `diary_id`
- `image_placeholder`
- `text_prompt`
- `style`
- `duration_s`
- `output_type`
- `preview_placeholder`
- `status`

## 3. 完成内容

服务层新增：

- `DemoUIService.aigc_preview(payload)`
- `_load_aigc_samples()`
- `_build_aigc_sample_options()`
- `_build_aigc_style_options()`
- `_build_aigc_preview(...)`
- `_build_aigc_storyboard(...)`

HTTP API 新增：

- `POST /api/aigc/preview`

Bootstrap 新增：

- `aigc_samples`
- `controls.aigc_styles`
- `presets.aigc`
- `stats.aigc_sample_count`

Web 页面新增：

- 顶部导航 `AIGC 演示`
- 左侧标签页 `AIGC 演示`
- 样例选择
- 图片占位展示
- 文字描述输入
- 风格模板选择
- 预览时长输入
- 快捷样例按钮
- 右侧结果区分镜预览展示

## 4. 输出结构

AIGC 预览接口继续使用统一 Response 风格：

- `success`
- `message`
- `query_type`
- `filters`
- `metadata`
- `total`
- `data`
- `results`

单条预览结果包含：

- `sample_id`
- `diary_id`
- `title`
- `image_placeholder`
- `text_prompt`
- `style`
- `style_label`
- `duration_s`
- `output_type`
- `preview_placeholder`
- `status`
- `prototype_notice`
- `prompt_summary`
- `storyboard_frames`
- `keyframes`
- `generation_pipeline`
- `source`

## 5. 原型口径

当前明确为轻量原型：

- `metadata.prototype_mode = template_preview`
- `metadata.real_model_called = false`
- `source.real_model_called = false`

这样可以满足第十一周“浏览器可见、可触发、可测试”的演示要求，同时避免引入外部模型依赖。

## 6. 页面演示流程

1. 启动 Web 服务：`python -B -m src.ui.demo_server`
2. 浏览器访问：`http://127.0.0.1:8765`
3. 打开 `AIGC 演示`。
4. 选择媒体样例，页面自动填充图片占位、文字描述、风格和时长。
5. 可手动修改文字描述或风格。
6. 点击 `生成轻量预览`。
7. 右侧结果区展示图片占位、预览占位、分镜帧和处理流程。

## 7. 验证结果

已通过：

- `node --check src\ui\static\app.js`
- `python -B tests/test_ui_demo.py`
- `python -B -m py_compile src/ui/demo_service.py src/ui/demo_server.py`

## 8. 修改范围

代码：

- `src/ui/demo_service.py`
- `src/ui/demo_server.py`
- `src/ui/static/index.html`
- `src/ui/static/app.js`
- `src/ui/static/styles.css`

测试：

- `tests/test_ui_demo.py`

文档：

- `工作进度/第十一周/memberB第11周AIGC轻量演示入口记录.md`
- `工作进度/第十一周/memberB第11周任务推进清单.md`
