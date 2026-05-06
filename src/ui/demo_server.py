"""Zero-dependency local web server for Member B's minimal demonstrable UI."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.ui.demo_service import DemoUIService


STATIC_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/app.js": "app.js",
    "/styles.css": "styles.css",
}


def build_handler(service: DemoUIService) -> type[BaseHTTPRequestHandler]:
    static_root = Path(__file__).resolve().parent / "static"

    class DemoRequestHandler(BaseHTTPRequestHandler):
        server_version = "MemberBDemoUI/1.0"

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/api/bootstrap":
                self._write_json(service.get_bootstrap_payload())
                return

            if path == "/api/health":
                self._write_json({"success": True, "site_id": service.site_id})
                return

            file_name = STATIC_FILES.get(path)
            if file_name is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                return

            file_path = static_root / file_name
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

            routes: dict[str, Callable[[dict[str, object]], dict[str, object]]] = {
                "/api/search/scenic": service.scenic_search,
                "/api/search/places": service.place_search,
                "/api/recommend/catering": service.catering_search,
                "/api/diaries/fulltext": service.diary_fulltext_search,
                "/api/route": service.plan_route,
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

    service = DemoUIService(site_id=args.site)
    handler_class = build_handler(service)
    server = ThreadingHTTPServer((args.host, args.port), handler_class)

    print(f"Member B minimal demo UI running at http://{args.host}:{args.port}")
    print(f"Site: {service.site_meta['name']} ({service.site_id})")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping demo UI server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

