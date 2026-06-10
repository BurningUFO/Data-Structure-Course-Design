"""Zero-dependency local web server for Member B's minimal demonstrable UI."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.ui.demo_service import DemoUIService


STATIC_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/app.js": "app.js",
    "/styles.css": "styles.css",
}

LOCAL_ENV_FILES = (
    ".env.local",
    ".env.aigc.local",
)
GENERATED_STATIC_ROOT_ENV = "DEMO_UI_GENERATED_STATIC_ROOT"
TILE_CACHE_DIR_ENV = "DEMO_UI_TILE_CACHE_DIR"
TILE_CACHE_MAX_AGE_S = 7 * 24 * 60 * 60
TILE_USER_AGENT = "IntelligentCampusGuide/1.0 (course-design desktop demo; contact: local-user)"
TILE_PROXY_SOURCES = {
    "osm": {
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "OpenStreetMap contributors",
        "max_zoom": 19,
    },
    "carto_light": {
        "url": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "subdomains": "abcd",
        "attribution": "OpenStreetMap contributors; CARTO",
        "max_zoom": 20,
    },
}


def load_local_env_files(root_dir: Path | None = None) -> list[Path]:
    """Load untracked local KEY=VALUE files before the demo service starts."""
    repo_root = root_dir or Path(__file__).resolve().parents[2]
    loaded: list[Path] = []
    for file_name in LOCAL_ENV_FILES:
        env_path = repo_root / file_name
        if not env_path.is_file():
            continue
        _load_env_file(env_path)
        loaded.append(env_path)
    return loaded


def _load_env_file(env_path: Path) -> None:
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _resolve_generated_static_root(static_root: Path) -> Path:
    configured_root = os.environ.get(GENERATED_STATIC_ROOT_ENV, "").strip()
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return (static_root / "generated").resolve()


def _resolve_tile_cache_dir() -> Path:
    configured_root = os.environ.get(TILE_CACHE_DIR_ENV, "").strip()
    if configured_root:
        return Path(configured_root).expanduser().resolve()

    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "IntelligentCampusGuide" / "tile_cache"
    return Path.home() / ".cache" / "IntelligentCampusGuide" / "tile_cache"


def _parse_tile_proxy_path(path: str) -> tuple[str, int, int, int] | None:
    parts = path.removeprefix("/api/map/tile/").split("/")
    if len(parts) != 4:
        return None

    source_id, z_text, x_text, y_file = parts
    y_text = y_file.removesuffix(".png")
    if not source_id or y_text == y_file:
        return None
    try:
        z = int(z_text)
        x = int(x_text)
        y = int(y_text)
    except ValueError:
        return None

    max_tile = 2 ** z
    source = TILE_PROXY_SOURCES.get(source_id)
    max_zoom = int(source.get("max_zoom", 19)) if source else 19
    if z < 0 or z > max_zoom or x < 0 or y < 0 or x >= max_tile or y >= max_tile:
        return None
    return source_id, z, x, y


def _tile_cache_path(source_id: str, z: int, x: int, y: int) -> Path:
    return _resolve_tile_cache_dir() / source_id / str(z) / str(x) / f"{y}.png"


def _cached_tile_is_fresh(path: Path) -> bool:
    if not path.is_file():
        return False
    return time.time() - path.stat().st_mtime <= TILE_CACHE_MAX_AGE_S


def _source_tile_url(source_id: str, z: int, x: int, y: int) -> str:
    source = TILE_PROXY_SOURCES[source_id]
    subdomains = str(source.get("subdomains") or "")
    subdomain = subdomains[(x + y) % len(subdomains)] if subdomains else ""
    return str(source["url"]).format(s=subdomain, z=z, x=x, y=y)


def _fetch_tile_to_cache(source_id: str, z: int, x: int, y: int, cache_path: Path) -> bytes:
    url = _source_tile_url(source_id, z, x, y)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "image/avif,image/webp,image/apng,image/png,image/*,*/*;q=0.8",
            "User-Agent": TILE_USER_AGENT,
            "Referer": "http://127.0.0.1/",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = response.read()
    if not payload:
        raise OSError("empty tile response")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cache_path.with_suffix(".tmp")
    temporary_path.write_bytes(payload)
    os.replace(temporary_path, cache_path)
    return payload


def build_handler(
    service: DemoUIService,
    *,
    service_factory: Callable[[str], DemoUIService] | None = None,
    generated_static_root: str | Path | None = None,
) -> type[BaseHTTPRequestHandler]:
    static_root = Path(__file__).resolve().parent / "static"
    generated_root = (
        Path(generated_static_root).expanduser().resolve()
        if generated_static_root is not None
        else _resolve_generated_static_root(static_root)
    )
    service_cache: dict[str, DemoUIService] = {service.site_id: service}

    def resolve_service(site_id: object | None = None) -> DemoUIService:
        normalized_site_id = str(site_id or service.site_id).strip() or service.site_id
        if normalized_site_id not in service_cache:
            service_cache[normalized_site_id] = (
                service_factory(normalized_site_id)
                if service_factory is not None
                else DemoUIService(site_id=normalized_site_id)
            )
        return service_cache[normalized_site_id]

    class DemoRequestHandler(BaseHTTPRequestHandler):
        server_version = "MemberBDemoUI/1.0"

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/api/bootstrap":
                query = parse_qs(parsed.query)
                site_id = (query.get("site_id") or query.get("site") or [None])[0]
                try:
                    selected_service = resolve_service(site_id)
                except Exception as error:
                    self._write_json(
                        {
                            "success": False,
                            "message": f"{type(error).__name__}: {error}",
                        },
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                self._write_json(selected_service.get_bootstrap_payload())
                return

            if path == "/api/map/geojson":
                query = parse_qs(parsed.query)
                site_id = (query.get("site_id") or query.get("site") or [None])[0]
                try:
                    selected_service = resolve_service(site_id)
                except Exception as error:
                    self._write_json(
                        {
                            "success": False,
                            "message": f"{type(error).__name__}: {error}",
                        },
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                self._write_json(selected_service.get_map_geojson_payload())
                return

            if path == "/api/map/osm-layers":
                query = parse_qs(parsed.query)
                site_id = (query.get("site_id") or query.get("site") or [None])[0]
                try:
                    selected_service = resolve_service(site_id)
                except Exception as error:
                    self._write_json(
                        {
                            "success": False,
                            "message": f"{type(error).__name__}: {error}",
                        },
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                self._write_json(selected_service.get_osm_layers_payload())
                return

            if path == "/api/map/indoor":
                query = parse_qs(parsed.query)
                site_id = (query.get("site_id") or query.get("site") or [None])[0]
                building_id = (query.get("building_id") or [None])[0]
                floor_id = (query.get("floor") or query.get("floor_id") or [None])[0]
                if not str(building_id or "").strip():
                    self._write_json(
                        {
                            "success": False,
                            "message": "building_id is required",
                        },
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                try:
                    selected_service = resolve_service(site_id)
                except Exception as error:
                    self._write_json(
                        {
                            "success": False,
                            "message": f"{type(error).__name__}: {error}",
                        },
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                response = selected_service.get_indoor_map_payload(str(building_id or ""), floor_id)
                status = HTTPStatus.OK if response.get("success") else HTTPStatus.BAD_REQUEST
                self._write_json(response, status=status)
                return

            if path == "/api/health":
                query = parse_qs(parsed.query)
                site_id = (query.get("site_id") or query.get("site") or [None])[0]
                try:
                    selected_service = resolve_service(site_id)
                except Exception as error:
                    self._write_json(
                        {
                            "success": False,
                            "message": f"{type(error).__name__}: {error}",
                        },
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                self._write_json({"success": True, "site_id": selected_service.site_id})
                return

            if path.startswith("/api/map/tile/"):
                tile_request = _parse_tile_proxy_path(path)
                if tile_request is None:
                    self.send_error(HTTPStatus.NOT_FOUND, "Tile Not Found")
                    return

                source_id, z, x, y = tile_request
                if source_id not in TILE_PROXY_SOURCES:
                    self.send_error(HTTPStatus.NOT_FOUND, "Unknown tile source")
                    return

                cache_path = _tile_cache_path(source_id, z, x, y)
                try:
                    if _cached_tile_is_fresh(cache_path):
                        content = cache_path.read_bytes()
                    else:
                        content = _fetch_tile_to_cache(source_id, z, x, y, cache_path)
                except (OSError, urllib.error.URLError, urllib.error.HTTPError) as error:
                    print(f"[demo-ui] tile source failed: {source_id}/{z}/{x}/{y}: {error}")
                    self.send_error(HTTPStatus.BAD_GATEWAY, "Tile source unavailable")
                    return

                self._write_bytes(
                    content,
                    content_type="image/png",
                    status=HTTPStatus.OK,
                )
                return

            file_name = STATIC_FILES.get(path)
            if file_name is not None:
                file_path = static_root / file_name
            elif path.startswith("/assets/"):
                asset_name = path.removeprefix("/assets/")
                file_path = (static_root / "assets" / asset_name).resolve()
                asset_root = (static_root / "assets").resolve()
                if asset_root not in file_path.parents and file_path != asset_root:
                    self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                    return
            elif path.startswith("/vendor/"):
                vendor_name = path.removeprefix("/vendor/")
                file_path = (static_root / "vendor" / vendor_name).resolve()
                vendor_root = (static_root / "vendor").resolve()
                if vendor_root not in file_path.parents and file_path != vendor_root:
                    self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                    return
            elif path.startswith("/generated/"):
                generated_name = path.removeprefix("/generated/")
                file_path = (generated_root / generated_name).resolve()
                if generated_root not in file_path.parents and file_path != generated_root:
                    self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                    return
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                return

            if not file_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "Static file missing")
                return

            content = file_path.read_bytes()
            content_type, _ = mimetypes.guess_type(file_path.name)
            self._write_bytes(
                content,
                content_type=content_type or "application/octet-stream",
            )

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            body = self._read_json_body()
            if body is None:
                return

            try:
                selected_service = resolve_service(body.get("site_id"))
            except Exception as error:
                self._write_json(
                    {
                        "success": False,
                        "message": f"{type(error).__name__}: {error}",
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            routes: dict[str, Callable[[dict[str, object]], dict[str, object]]] = {
                "/api/search/scenic": selected_service.scenic_search,
                "/api/search/places": selected_service.place_search,
                "/api/recommend/catering": selected_service.catering_search,
                "/api/diaries/list": selected_service.diary_list,
                "/api/diaries/recommend": selected_service.diary_list,
                "/api/diaries/fulltext": selected_service.diary_fulltext_search,
                "/api/diaries": selected_service.create_diary,
                "/api/diaries/create": selected_service.create_diary,
                "/api/diaries/update": selected_service.update_diary,
                "/api/diaries/delete": selected_service.delete_diary,
                "/api/diaries/view": selected_service.view_diary,
                "/api/diaries/rate": selected_service.rate_diary,
                "/api/diaries/compress": selected_service.diary_compress_preview,
                "/api/aigc/preview": selected_service.aigc_preview,
                "/api/route": selected_service.plan_route,
                "/api/route/multi": selected_service.plan_multi_route,
            }

            handler = routes.get(parsed.path)
            if handler is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                return

            try:
                response = handler(body)
            except Exception as error:  # pragma: no cover - server safety net
                self._write_json(
                    {
                        "success": False,
                        "message": f"{type(error).__name__}: {error}",
                    },
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return

            self._write_json(response)

        def _read_json_body(self) -> dict[str, object] | None:
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                content_length = 0

            raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            try:
                decoded = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                self._write_json(
                    {"success": False, "message": "invalid json body"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return None

            return decoded if isinstance(decoded, dict) else {}

        def _write_json(
            self,
            payload: dict[str, object],
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._write_bytes(content, content_type="application/json; charset=utf-8", status=status)

        def _write_bytes(
            self,
            payload: bytes,
            *,
            content_type: str,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            print(f"[demo-ui] {self.address_string()} - {format % args}")

    return DemoRequestHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Member B minimal demo UI")
    parser.add_argument("--host", default="127.0.0.1", help="listen host")
    parser.add_argument("--port", default=8765, type=int, help="listen port")
    parser.add_argument("--site", default=None, help="site id, default uses global_sites.json")
    args = parser.parse_args()

    loaded_env_files = load_local_env_files()
    service = DemoUIService(site_id=args.site)
    handler_class = build_handler(service)
    server = ThreadingHTTPServer((args.host, args.port), handler_class)

    print(f"Member B minimal demo UI running at http://{args.host}:{args.port}")
    print(f"Site: {service.site_meta['name']} ({service.site_id})")
    if loaded_env_files:
        names = ", ".join(path.name for path in loaded_env_files)
        print(f"Loaded local env file(s): {names}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping demo UI server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
