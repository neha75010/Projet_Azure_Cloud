from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_API_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _API_DIR.parent.parent

_env_candidates = [_API_DIR / ".env", _PROJECT_ROOT / ".env"]
_env_files = tuple(str(p) for p in _env_candidates if p.is_file()) or (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cosmos_endpoint: str
    cosmos_key: str
    cosmos_database: str = "db-doc"
    cosmos_container: str = "jobs"
    blob_connection_string: str
    blob_container: str

settings = Settings()