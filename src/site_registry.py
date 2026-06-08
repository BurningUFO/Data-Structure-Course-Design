"""Shared helpers for resolving registered campus site data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SiteRecord = dict[str, Any]


def normalize_site_id(site_id: str | None) -> str:
    """Return a stable display site id."""
    return str(site_id or "").strip()


def resolve_data_root(data_root: str | Path | None = None) -> Path:
    """Resolve the repository data directory."""
    if data_root is not None:
        return Path(data_root)
    return Path(__file__).resolve().parents[1] / "data"


def get_global_sites_path(data_root: str | Path | None = None) -> Path:
    """Return the global site registry path."""
    return resolve_data_root(data_root) / "global_sites.json"


def load_global_sites(data_root: str | Path | None = None) -> list[SiteRecord]:
    """Load registered site records from data/global_sites.json."""
    path = get_global_sites_path(data_root)
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    sites = data.get("sites", [])
    return [site for site in sites if isinstance(site, dict)] if isinstance(sites, list) else []


def find_site_entry(
    site_id: str | None,
    data_root: str | Path | None = None,
) -> SiteRecord | None:
    """Find a registered site by id, case-insensitively."""
    normalized_site_id = normalize_site_id(site_id)
    if not normalized_site_id:
        return None

    normalized_lookup = normalized_site_id.upper()
    for site in load_global_sites(data_root):
        if normalize_site_id(site.get("id")).upper() == normalized_lookup:
            return site
    return None


def resolve_site_template_id(
    site_id: str | None,
    data_root: str | Path | None = None,
) -> str:
    """Return the template site id for alias/template-clone sites."""
    site = find_site_entry(site_id, data_root)
    if not site:
        return ""
    return normalize_site_id(site.get("template_site_id"))


def resolve_site_data_id(
    site_id: str | None,
    data_root: str | Path | None = None,
) -> str:
    """Return the physical site id whose graph files should be read."""
    requested_site_id = normalize_site_id(site_id)
    return resolve_site_template_id(requested_site_id, data_root) or requested_site_id


def resolve_site_subgraphs(
    site_id: str | None,
    data_root: str | Path | None = None,
) -> list[str]:
    """Return subgraph file stems for a display site or its template."""
    site = find_site_entry(site_id, data_root)
    if site:
        sub_graphs = [
            normalize_site_id(name)
            for name in site.get("sub_graphs", [])
            if normalize_site_id(name)
        ]
        if sub_graphs:
            return sub_graphs

    template_site_id = resolve_site_template_id(site_id, data_root)
    if template_site_id:
        template_site = find_site_entry(template_site_id, data_root)
        if template_site:
            return [
                normalize_site_id(name)
                for name in template_site.get("sub_graphs", [])
                if normalize_site_id(name)
            ]

    return []


def resolve_site_data_dir(
    site_id: str | None,
    data_root: str | Path | None = None,
) -> Path:
    """Return the physical data/sites/{site_id} directory for a site."""
    return resolve_data_root(data_root) / "sites" / resolve_site_data_id(site_id, data_root)


def site_uses_template_clone(
    site_id: str | None,
    data_root: str | Path | None = None,
) -> bool:
    """Return whether a display site is backed by another site's data."""
    site = find_site_entry(site_id, data_root)
    if not site:
        return False

    return bool(
        normalize_site_id(site.get("template_site_id"))
        or normalize_site_id(site.get("map_profile")) == "template_clone"
        or normalize_site_id(site.get("data_status")) == "template_clone_available"
    )


def resolve_site_display_overrides(
    site_id: str | None,
    data_root: str | Path | None = None,
) -> SiteRecord:
    """Return display-only overrides for template-clone sites."""
    site = find_site_entry(site_id, data_root)
    if not site:
        return {}

    overrides = site.get("display_overrides")
    return overrides if isinstance(overrides, dict) else {}


def resolve_site_node_name_overrides(
    site_id: str | None,
    data_root: str | Path | None = None,
) -> dict[str, str]:
    """Return node_id -> display name overrides for a site."""
    overrides = resolve_site_display_overrides(site_id, data_root)
    node_names = overrides.get("node_names")
    if not isinstance(node_names, dict):
        return {}

    return {
        normalize_site_id(node_id): str(display_name).strip()
        for node_id, display_name in node_names.items()
        if normalize_site_id(node_id) and str(display_name).strip()
    }


def resolve_site_user_name_overrides(
    site_id: str | None,
    data_root: str | Path | None = None,
) -> dict[str, str]:
    """Return user_id -> display name overrides for a site."""
    overrides = resolve_site_display_overrides(site_id, data_root)
    user_names = overrides.get("user_names")
    if not isinstance(user_names, dict):
        return {}

    return {
        normalize_site_id(user_id): str(display_name).strip()
        for user_id, display_name in user_names.items()
        if normalize_site_id(user_id) and str(display_name).strip()
    }


def resolve_site_text_replacements(
    site_id: str | None,
    data_root: str | Path | None = None,
) -> list[tuple[str, str]]:
    """Return ordered text replacements for display-only template names."""
    overrides = resolve_site_display_overrides(site_id, data_root)
    replacements = overrides.get("text_replacements")
    items: list[tuple[str, str]] = []

    if isinstance(replacements, dict):
        items = [
            (str(source).strip(), str(target).strip())
            for source, target in replacements.items()
            if str(source).strip()
        ]
    elif isinstance(replacements, list):
        for item in replacements:
            if not isinstance(item, dict):
                continue
            source = str(item.get("from", "")).strip()
            if source:
                items.append((source, str(item.get("to", "")).strip()))

    return sorted(items, key=lambda pair: len(pair[0]), reverse=True)


def apply_site_text_replacements(
    site_id: str | None,
    value: Any,
    data_root: str | Path | None = None,
) -> str:
    """Apply display-only string replacements for a site."""
    if value is None:
        return ""

    text = str(value)
    for source, target in resolve_site_text_replacements(site_id, data_root):
        text = text.replace(source, target)
    return text.strip()


def resolve_site_node_display_name(
    site_id: str | None,
    node_id: str | None,
    fallback_name: Any = "",
    data_root: str | Path | None = None,
) -> str:
    """Return the display name for a node without changing its stable id."""
    normalized_node_id = normalize_site_id(node_id)
    node_names = resolve_site_node_name_overrides(site_id, data_root)
    if normalized_node_id in node_names:
        return node_names[normalized_node_id]

    fallback = normalize_site_id(fallback_name) or normalized_node_id
    return apply_site_text_replacements(site_id, fallback, data_root)
