import json
import os
from pathlib import Path

_UI_SETTINGS_PATH = Path(__file__).parent / "ui_settings.json"

_ENV_KEY_MAP = {
    "atlassian_url": "ATLASSIAN_URL",
    "atlassian_user": "ATLASSIAN_USER",
    "atlassian_api_token": "ATLASSIAN_API_TOKEN",
    "confluence_space_key": "CONFLUENCE_SPACE_KEY",
    "test_plan_parent_id": "TEST_PLAN_PARENT_ID",
    "qa_report_parent_id": "QA_REPORT_PARENT_ID",
    "mor_parent_id": "MOR_PARENT_ID",
}


def load_ui_settings() -> dict:
    """Read ui_settings.json; fall back to environment variables if file is absent."""
    if _UI_SETTINGS_PATH.exists():
        try:
            with _UI_SETTINGS_PATH.open(encoding="utf-8") as f:
                data = json.load(f)
            if data:
                return data
        except json.JSONDecodeError:
            pass
    return {k: os.environ.get(v, "") for k, v in _ENV_KEY_MAP.items()}


def save_ui_settings(data: dict) -> None:
    """Write data to ui_settings.json atomically via a temp file."""
    tmp = _UI_SETTINGS_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(_UI_SETTINGS_PATH)
