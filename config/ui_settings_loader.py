import json
from pathlib import Path

_UI_SETTINGS_PATH = Path(__file__).parent / "ui_settings.json"


def load_ui_settings() -> dict:
    """Read ui_settings.json and return its contents as a dict.

    Returns an empty dict if the file does not exist yet or is malformed.
    """
    if not _UI_SETTINGS_PATH.exists():
        return {}
    try:
        with _UI_SETTINGS_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_ui_settings(data: dict) -> None:
    """Write data to ui_settings.json atomically via a temp file."""
    tmp = _UI_SETTINGS_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(_UI_SETTINGS_PATH)
