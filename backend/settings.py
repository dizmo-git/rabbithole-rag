from pathlib import Path

from pydantic import BaseModel, ValidationError

# Resolved from this file, not the cwd. Lives outside data/notebooks/, so nuke() keeps it.
SETTINGS_PATH = Path(__file__).resolve().parent.parent / "data" / "settings.json"


class AppSettings(BaseModel):
    # Defaults use the ":latest" names because that's how `ollama list` reports models.
    # New fields need a default, so an older settings.json still loads.
    chat_model: str = "llama3.2:latest"  # answers + query rewriting
    embedding_model: str = "nomic-embed-text:latest"  # default for NEW notebooks only


_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    global _settings
    if _settings is None:
        _settings = _load()
    return _settings


def save_settings(settings: AppSettings) -> None:
    global _settings
    SETTINGS_PATH.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
    _settings = settings


def _load() -> AppSettings:
    if not SETTINGS_PATH.exists():
        return AppSettings()
    try:
        return AppSettings.model_validate_json(SETTINGS_PATH.read_text(encoding="utf-8"))
    except ValidationError as e:
        print(f"Invalid {SETTINGS_PATH}, using defaults: {e}")
        return AppSettings()
