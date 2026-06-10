#!/usr/bin/env python3
"""Configure the local AIGC OpenAI key for the demo UI.

The demo server already loads `.env.aigc.local` from the repository root.
That file is ignored by git, so this script writes secrets there instead of
putting them in tracked source files.
"""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = REPO_ROOT / ".env.aigc.local"
DEFAULT_MODEL = "gpt-image-1"
MANAGED_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_IMAGE_MODEL",
    "OPENAI_BASE_URL",
    "OPENAI_IMAGE_API_URL",
    "OPENAI_IMAGE_TIMEOUT_S",
    "OPENAI_HTTP_TRANSPORT",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write local OpenAI settings used by the AIGC demo.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help="target env file, defaults to repo-root .env.aigc.local",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="OpenAI API key. Prefer the hidden interactive prompt to avoid shell history.",
    )
    parser.add_argument(
        "--model",
        default="",
        help=f"image model name, default {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="optional OpenAI-compatible base URL, e.g. https://api.openai.com",
    )
    parser.add_argument(
        "--image-api-url",
        default=None,
        help="optional explicit image generation endpoint URL",
    )
    parser.add_argument(
        "--timeout",
        default="",
        help="optional image request timeout seconds, allowed range is enforced by the app",
    )
    parser.add_argument(
        "--transport",
        default="",
        choices=["", "auto", "curl", "urllib"],
        help="optional HTTP transport. Use auto unless debugging a provider.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="show current local AIGC configuration without printing secrets",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="do not prompt; requires --api-key unless OPENAI_API_KEY is set in the environment",
    )
    return parser.parse_args()


def parse_env_file(path: Path) -> tuple[list[str], dict[str, str]]:
    if not path.exists():
        return [], {}

    lines = path.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip().strip('"').strip("'")
    return lines, values


def masked_secret(value: str) -> str:
    if not value:
        return "(not set)"
    if len(value) <= 10:
        return value[:2] + "***"
    return f"{value[:6]}...{value[-4:]}"


def validate_env_value(key: str, value: str) -> str:
    value = value.strip()
    if "\n" in value or "\r" in value:
        raise SystemExit(f"{key} must be a single-line value.")
    return value


def prompt_secret(prompt: str, current_value: str = "") -> str:
    suffix = f" [{masked_secret(current_value)}]" if current_value else ""
    value = getpass.getpass(f"{prompt}{suffix}: ").strip()
    return current_value if not value and current_value else value


def prompt_text(prompt: str, current_value: str = "", default_value: str = "") -> str:
    default = current_value or default_value
    suffix = f" [{default}]" if default else " [blank]"
    value = input(f"{prompt}{suffix}: ").strip()
    return default if value == "" else value


def prompt_optional_url(prompt: str, current_value: str = "") -> str:
    if current_value:
        suffix = f" [{current_value}; type '-' to remove]"
    else:
        suffix = " [blank for official OpenAI]"
    value = input(f"{prompt}{suffix}: ").strip()
    if value == "":
        return current_value
    if value == "-":
        return ""
    return value


def build_new_values(args: argparse.Namespace, existing: dict[str, str]) -> dict[str, str]:
    if args.status:
        return {}

    if args.non_interactive:
        api_key = args.api_key.strip() or os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise SystemExit("--non-interactive requires --api-key or environment OPENAI_API_KEY.")
        model = args.model.strip() or existing.get("OPENAI_IMAGE_MODEL") or DEFAULT_MODEL
        base_url = existing.get("OPENAI_BASE_URL", "") if args.base_url is None else args.base_url.strip()
        image_api_url = (
            existing.get("OPENAI_IMAGE_API_URL", "")
            if args.image_api_url is None
            else args.image_api_url.strip()
        )
        timeout = args.timeout.strip() or existing.get("OPENAI_IMAGE_TIMEOUT_S", "")
        transport = args.transport.strip() or existing.get("OPENAI_HTTP_TRANSPORT", "")
    else:
        print("This writes a git-ignored local file: .env.aigc.local")
        print("Leave optional URL fields blank when using the official OpenAI API.")
        api_key = args.api_key.strip() or prompt_secret(
            "OPENAI_API_KEY",
            existing.get("OPENAI_API_KEY", ""),
        )
        model = args.model.strip() or prompt_text(
            "OPENAI_IMAGE_MODEL",
            existing.get("OPENAI_IMAGE_MODEL", ""),
            DEFAULT_MODEL,
        )
        base_url = (
            args.base_url.strip()
            if args.base_url is not None
            else prompt_optional_url("OPENAI_BASE_URL", existing.get("OPENAI_BASE_URL", ""))
        )
        image_api_url = (
            args.image_api_url.strip()
            if args.image_api_url is not None
            else prompt_optional_url(
                "OPENAI_IMAGE_API_URL",
                existing.get("OPENAI_IMAGE_API_URL", ""),
            )
        )
        timeout = args.timeout.strip() or prompt_text(
            "OPENAI_IMAGE_TIMEOUT_S",
            existing.get("OPENAI_IMAGE_TIMEOUT_S", ""),
            "",
        )
        transport = args.transport.strip() or prompt_text(
            "OPENAI_HTTP_TRANSPORT",
            existing.get("OPENAI_HTTP_TRANSPORT", ""),
            "auto",
        )

    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required.")

    return {
        "OPENAI_API_KEY": validate_env_value("OPENAI_API_KEY", api_key),
        "OPENAI_IMAGE_MODEL": validate_env_value("OPENAI_IMAGE_MODEL", model or DEFAULT_MODEL),
        "OPENAI_BASE_URL": validate_env_value("OPENAI_BASE_URL", base_url),
        "OPENAI_IMAGE_API_URL": validate_env_value("OPENAI_IMAGE_API_URL", image_api_url),
        "OPENAI_IMAGE_TIMEOUT_S": validate_env_value("OPENAI_IMAGE_TIMEOUT_S", timeout),
        "OPENAI_HTTP_TRANSPORT": validate_env_value("OPENAI_HTTP_TRANSPORT", transport),
    }


def key_for_line(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return ""
    return stripped.split("=", 1)[0].strip()


def render_env_file(existing_lines: list[str], new_values: dict[str, str]) -> str:
    output: list[str] = []
    seen: set[str] = set()

    if not existing_lines:
        output.extend(
            [
                "# Local AIGC/OpenAI configuration for the demo UI.",
                "# This file is ignored by git. Do not commit API keys.",
            ]
        )

    for line in existing_lines:
        key = key_for_line(line)
        if key in MANAGED_KEYS:
            seen.add(key)
            value = new_values.get(key, "")
            if value:
                output.append(f"{key}={value}")
            continue
        output.append(line)

    if output and output[-1].strip():
        output.append("")

    for key in MANAGED_KEYS:
        if key in seen:
            continue
        value = new_values.get(key, "")
        if value:
            output.append(f"{key}={value}")

    return "\n".join(output).rstrip() + "\n"


def write_env_file(path: Path, existing_lines: list[str], new_values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_env_file(existing_lines, new_values), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def print_status(path: Path, values: dict[str, str]) -> None:
    print(f"Env file: {path}")
    print(f"Exists: {'yes' if path.exists() else 'no'}")
    print(f"OPENAI_API_KEY: {masked_secret(values.get('OPENAI_API_KEY', ''))}")
    print(f"OPENAI_IMAGE_MODEL: {values.get('OPENAI_IMAGE_MODEL') or DEFAULT_MODEL}")
    print(f"OPENAI_BASE_URL: {values.get('OPENAI_BASE_URL') or '(official OpenAI default)'}")
    print(f"OPENAI_IMAGE_API_URL: {values.get('OPENAI_IMAGE_API_URL') or '(derived from base URL)'}")
    print(f"OPENAI_IMAGE_TIMEOUT_S: {values.get('OPENAI_IMAGE_TIMEOUT_S') or '(app default)'}")
    print(f"OPENAI_HTTP_TRANSPORT: {values.get('OPENAI_HTTP_TRANSPORT') or 'auto'}")


def main() -> None:
    args = parse_args()
    env_file = args.env_file.expanduser().resolve()
    existing_lines, existing_values = parse_env_file(env_file)

    if args.status:
        print_status(env_file, existing_values)
        return

    new_values = build_new_values(args, existing_values)
    write_env_file(env_file, existing_lines, new_values)
    _, written_values = parse_env_file(env_file)

    print(f"Wrote local AIGC config: {env_file}")
    print(f"OPENAI_API_KEY: {masked_secret(written_values.get('OPENAI_API_KEY', ''))}")
    print(f"OPENAI_IMAGE_MODEL: {written_values.get('OPENAI_IMAGE_MODEL') or DEFAULT_MODEL}")
    if written_values.get("OPENAI_BASE_URL"):
        print(f"OPENAI_BASE_URL: {written_values['OPENAI_BASE_URL']}")
    if written_values.get("OPENAI_IMAGE_API_URL"):
        print(f"OPENAI_IMAGE_API_URL: {written_values['OPENAI_IMAGE_API_URL']}")
    if written_values.get("OPENAI_HTTP_TRANSPORT"):
        print(f"OPENAI_HTTP_TRANSPORT: {written_values['OPENAI_HTTP_TRANSPORT']}")
    print("\nRestart the demo server after changing this file, then switch AIGC to live generation.")
    print("Example: python src/ui/demo_server.py --site PKU")


if __name__ == "__main__":
    main()
