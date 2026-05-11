# memberB第11周日记中心Web页面记录

## 1. 任务定位

第 7 项是在第 6 项“日记管理业务接口”基础上，把日记创建、编辑、评分、删除和媒体占位展示接入浏览器页面。

本阶段不改变日记标准数据文件，继续沿用第 6 项的内存态演示策略。

## 2. 完成内容

日记中心页面已拆成两块：

- 全文检索：保留第十周已有的日记全文检索入口。
- 日记管理：新增创建、编辑、评分、清空表单等操作区。

页面新增输入项：

- 标题
- 正文
- 目的地名称
- 绑定路线目标
- 评分
- 标签
- 图片占位
- 视频占位

结果卡片新增操作：

- 载入编辑
- 快速评 5 分
- 删除日记
- 从绑定目的地规划路线

结果卡片新增展示：

- 目的地
- 创建时间
- 评分
- 图片占位字段
- 视频占位字段

## 3. 交互流程

创建流程：

1. 在“日记中心”填写标题、正文、目的地、评分、标签和媒体占位。
2. 点击“创建日记”。
3. 页面调用 `POST /api/diaries/create`。
4. 创建结果展示在右侧结果区。
5. 如果绑定了路线目标，可直接点击“从当前起点规划路线”。

编辑流程：

1. 先通过全文检索或创建结果拿到日记卡片。
2. 点击“载入编辑”。
3. 表单进入当前日记编辑状态。
4. 修改字段后点击“更新所选日记”。
5. 页面调用 `POST /api/diaries/update`。

评分流程：

- 可在表单中填写评分后点击“仅更新评分”。
- 也可在日记卡片中点击“快速评 5 分”。
- 页面调用 `POST /api/diaries/rate`。

删除流程：

- 点击日记卡片中的“删除日记”。
- 页面调用 `POST /api/diaries/delete`。
- 删除成功后结果区显示被删除记录，并标记“已从内存态移除”。

## 4. 与业务接口对齐

已接入第 6 项完成的接口：

- `POST /api/diaries/create`
- `POST /api/diaries/update`
- `POST /api/diaries/delete`
- `POST /api/diaries/rate`

仍保留全文检索接口：

- `POST /api/diaries/fulltext`

Web 服务层已补充全文检索结果的日记原始字段合并能力，因此从全文检索结果载入编辑时，可以带出正文、标签、图片和视频占位字段。

## 5. 存储口径

当前页面展示的是内存态管理能力：

- 新增、编辑、评分、删除只影响当前 Web 服务实例中的日记列表。
- 不写回 `data/diary_data.json`。
- 刷新服务后恢复标准样例数据。

该口径适合课程演示和联调，不会污染公共样例数据。

## 6. 验证结果

已通过：

- `node --check src\ui\static\app.js`
- `python -B tests/test_ui_demo.py`
- `python -B tests/test_diary.py`
- `python -B -m py_compile src/ui/demo_service.py src/ui/demo_server.py src/diary/diary_service.py`

## 7. 修改范围

代码：

- `src/ui/static/index.html`
- `src/ui/static/app.js`
- `src/ui/static/styles.css`
- `src/ui/demo_service.py`

测试：

- `tests/test_ui_demo.py`

文档：

- `工作进度/第十一周/memberB第11周日记中心Web页面记录.md`
- `工作进度/第十一周/memberB第11周任务推进清单.md`
