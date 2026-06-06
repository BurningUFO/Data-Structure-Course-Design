"""Windows desktop launcher for the demo UI."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Sequence

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.ui.demo_server import build_handler, load_local_env_files
from src.ui.demo_service import DemoUIService
from src.ui.desktop_paths import DesktopRuntimePaths, prepare_desktop_runtime


GENERATED_STATIC_ROOT_ENV = "DEMO_UI_GENERATED_STATIC_ROOT"
WINDOW_TITLE = "智能校园导览系统"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the campus guide desktop app")
    parser.add_argument("--site", default=None, help="site id, default uses global_sites.json")
    parser.add_argument("--debug", action="store_true", help="enable pywebview debug mode")
    parser.add_argument("--smoke", action="store_true", help="start the backend and verify /api/health without opening a window")
    return parser


def create_desktop_server(
    *,
    site_id: str | None = None,
    runtime_paths: DesktopRuntimePaths | None = None,
) -> tuple[DesktopRuntimePaths, DemoUIService, ThreadingHTTPServer, str]:
    """Create the local HTTP server used by the desktop window."""

    runtime = runtime_paths or prepare_desktop_runtime()
    os.environ[GENERATED_STATIC_ROOT_ENV] = str(runtime.generated_static_root)

    load_local_env_files()
    load_local_env_files(runtime.user_data_dir)

    def service_factory(selected_site_id: str) -> DemoUIService:
        return DemoUIService(
            site_id=selected_site_id,
            diary_data_path=runtime.diary_data_path,
        )

    service = DemoUIService(site_id=site_id, diary_data_path=runtime.diary_data_path)
    handler_class = build_handler(
        service,
        service_factory=service_factory,
        generated_static_root=runtime.generated_static_root,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    return runtime, service, server, base_url


def start_server_thread(server: ThreadingHTTPServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, name="desktop-demo-ui-server", daemon=True)
    thread.start()
    return thread


def stop_server(server: ThreadingHTTPServer, stopped: threading.Event) -> None:
    if stopped.is_set():
        return
    stopped.set()
    server.shutdown()
    server.server_close()


def run_smoke(
    *,
    site_id: str | None = None,
    runtime_paths: DesktopRuntimePaths | None = None,
) -> int:
    runtime, service, server, base_url = create_desktop_server(
        site_id=site_id,
        runtime_paths=runtime_paths,
    )
    stopped = threading.Event()
    start_server_thread(server)
    try:
        health_url = f"{base_url}/api/health?site_id={service.site_id}"
        with urllib.request.urlopen(health_url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("success") is True and payload.get("site_id") == service.site_id:
            print(f"Desktop smoke OK: {health_url}")
            print(f"User data: {runtime.user_data_dir}")
            return 0
        print(f"Desktop smoke failed: unexpected payload {payload}", file=sys.stderr)
        return 1
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        print(f"Desktop smoke failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    finally:
        stop_server(server, stopped)


def show_windows_error(title: str, message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        print(f"{title}: {message}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.smoke:
        return run_smoke(site_id=args.site)

    try:
        runtime, service, server, base_url = create_desktop_server(site_id=args.site)
    except Exception as error:
        show_windows_error("Desktop startup failed", f"{type(error).__name__}: {error}")
        return 1

    stopped = threading.Event()
    start_server_thread(server)
    print(f"Desktop app running at {base_url}")
    print(f"Site: {service.site_meta['name']} ({service.site_id})")
    print(f"User data: {runtime.user_data_dir}")

    try:
        import webview
    except ImportError as error:
        stop_server(server, stopped)
        show_windows_error(
            "pywebview is not installed",
            "Please install desktop dependencies with: py -3 -m pip install -r requirements-desktop.txt",
        )
        return 1

    try:
        window = webview.create_window(
            WINDOW_TITLE,
            base_url,
            width=1280,
            height=840,
            min_size=(1000, 700),
        )
        try:
            window.events.closed += lambda: stop_server(server, stopped)
        except AttributeError:
            pass
        webview.start(gui="edgechromium", debug=args.debug)
        return 0
    except Exception as error:
        show_windows_error(
            "Desktop window failed",
            (
                f"{type(error).__name__}: {error}\n\n"
                "Please ensure Microsoft Edge WebView2 Runtime is installed."
            ),
        )
        return 1
    finally:
        stop_server(server, stopped)


if __name__ == "__main__":
    raise SystemExit(main())
