# M32B UI Smoke Screenshots and Demo Routes Report

## 1. Scope

- Stage: `M32B` multi-campus UI smoke, screenshots, representative buildings, and demo-route material.
- Date: 2026-05-20.
- Sites: 20 extension campuses. `M32A` was not repeated.
- Boundary: no new features, no core architecture changes, no OSMnx, no Overpass, no web search.
- Runtime: local `DemoUIService` + `demo_server`, driven by a real browser through Playwright CLI.
- Artifact directory: `output/playwright/m32b_ui_smoke/`.

## 2. UI Smoke Flow

1. Switch the site selector to the target `SITE_ID`.
2. Wait for the target-campus bootstrap hydrate and Leaflet map status refresh.
3. Run the main scenic/search query and verify result cards render.
4. Run place/nearby query centered on the library and verify result cards render.
5. Run catering recommendation and verify result cards render.
6. Plan the default-start to library route with `mixed + shortest_time`.
7. Enter the library indoor map, switch to the second floor, and verify indoor panel/floor controls.
8. Capture one browser screenshot for the campus.

## 3. Result

- Passed sites: `20/20`.
- Machine-readable result: `output/playwright/m32b_ui_smoke/m32b_ui_smoke_results.json`.
- Conclusion: all 20 campuses passed site switch, Leaflet map, main query, nearby query, catering recommendation, outdoor route, indoor entry, and floor-switch UI smoke checks.
- Note: the 20 extension campuses currently use compact/template campus data; 0% route geometry coverage in many screenshots is expected for this data stage and is not an M32B UI failure.

## 4. Campus Materials

| SITE_ID | Campus | Representative buildings | Fixed demo routes | Screenshot | UI smoke status |
| --- | --- | --- | --- | --- | --- |
| `THU` | 清华大学 · 北京市海淀区清华园 | 清华大学图书馆 · F1 / F2 / F3<br>第三教室楼 · F1 / F2 / F3<br>紫荆学生公寓 · F1 / F2 / F3<br>桃李园 · F1 / F2<br>中央主楼 · F1 / F2 / F3 | Single: 清华大学北区入口 · 校门 -> 清华大学图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 清华大学北区入口 · 校门 -> 清华大学图书馆 · 教学 / 学习 -> 桃李园 · 餐饮 (mixed + shortest_time)<br>Indoor: 清华大学图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/THU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：清华大学北区入口 -> 清华大学图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `WHU` | 武汉大学 · 湖北省武汉市武昌区珞珈山 | 武汉大学图书馆总馆 · F1 / F2 / F3<br>武汉大学法学院 · F1 / F2 / F3<br>桂园学生宿舍 · F1 / F2 / F3<br>桂园食堂 · F1 / F2<br>万林艺术博物馆 · F1 / F2 / F3 | Single: 武汉大学北侧湖滨入口 · 校门 -> 武汉大学图书馆总馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 武汉大学北侧湖滨入口 · 校门 -> 武汉大学图书馆总馆 · 教学 / 学习 -> 桂园食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 武汉大学图书馆总馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/WHU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：武汉大学北侧湖滨入口 -> 武汉大学图书馆总馆 · 0/5 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `XMU` | 厦门大学 · 福建省厦门市思明区思明南路422号 | 厦门大学图书馆 · F1 / F2 / F3<br>厦门大学南强二教学楼 · F1 / F2 / F3<br>厦门大学芙蓉学生公寓 · F1 / F2 / F3<br>厦门大学芙蓉餐厅 · F1 / F2<br>厦门大学上弦场 · F1 / F2 / F3 | Single: 厦门大学大南校门 · 校门 -> 厦门大学图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 厦门大学大南校门 · 校门 -> 厦门大学图书馆 · 教学 / 学习 -> 厦门大学芙蓉餐厅 · 餐饮 (mixed + shortest_time)<br>Indoor: 厦门大学图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/XMU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：厦门大学大南校门 -> 厦门大学图书馆 · 0/4 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `ZJU` | 浙江大学 · 浙江省杭州市西湖区余杭塘路866号 | 浙江大学紫金港图书信息中心 · F1 / F2 / F3<br>浙江大学紫金港东教学楼 · F1 / F2 / F3<br>浙江大学丹青学园 · F1 / F2 / F3<br>浙江大学紫金港临湖餐厅 · F1 / F2<br>浙江大学紫金港体育馆 · F1 / F2 / F3 | Single: 浙江大学紫金港校区北门 · 校门 -> 浙江大学紫金港图书信息中心 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 浙江大学紫金港校区北门 · 校门 -> 浙江大学紫金港图书信息中心 · 教学 / 学习 -> 浙江大学紫金港临湖餐厅 · 餐饮 (mixed + shortest_time)<br>Indoor: 浙江大学紫金港图书信息中心 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/ZJU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：浙江大学紫金港校区北门 -> 浙江大学紫金港图书信息中心 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `NJU` | 南京大学 · 江苏省南京市栖霞区仙林大道163号 | 南京大学杜厦图书馆 · F1 / F2 / F3<br>南京大学仙林教学楼 · F1 / F2 / F3<br>南京大学仙林学生宿舍一组团 · F1 / F2 / F3<br>南京大学仙林校区九食堂 · F1 / F2<br>南京大学方肇周体育馆 · F1 / F2 / F3 | Single: 南京大学仙林校区北门 · 校门 -> 南京大学杜厦图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 南京大学仙林校区北门 · 校门 -> 南京大学杜厦图书馆 · 教学 / 学习 -> 南京大学仙林校区九食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 南京大学杜厦图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/NJU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：南京大学仙林校区北门 -> 南京大学杜厦图书馆 · 0/4 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `FDU` | 复旦大学 · 上海市杨浦区邯郸路220号 | 复旦大学文科图书馆 · F1 / F2 / F3<br>复旦大学第三教学楼 · F1 / F2 / F3<br>复旦大学邯郸校区南区学生宿舍 · F1 / F2 / F3<br>复旦大学邯郸校区南区食堂 · F1 / F2<br>复旦大学邯郸校区体育馆 · F1 / F2 / F3 | Single: 复旦大学邯郸校区北门 · 校门 -> 复旦大学文科图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 复旦大学邯郸校区北门 · 校门 -> 复旦大学文科图书馆 · 教学 / 学习 -> 复旦大学邯郸校区南区食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 复旦大学文科图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/FDU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：复旦大学邯郸校区北门 -> 复旦大学文科图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `SJTU` | 上海交通大学 · 上海市闵行区东川路800号 | 上海交通大学闵行校区图书馆 · F1 / F2 / F3<br>上海交通大学东中院教学楼 · F1 / F2 / F3<br>上海交通大学闵行校区北区学生宿舍 · F1 / F2 / F3<br>上海交通大学闵行校区第一餐饮大楼 · F1 / F2<br>上海交通大学霍英东体育中心 · F1 / F2 / F3 | Single: 上海交通大学闵行校区北门 · 校门 -> 上海交通大学闵行校区图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 上海交通大学闵行校区北门 · 校门 -> 上海交通大学闵行校区图书馆 · 教学 / 学习 -> 上海交通大学闵行校区第一餐饮大楼 · 餐饮 (mixed + shortest_time)<br>Indoor: 上海交通大学闵行校区图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/SJTU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：上海交通大学闵行校区北门 -> 上海交通大学闵行校区图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `TONGJI` | 同济大学 · 上海市杨浦区四平路1239号 | 同济大学四平路校区图书馆 · F1 / F2 / F3<br>同济大学四平路校区教学楼 · F1 / F2 / F3<br>同济大学四平路校区西区学生宿舍 · F1 / F2 / F3<br>同济大学学苑食堂 · F1 / F2<br>同济大学体育馆 · F1 / F2 / F3 | Single: 同济大学四平路校区北门 · 校门 -> 同济大学四平路校区图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 同济大学四平路校区北门 · 校门 -> 同济大学四平路校区图书馆 · 教学 / 学习 -> 同济大学学苑食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 同济大学四平路校区图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/TONGJI_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：同济大学四平路校区北门 -> 同济大学四平路校区图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `SEU` | 东南大学 · 江苏省南京市江宁区东南大学路2号 | 东南大学李文正图书馆 · F1 / F2 / F3<br>东南大学九龙湖校区教学楼群 · F1 / F2 / F3<br>东南大学九龙湖校区桃园学生宿舍 · F1 / F2 / F3<br>东南大学九龙湖校区桃园食堂 · F1 / F2<br>东南大学九龙湖校区体育馆 · F1 / F2 / F3 | Single: 东南大学九龙湖校区北门 · 校门 -> 东南大学李文正图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 东南大学九龙湖校区北门 · 校门 -> 东南大学李文正图书馆 · 教学 / 学习 -> 东南大学九龙湖校区桃园食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 东南大学李文正图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/SEU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：东南大学九龙湖校区北门 -> 东南大学李文正图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `SYSU` | 中山大学 · 广东省广州市海珠区新港西路135号 | 中山大学广州校区南校园图书馆 · F1 / F2 / F3<br>中山大学第一教学楼 · F1 / F2 / F3<br>中山大学南校园西区学生宿舍 · F1 / F2 / F3<br>中山大学南校园西区食堂 · F1 / F2<br>中山大学南校园体育馆 · F1 / F2 / F3 | Single: 中山大学广州校区南校园北门 · 校门 -> 中山大学广州校区南校园图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 中山大学广州校区南校园北门 · 校门 -> 中山大学广州校区南校园图书馆 · 教学 / 学习 -> 中山大学南校园西区食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 中山大学广州校区南校园图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/SYSU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：中山大学广州校区南校园北门 -> 中山大学广州校区南校园图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `SCU` | 四川大学 · 四川省成都市武侯区一环路南一段24号 | 四川大学望江校区图书馆 · F1 / F2 / F3<br>四川大学望江校区基础教学楼 · F1 / F2 / F3<br>四川大学望江校区西区学生宿舍 · F1 / F2 / F3<br>四川大学望江校区学生食堂 · F1 / F2<br>四川大学望江校区体育馆 · F1 / F2 / F3 | Single: 四川大学望江校区北门 · 校门 -> 四川大学望江校区图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 四川大学望江校区北门 · 校门 -> 四川大学望江校区图书馆 · 教学 / 学习 -> 四川大学望江校区学生食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 四川大学望江校区图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/SCU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：四川大学望江校区北门 -> 四川大学望江校区图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `HNU` | 湖南大学 · 湖南省长沙市岳麓区麓山南路 | 湖南大学图书馆 · F1 / F2 / F3<br>湖南大学教学楼群 · F1 / F2 / F3<br>湖南大学天马学生公寓 · F1 / F2 / F3<br>湖南大学德智园学生食堂 · F1 / F2<br>湖南大学体育馆 · F1 / F2 / F3 | Single: 湖南大学岳麓山校区北门 · 校门 -> 湖南大学图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 湖南大学岳麓山校区北门 · 校门 -> 湖南大学图书馆 · 教学 / 学习 -> 湖南大学德智园学生食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 湖南大学图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/HNU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：湖南大学岳麓山校区北门 -> 湖南大学图书馆 · 0/4 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `SDU` | 山东大学 · 山东省济南市历城区山大南路27号 | 山东大学中心校区图书馆 · F1 / F2 / F3<br>山东大学中心校区教学楼群 · F1 / F2 / F3<br>山东大学中心校区学生公寓 · F1 / F2 / F3<br>山东大学中心校区学生食堂 · F1 / F2<br>山东大学中心校区体育馆 · F1 / F2 / F3 | Single: 山东大学中心校区北门 · 校门 -> 山东大学中心校区图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 山东大学中心校区北门 · 校门 -> 山东大学中心校区图书馆 · 教学 / 学习 -> 山东大学中心校区学生食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 山东大学中心校区图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/SDU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：山东大学中心校区北门 -> 山东大学中心校区图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `HUST` | 华中科技大学 · 湖北省武汉市洪山区珞喻路1037号 | 华中科技大学图书馆 · F1 / F2 / F3<br>华中科技大学东九教学楼 · F1 / F2 / F3<br>华中科技大学韵苑学生公寓 · F1 / F2 / F3<br>华中科技大学百景园食堂 · F1 / F2<br>华中科技大学体育馆 · F1 / F2 / F3 | Single: 华中科技大学主校区北门 · 校门 -> 华中科技大学图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 华中科技大学主校区北门 · 校门 -> 华中科技大学图书馆 · 教学 / 学习 -> 华中科技大学百景园食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 华中科技大学图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/HUST_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：华中科技大学主校区北门 -> 华中科技大学图书馆 · 0/4 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `SCUT` | 华南理工大学 · 广东省广州市天河区五山路381号 | 华南理工大学五山校区图书馆 · F1 / F2 / F3<br>华南理工大学五山校区教学楼群 · F1 / F2 / F3<br>华南理工大学五山校区学生宿舍区 · F1 / F2 / F3<br>华南理工大学五山校区学生食堂 · F1 / F2<br>华南理工大学五山校区体育馆 · F1 / F2 / F3 | Single: 华南理工大学五山校区北门 · 校门 -> 华南理工大学五山校区图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 华南理工大学五山校区北门 · 校门 -> 华南理工大学五山校区图书馆 · 教学 / 学习 -> 华南理工大学五山校区学生食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 华南理工大学五山校区图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/SCUT_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：华南理工大学五山校区北门 -> 华南理工大学五山校区图书馆 · 0/4 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `OUC` | 中国海洋大学 · 山东省青岛市崂山区松岭路238号 | 中国海洋大学崂山校区图书馆 · F1 / F2 / F3<br>中国海洋大学崂山校区教学楼群 · F1 / F2 / F3<br>中国海洋大学崂山校区学生宿舍区 · F1 / F2 / F3<br>中国海洋大学崂山校区学生食堂 · F1 / F2<br>中国海洋大学崂山校区体育馆 · F1 / F2 / F3 | Single: 中国海洋大学崂山校区北门 · 校门 -> 中国海洋大学崂山校区图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 中国海洋大学崂山校区北门 · 校门 -> 中国海洋大学崂山校区图书馆 · 教学 / 学习 -> 中国海洋大学崂山校区学生食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 中国海洋大学崂山校区图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/OUC_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：中国海洋大学崂山校区北门 -> 中国海洋大学崂山校区图书馆 · 0/6 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `SUDA` | 苏州大学 · 江苏省苏州市姑苏区干将东路333号 | 苏州大学天赐庄校区图书馆 · F1 / F2 / F3<br>苏州大学天赐庄校区教学楼群 · F1 / F2 / F3<br>苏州大学天赐庄校区学生宿舍区 · F1 / F2 / F3<br>苏州大学天赐庄校区学生食堂 · F1 / F2<br>苏州大学天赐庄校区体育馆 · F1 / F2 / F3 | Single: 苏州大学天赐庄校区北门 · 校门 -> 苏州大学天赐庄校区图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 苏州大学天赐庄校区北门 · 校门 -> 苏州大学天赐庄校区图书馆 · 教学 / 学习 -> 苏州大学天赐庄校区学生食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 苏州大学天赐庄校区图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/SUDA_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：苏州大学天赐庄校区北门 -> 苏州大学天赐庄校区图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `HIT` | 哈尔滨工业大学 · 黑龙江省哈尔滨市南岗区西大直街92号 | 哈尔滨工业大学一校区图书馆 · F1 / F2 / F3<br>哈尔滨工业大学正心楼与教学楼群 · F1 / F2 / F3<br>哈尔滨工业大学一校区学生宿舍区 · F1 / F2 / F3<br>哈尔滨工业大学一校区学生食堂 · F1 / F2<br>哈尔滨工业大学一校区体育馆 · F1 / F2 / F3 | Single: 哈尔滨工业大学一校区北门 · 校门 -> 哈尔滨工业大学一校区图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 哈尔滨工业大学一校区北门 · 校门 -> 哈尔滨工业大学一校区图书馆 · 教学 / 学习 -> 哈尔滨工业大学一校区学生食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 哈尔滨工业大学一校区图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/HIT_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：哈尔滨工业大学一校区北门 -> 哈尔滨工业大学一校区图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `YNU` | 云南大学 · 云南省昆明市呈贡区大学城东外环南路 | 云南大学呈贡校区图书馆 · F1 / F2 / F3<br>云南大学呈贡校区教学楼群 · F1 / F2 / F3<br>云南大学呈贡校区学生宿舍区 · F1 / F2 / F3<br>云南大学呈贡校区学生食堂 · F1 / F2<br>云南大学呈贡校区体育馆 · F1 / F2 / F3 | Single: 云南大学呈贡校区北门 · 校门 -> 云南大学呈贡校区图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 云南大学呈贡校区北门 · 校门 -> 云南大学呈贡校区图书馆 · 教学 / 学习 -> 云南大学呈贡校区学生食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 云南大学呈贡校区图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/YNU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：云南大学呈贡校区北门 -> 云南大学呈贡校区图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |
| `HZAU` | 华中农业大学 · 湖北省武汉市洪山区狮子山街1号 | 华中农业大学图书馆 · F1 / F2 / F3<br>华中农业大学教学楼群 · F1 / F2 / F3<br>华中农业大学学生宿舍区 · F1 / F2 / F3<br>华中农业大学博园食堂 · F1 / F2<br>华中农业大学体育馆 · F1 / F2 / F3 | Single: 华中农业大学狮子山校区北门 · 校门 -> 华中农业大学图书馆 · 教学 / 学习 (mixed + shortest_time)<br>Multi: 华中农业大学狮子山校区北门 · 校门 -> 华中农业大学图书馆 · 教学 / 学习 -> 华中农业大学博园食堂 · 餐饮 (mixed + shortest_time)<br>Indoor: 华中农业大学图书馆 · 2F · 5 个功能区 | `output/playwright/m32b_ui_smoke/HZAU_ui_smoke.png` | Leaflet 真实地图<br>6 条结果 · 综合查询<br>6 条结果 · 场所查询<br>6 条结果 · catering_recommend<br>已规划：华中农业大学狮子山校区北门 -> 华中农业大学图书馆 · 0/3 段真实线形<br>Floor buttons: 3 (1F / 2F / 3F) |

## 5. Screenshot Manifest

- `THU`: `output/playwright/m32b_ui_smoke/THU_ui_smoke.png`
- `WHU`: `output/playwright/m32b_ui_smoke/WHU_ui_smoke.png`
- `XMU`: `output/playwright/m32b_ui_smoke/XMU_ui_smoke.png`
- `ZJU`: `output/playwright/m32b_ui_smoke/ZJU_ui_smoke.png`
- `NJU`: `output/playwright/m32b_ui_smoke/NJU_ui_smoke.png`
- `FDU`: `output/playwright/m32b_ui_smoke/FDU_ui_smoke.png`
- `SJTU`: `output/playwright/m32b_ui_smoke/SJTU_ui_smoke.png`
- `TONGJI`: `output/playwright/m32b_ui_smoke/TONGJI_ui_smoke.png`
- `SEU`: `output/playwright/m32b_ui_smoke/SEU_ui_smoke.png`
- `SYSU`: `output/playwright/m32b_ui_smoke/SYSU_ui_smoke.png`
- `SCU`: `output/playwright/m32b_ui_smoke/SCU_ui_smoke.png`
- `HNU`: `output/playwright/m32b_ui_smoke/HNU_ui_smoke.png`
- `SDU`: `output/playwright/m32b_ui_smoke/SDU_ui_smoke.png`
- `HUST`: `output/playwright/m32b_ui_smoke/HUST_ui_smoke.png`
- `SCUT`: `output/playwright/m32b_ui_smoke/SCUT_ui_smoke.png`
- `OUC`: `output/playwright/m32b_ui_smoke/OUC_ui_smoke.png`
- `SUDA`: `output/playwright/m32b_ui_smoke/SUDA_ui_smoke.png`
- `HIT`: `output/playwright/m32b_ui_smoke/HIT_ui_smoke.png`
- `YNU`: `output/playwright/m32b_ui_smoke/YNU_ui_smoke.png`
- `HZAU`: `output/playwright/m32b_ui_smoke/HZAU_ui_smoke.png`

## 6. Verification Commands

- `git status --short --branch`: run before changes; branch confirmed as `experiment/map-plan-b`.
- `git branch --show-current`: run before changes; output was `experiment/map-plan-b`.
- `netstat -ano | findstr :8765`: run before browser screenshots; no output, so port 8765 was not hit.
- `where.exe npx`: confirmed local `npx` availability.
- `npx --yes --package @playwright/cli playwright-cli --help`: confirmed Playwright CLI availability.
- `py output/playwright/m32b_ui_smoke/_capture_m32b_ui_smoke.py`: temporary capture script executed the real-browser UI smoke flow and generated screenshots; the script was deleted after use.

## 7. Temporary Files and Boundaries

- Temporary capture script, browser helper, and `__pycache__` were deleted after capture.
- Final retained artifacts are screenshots, `m32b_ui_smoke_results.json`, and this report.
- No new sub-agent or fourth-level delegation was used.
- No `git add`, `git commit`, `git reset`, `git checkout`, `git restore`, or `git revert` was run.
- No core runtime, API, or frontend feature code was modified.
