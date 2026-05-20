from pathlib import Path


EXTENSION_SITE_IDS = [
    "THU",
    "WHU",
    "XMU",
    "ZJU",
    "NJU",
    "FDU",
    "SJTU",
    "TONGJI",
    "SEU",
    "SYSU",
    "SCU",
    "HNU",
    "SDU",
    "HUST",
    "SCUT",
    "OUC",
    "SUDA",
    "HIT",
    "YNU",
    "HZAU",
]


M32C_DOC = Path("docs/地图方案B_M32C_课程答辩材料与扩站说明.md")
M32_REPORT = Path("docs/地图方案B_M32_多校园总验收收口报告.md")
FINAL_DELIVERY = Path("docs/地图方案B最终交付说明.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_m32c_defense_materials_cover_all_extension_sites():
    text = _read(M32C_DOC)

    assert "M32C" in text
    assert "PKU` 基线站点 + 20 个扩展校园" in text
    assert "py -m pytest -q" in text
    assert "未调用 OSMnx、Overpass、web search" in text
    for site_id in EXTENSION_SITE_IDS:
        assert f"`{site_id}`" in text


def test_m32_delivery_index_links_regression_materials():
    report = _read(M32_REPORT)
    final_delivery = _read(FINAL_DELIVERY)
    combined = report + final_delivery

    required_paths = [
        "docs/地图方案B_M31D_20校推荐附近交通总回归.md",
        "docs/地图方案B_M32A_API回归测试清单.md",
        "docs/地图方案B_M32B_UI冒烟与演示路径清单.md",
        "docs/M32B_UI_smoke_screenshots_demo_routes_report.md",
        "docs/地图方案B_M32C_课程答辩材料与扩站说明.md",
        "tests/test_m31d_regression.py",
        "tests/test_m32a_api_regression.py",
        "tests/test_m32b_ui_smoke.py",
    ]
    for path in required_paths:
        assert path in combined

    assert "可用站点 | 21" in report
    assert "扩展校园室外 GeoJSON 节点 | 752" in report
    assert "扩展校园室外 GeoJSON 边 | 827" in report
    assert "py -m src.ui.demo_server" in combined
    assert "http://127.0.0.1:8765" in combined

