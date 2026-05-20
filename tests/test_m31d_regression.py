import json
from pathlib import Path

from src.ui.demo_service import DemoUIService


M31D_SITE_IDS = [
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

ROUTE_TARGET_PRIORITY = [
    "sports_ground",
    "gymnasium",
    "sports_center",
    "library",
]


def _outdoor_payload(site_id):
    return json.loads(Path(f"data/sites/{site_id}/outdoor.json").read_text(encoding="utf-8"))


def _route_target_for(service):
    for node_id in ROUTE_TARGET_PRIORITY:
        if node_id in service.graph.nodes:
            return node_id
    raise AssertionError(f"missing route target in {service.site_id}")


def test_m31d_twenty_campus_transport_nearby_interest_regression():
    assert len(M31D_SITE_IDS) == 20

    for site_id in M31D_SITE_IDS:
        service = DemoUIService(site_id)
        bootstrap = service.get_bootstrap_payload()
        outdoor = _outdoor_payload(site_id)
        metadata = outdoor["metadata"]

        assert bootstrap["site"]["id"] == site_id
        assert bootstrap["site"]["is_available"] is True
        assert [item["value"] for item in bootstrap["controls"]["transport_modes"]] == [
            "walk",
            "bike",
            "mixed",
        ]
        assert metadata["nearby_calibration_stage"] == f"M31B_{site_id}"
        assert metadata["interest_calibration_stage"] == f"M31C_{site_id}"
        assert len(metadata["interest_highlights"]) >= 3

        route_target = _route_target_for(service)
        route_request = {
            "start_node_id": "gate_south",
            "target_node_id": route_target,
            "strategy": "shortest_time",
        }
        walk_route = service.plan_route({**route_request, "transport_mode": "walk"})
        mixed_route = service.plan_route({**route_request, "transport_mode": "mixed"})

        assert walk_route["success"] is True
        assert mixed_route["success"] is True
        assert mixed_route["site_id"] == site_id
        assert mixed_route["summary"]["transport_text"] == "步行 + 自行车最短时间"
        assert mixed_route["summary"]["strategy_text"] == "最短时间"
        assert mixed_route["ui"]["route_geojson"] is not None
        assert {"walk", "bike"} <= {
            step["transport_mode_used"] for step in mixed_route["path_steps"]
        }

        nearby_profiles = bootstrap["controls"]["nearby_profiles"]
        assert len(nearby_profiles) >= 6
        first_profile = next(iter(nearby_profiles.values()))
        nearby_response = service.place_search(
            {
                "center_node_id": first_profile["center_node_id"],
                "category": first_profile["default_category"],
                "radius_m": first_profile["default_radius_m"],
                "sort_field": "distance_m",
                "limit": 5,
            }
        )
        nearby_metadata = nearby_response["metadata"]["nearby"]

        assert nearby_response["success"] is True
        assert nearby_response["results"]
        assert nearby_metadata["calibration_stage"] == f"M31B_{site_id}"
        assert nearby_metadata["calibration_profile"]["center_node_id"] == first_profile["center_node_id"]
        assert all(item["site_id"] == site_id for item in nearby_response["results"])
        assert all(
            item["nearby_center_node_id"] == first_profile["center_node_id"]
            for item in nearby_response["results"]
        )
        assert all(first_profile["center_name"] in item["nearby_reason"] for item in nearby_response["results"])

        default_user = bootstrap["users"][0]
        interest_response = service.scenic_search(
            {
                "sort_field": "interest",
                "user_id": default_user["id"],
                "limit": 5,
            }
        )
        interest_context = interest_response["metadata"]["user_interest_context"]

        assert default_user["home_site_id"] == site_id
        assert interest_response["success"] is True
        assert interest_response["results"]
        assert interest_context["user_id"] == default_user["id"]
        assert interest_context["source"] == "user_profile"
        assert interest_context["interests"] == default_user["interests"]
        assert all(item["site_id"] == site_id for item in interest_response["results"])
