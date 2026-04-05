1. 高德地图开放平台 (推荐用于获取实时 POI 数据)
这是获取景点名称、经纬度、分类及周边设施最稳定、最标准的方式。

官方地址：https://lbs.amap.com/

核心功能：搜索 POI（Point of Interest，兴趣点）。

具体操作步骤：

注册与认证：注册高德账号并完成“个人开发者”认证。

创建应用：进入“控制台” -> “应用管理” -> “我创建的应用”，点击“创建新应用”。

获取 Key：在应用下点击“添加”，名称随意，类型选择 “Web 服务”（这个类型支持 HTTP 接口请求，最适合爬取数据），提交后即可获得一串 API Key。

接口调用：使用 Python 的 requests 库发送请求。

示例 URL：https://restapi.amap.com/v3/place/text?keywords=景点名称&city=北京&key=你的Key&types=风景名胜

数据清洗：高德返回的是标准 JSON 格式。你需要提取 name（景点名）、location（经纬度）、type（分类）和 address（地址）。

已作废2. Kaggle 公开数据集 (推荐用于获取大量静态数据)
适合用于初始化数据库，不需要写代码调用 API，直接下载 CSV 文件。

具体资源地址：

中国城市景点详情：China City Attraction Details

通用旅游数据集：Tourism Dataset

操作方式：

访问上述链接，点击 "Download"（需登录，支持 GitHub/Google 账号）。

下载后解压得到 .csv 文件。

处理逻辑：使用 Python 的 pandas 库读取：

Python
import pandas as pd
df = pd.read_csv('attractions.csv')
# 筛选出你需要的列，转存为成员A/B需要的JSON格式
3. 百度地图 API (推荐用于搜索景点详情)
百度地图的 POI 检索功能非常细致，支持城市内检索和周边检索。

官方地址：https://lbsyun.baidu.com/

操作方式：

控制台申请：同高德类似，创建应用并勾选 “地点检索” 权限。

关键参数：使用 searchInCity 接口，必填 city（城市）和 keyword（关键词，如“景点”或“美食”）。

特色数据：百度 API 常能返回景点的 评分 (rating) 和 营业时间，这对成员 B 实现“推荐排序”非常有价值。