# 成员 B 接口依赖说明

## 1. 文档目的

本文档用于明确成员 B 在第 5 周设计方案阶段，和成员 A、成员 C 之间需要提前约定的接口内容。

目标有两个：

1. 减少后续联调时因为字段不统一、输入输出不一致造成的返工
2. 让成员 B 的查询、推荐、日记业务逻辑可以尽早并行开发

---

## 2. 成员 B 的接口需求概览

成员 B 主要负责：

- 查询
- 排序
- 推荐
- 日记业务逻辑

因此，成员 B 主要依赖两类外部能力：

### 来自成员 A 的能力

- 真实路径距离计算
- 路径规划结果返回
- 不同交通方式下的距离或时间结果

### 来自成员 C 的能力

- 结构化基础数据
- 日记全文检索结果
- 数据字典与测试样例

---

## 3. 成员 B 与成员 A 的接口约定

成员 A 负责图结构和路径规划，因此成员 B 最关心的是“距离接口”和“路径结果接口”。

## 3.1 真实距离接口

### 用途

用于：

- 场所查询按距离排序
- 美食推荐按距离排序
- 未来可能的“推荐 + 路线”联合展示

### 建议输入

```json
{
  "site_id": "campus_001",
  "start_node_id": "node_105",
  "target_node_id": "node_233",
  "strategy": "shortest_distance",
  "transport_mode": "walk"
}
```

### 建议字段说明

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `site_id` | string | 当前景区或校园 ID |
| `start_node_id` | string | 起点节点 ID |
| `target_node_id` | string | 终点节点 ID |
| `strategy` | string | 距离或时间策略 |
| `transport_mode` | string | 交通方式，如步行、自行车、电瓶车 |

### 建议输出

```json
{
  "success": true,
  "distance": 386.5,
  "estimated_time": 420,
  "path_nodes": ["node_105", "node_107", "node_120", "node_233"],
  "strategy": "shortest_distance",
  "transport_mode": "walk"
}
```

### 成员 B 需要重点确认的问题

- 返回的 `distance` 单位是米还是千米
- `estimated_time` 单位是秒还是分钟
- 当路径不可达时返回什么
- 不同交通方式是否统一走同一个接口

---

## 3.2 多目标路径结果接口

### 用途

当前成员 B 不是主负责多目标路径，但后续可能用于：

- 推荐若干景点后，调用多点路径规划做扩展展示

### 建议输入

```json
{
  "site_id": "campus_001",
  "start_node_id": "node_105",
  "target_node_ids": ["node_233", "node_450", "node_512"],
  "strategy": "shortest_time",
  "transport_mode": "mixed"
}
```

### 建议输出

```json
{
  "success": true,
  "total_distance": 1820.3,
  "total_time": 1560,
  "visit_order": ["node_233", "node_450", "node_512"],
  "path_nodes": ["node_105", "node_120", "node_233", "node_300", "node_450", "node_512", "node_105"]
}
```

### 对成员 B 的意义

这部分目前主要是预留接口，不是本周首要实现目标，但建议格式先统一，避免后面扩展时推翻已有设计。

---

## 4. 成员 B 与成员 C 的接口约定

成员 C 负责数据、全文检索和测试支持，因此成员 B 最需要先确认的是“数据字段”和“检索结果格式”。

## 4.1 景点 / 学校 / 设施 / 美食基础数据

### 建议统一字段

不同对象可以字段不完全一样，但建议保留统一核心字段，方便成员 B 写通用查询和排序逻辑。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 唯一标识 |
| `name` | string | 名称 |
| `category` | string | 类别 |
| `site_id` | string | 所属景区或校园 |
| `node_id` | string | 对应图节点 ID |
| `heat` | number | 热度 |
| `rating` | number | 评分 |
| `tags` | array | 标签 |
| `keywords` | array | 关键字 |
| `description` | string | 描述信息 |

### 美食对象建议附加字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `cuisine` | string | 菜系 |
| `restaurant_name` | string | 所属餐厅或窗口名称 |
| `price_level` | string/number | 价格级别 |

### 成员 B 需要重点确认的问题

- `tags` 和 `keywords` 是数组还是字符串
- `heat`、`rating` 是否保证存在
- `node_id` 是否一定对应图中的有效节点
- 景点、设施、美食是否都放在同一个 `site_id` 体系下

---

## 4.2 日记数据接口

### 用途

用于：

- 按目的地查询日记
- 按标题精确查询日记
- 按热度、评分、兴趣推荐日记

### 建议字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 日记 ID |
| `title` | string | 日记标题 |
| `destination` | string | 目的地名称 |
| `author_id` | string | 作者 ID |
| `content` | string | 正文内容 |
| `heat` | number | 浏览量或热度 |
| `rating` | number | 平均评分 |
| `tags` | array | 内容标签 |
| `created_at` | string | 发布时间 |

### 成员 B 需要重点确认的问题

- 标题是否允许重复
- `destination` 是否统一命名
- `heat` 是原始浏览量还是做过归一化
- `tags` 是否已由成员 C 预处理

---

## 4.3 全文检索结果接口

这部分由成员 C 负责检索算法，成员 B 负责业务结果组织。

### 建议输入

```json
{
  "query": "西湖 夜景 美食"
}
```

### 建议输出

```json
{
  "success": true,
  "query": "西湖 夜景 美食",
  "results": [
    {
      "diary_id": "diary_101",
      "title": "西湖夜游记录",
      "matched_terms": ["西湖", "夜景", "美食"],
      "score": 0.93
    }
  ]
}
```

### 成员 B 拿到后需要做什么

- 根据 `diary_id` 找到完整日记信息
- 统一封装返回格式
- 必要时结合热度、评分做二次排序

### 成员 B 需要重点确认的问题

- `score` 的范围和含义是什么
- 全文检索是否已经去重
- 检索结果是否按相关性排好序

---

## 5. 成员 B 自己建议提供的统一业务接口

为了减少后续入口混乱，成员 B 自己也建议统一对外接口风格。

## 5.1 通用查询接口返回格式

```json
{
  "success": true,
  "message": "query success",
  "query_type": "scenic_search",
  "sort_by": "rating",
  "filters": {
    "category": "museum"
  },
  "total": 2,
  "items": [
    {
      "id": "spot_001",
      "name": "校史馆",
      "category": "museum",
      "heat": 95,
      "rating": 4.8
    }
  ]
}
```

## 5.2 通用错误返回格式

```json
{
  "success": false,
  "message": "invalid sort field",
  "error_code": "INVALID_SORT_FIELD"
}
```

这样做的好处是：

- 前端或命令行更容易接
- 查询、推荐、日记三个业务的返回结构统一
- 便于后续测试

---

## 6. 本周最需要尽快确认的 6 个问题

为了不影响下周编码，建议成员 B 尽快和另外两位成员确认下面 6 个问题。

### 和成员 A 确认

1. 距离接口是按 `node_id` 还是按坐标输入
2. 距离和时间是否统一通过一个接口返回
3. 路径不可达时的错误返回格式是什么

### 和成员 C 确认

4. 基础数据是否统一使用 `id / name / category / site_id / node_id / heat / rating`
5. 日记数据是否已经包含 `title / destination / heat / rating / content`
6. 全文检索结果是否至少返回 `diary_id / title / score`

---

## 7. 结论

成员 B 的开发效率，很大程度上取决于接口是否提前约定清楚。

只要本周把下面三件事确认下来，后面开发就会顺很多：

1. 成员 A 的真实距离接口格式
2. 成员 C 的基础数据字段格式
3. 全文检索结果如何交给成员 B 做统一展示

这样成员 B 就可以先独立写：

- 查询模块
- 排序模块
- Top-K 模块
- 推荐模块
- 日记结果组织模块

等成员 A、成员 C 的模块就位后，再快速联调。
