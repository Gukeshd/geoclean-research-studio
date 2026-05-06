from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "GeoClean Research Studio API"
    database_url: str = "sqlite:///./geoclean.db"
    upload_root: Path = Path("../uploads")
    raw_upload_dir: Path = Path("../uploads/raw")
    cleaned_upload_dir: Path = Path("../uploads/cleaned")
    export_dir: Path = Path("../uploads/exports")
    temp_dir: Path = Path("../uploads/temp")
    district_alias_path: Path = Path("data/district_alias_master.csv")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    def ensure_directories(self) -> None:
        for path in [self.raw_upload_dir, self.cleaned_upload_dir, self.export_dir, self.temp_dir]:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./geoclean.db"),
        upload_root=Path(os.getenv("UPLOAD_ROOT", "../uploads")),
        raw_upload_dir=Path(os.getenv("RAW_UPLOAD_DIR", "../uploads/raw")),
        cleaned_upload_dir=Path(os.getenv("CLEANED_UPLOAD_DIR", "../uploads/cleaned")),
        export_dir=Path(os.getenv("EXPORT_DIR", "../uploads/exports")),
        temp_dir=Path(os.getenv("TEMP_DIR", "../uploads/temp")),
    )
    settings.ensure_directories()
    return settings
