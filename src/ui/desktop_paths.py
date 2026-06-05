"""Runtime paths for the Windows desktop wrapper."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


APP_DIR_NAME = "IntelligentCampusGuide"
DIARY_DATA_FILE_NAME = "diary_data.json"


@dataclass(frozen=True)
class DesktopRuntimePaths:
    """Resolved writable and bundled paths used by the desktop app."""

    user_data_dir: Path
    diary_data_path: Path
    generated_static_root: Path


def get_bundle_root() -> Path:
    """Return the project root in development or PyInstaller bundle root."""

    meipass = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and meipass:
        return Path(meipass)
    return Path(__file__).resolve().parents[2]


def get_user_data_dir(
    *,
    app_name: str = APP_DIR_NAME,
    base_dir: str | Path | None = None,
) -> Path:
    """Return the per-user writable app directory."""

    if base_dir is not None:
        return Path(base_dir) / app_name

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / app_name

    if os.name == "nt":
        return Path.home() / "AppData" / "Local" / app_name
    return Path.home() / ".local" / "share" / app_name


def get_bundled_data_dir(bundle_root: str | Path | None = None) -> Path:
    """Return the read-only baseline data directory."""

    root = Path(bundle_root) if bundle_root is not None else get_bundle_root()
    return root / "data"


def ensure_user_diary_data_path(
    *,
    user_data_dir: str | Path | None = None,
    bundled_data_dir: str | Path | None = None,
) -> Path:
    """Copy the baseline diary data to the writable user directory once."""

    root = Path(user_data_dir) if user_data_dir is not None else get_user_data_dir()
    target_path = root / "data" / DIARY_DATA_FILE_NAME
    if target_path.exists():
        return target_path

    source_dir = Path(bundled_data_dir) if bundled_data_dir is not None else get_bundled_data_dir()
    source_path = source_dir / DIARY_DATA_FILE_NAME
    if not source_path.is_file():
        raise FileNotFoundError(f"Bundled diary data not found: {source_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return target_path


def get_generated_static_root(user_data_dir: str | Path | None = None) -> Path:
    """Return the writable root served through /generated in desktop mode."""

    root = Path(user_data_dir) if user_data_dir is not None else get_user_data_dir()
    return root / "static" / "generated"


def prepare_desktop_runtime(
    *,
    user_data_dir: str | Path | None = None,
    bundled_data_dir: str | Path | None = None,
) -> DesktopRuntimePaths:
    """Create required writable desktop directories and return their paths."""

    root = Path(user_data_dir) if user_data_dir is not None else get_user_data_dir()
    diary_path = ensure_user_diary_data_path(
        user_data_dir=root,
        bundled_data_dir=bundled_data_dir,
    )
    generated_root = get_generated_static_root(root)
    generated_root.mkdir(parents=True, exist_ok=True)
    return DesktopRuntimePaths(
        user_data_dir=root,
        diary_data_path=diary_path,
        generated_static_root=generated_root,
    )
