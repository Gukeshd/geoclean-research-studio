from __future__ import annotations

import hashlib
import io
import uuid
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import chardet
import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.harmonization.districts import harmonize_district, validate_state_district
from app.models import CleaningLog, Dataset
from app.schemas import ColumnProfile, DatasetProfile, FileProfile


MISSING_MARKERS = {"", "null", "na", "n/a", "-", "999", "9999"}
settings = get_settings()


@dataclass
class StoredDataset:
    file_name: str
    size: int
    encoding: str
    sheet_names: list[str]
    selected_sheet: str | None
    frame: pd.DataFrame
    original: pd.DataFrame
    digest: str
    log: list[str]
    raw_path: Path | None = None
    cleaned_path: Path | None = None


class DatasetStore:
    def __init__(self) -> None:
        self.datasets: dict[str, StoredDataset] = {}
        self.digests: set[str] = set()

    def add(self, file_name: str, payload: bytes, sheet: str | None = None) -> DatasetProfile:
        digest = hashlib.sha256(payload).hexdigest()
        dataset_id = str(uuid.uuid4())
        safe_name = safe_file_name(file_name)
        raw_path = settings.raw_upload_dir / f"{dataset_id}_{safe_name}"
        raw_path.write_bytes(payload)
        frame, encoding, sheets, selected_sheet = read_dataframe(file_name, payload, sheet)
        duplicate = self._is_duplicate(digest)
        stored = StoredDataset(
            file_name=file_name,
            size=len(payload),
            encoding=encoding,
            sheet_names=sheets,
            selected_sheet=selected_sheet,
            frame=frame,
            original=frame.copy(deep=True),
            digest=digest,
            log=[f"Uploaded {file_name}", "Generated automatic profile"],
            raw_path=raw_path,
        )
        self.datasets[dataset_id] = stored
        self.digests.add(digest)
        profile = profile_dataset(dataset_id, stored, duplicate)
        self._persist_dataset(dataset_id, stored, profile)
        return profile

    def get(self, dataset_id: str) -> StoredDataset:
        if dataset_id not in self.datasets:
            dataset = self._load_persisted(dataset_id)
            if dataset is None:
                raise KeyError(f"Unknown dataset_id: {dataset_id}")
            self.datasets[dataset_id] = dataset
        return self.datasets[dataset_id]

    def save_cleaned(self, dataset_id: str) -> None:
        dataset = self.get(dataset_id)
        cleaned_path = settings.cleaned_upload_dir / f"{dataset_id}_cleaned.csv"
        dataset.frame.to_csv(cleaned_path, index=False)
        dataset.cleaned_path = cleaned_path
        profile = profile_dataset(dataset_id, dataset)
        self._persist_dataset(dataset_id, dataset, profile)

    def record_log(self, dataset_id: str, operation: str, columns: list[str], options: dict[str, Any], summary: str) -> None:
        with SessionLocal() as db:
            db.add(CleaningLog(dataset_id=dataset_id, operation=operation, columns_json=columns, options_json=options, summary=summary))
            db.commit()

    def _is_duplicate(self, digest: str) -> bool:
        if digest in self.digests:
            return True
        with SessionLocal() as db:
            return db.query(Dataset).filter(Dataset.content_hash == digest).first() is not None

    def _persist_dataset(self, dataset_id: str, dataset: StoredDataset, profile: DatasetProfile) -> None:
        with SessionLocal() as db:
            record = db.get(Dataset, dataset_id)
            if record is None:
                record = Dataset(
                    id=dataset_id,
                    original_name=dataset.file_name,
                    raw_path=str(dataset.raw_path or ""),
                    content_hash=dataset.digest,
                )
                db.add(record)
            record.cleaned_path = str(dataset.cleaned_path) if dataset.cleaned_path else None
            record.encoding = dataset.encoding
            record.sheet_names = dataset.sheet_names
            record.selected_sheet = dataset.selected_sheet
            record.rows = profile.file.rows
            record.columns = profile.file.columns
            record.profile_json = profile.model_dump(mode="json")
            record.updated_at = datetime.utcnow()
            db.commit()

    def _load_persisted(self, dataset_id: str) -> StoredDataset | None:
        with SessionLocal() as db:
            record = db.get(Dataset, dataset_id)
            if record is None:
                return None
            path = Path(record.cleaned_path or record.raw_path)
            payload = path.read_bytes()
            reader_name = path.name if record.cleaned_path else record.original_name
            frame, encoding, sheets, selected_sheet = read_dataframe(reader_name, payload, record.selected_sheet)
            logs = [item.summary or item.operation for item in record.logs] or ["Loaded persisted dataset"]
            return StoredDataset(
                file_name=record.original_name,
                size=path.stat().st_size,
                encoding=record.encoding or encoding,
                sheet_names=record.sheet_names or sheets,
                selected_sheet=record.selected_sheet or selected_sheet,
                frame=frame,
                original=frame.copy(deep=True),
                digest=record.content_hash,
                log=logs,
                raw_path=Path(record.raw_path),
                cleaned_path=Path(record.cleaned_path) if record.cleaned_path else None,
            )


store = DatasetStore()


def safe_file_name(file_name: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {".", "_", "-"} else "_" for char in file_name)
    return cleaned[:180] or "dataset.csv"


def read_dataframe(file_name: str, payload: bytes, sheet: str | None = None) -> tuple[pd.DataFrame, str, list[str], str | None]:
    suffix = Path(file_name).suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        excel = pd.ExcelFile(io.BytesIO(payload))
        selected = sheet or excel.sheet_names[0]
        return pd.read_excel(excel, sheet_name=selected), "Workbook XML", excel.sheet_names, selected

    detected = chardet.detect(payload[: min(len(payload), 50000)])
    encoding = detected.get("encoding") or "utf-8"
    separator = "\t" if suffix == ".tsv" else ","
    return pd.read_csv(io.BytesIO(payload), sep=separator, encoding=encoding), encoding, ["Default"], None


def profile_dataset(dataset_id: str, dataset: StoredDataset, duplicate_file: bool = False) -> DatasetProfile:
    frame = dataset.frame.replace({np.nan: None})
    columns = [profile_column(name, frame[name]) for name in frame.columns]
    missing_total = sum(column.missing_count for column in columns)
    duplicate_rows = int(frame.duplicated().sum())
    warning_count = sum(1 for column in columns if column.outlier_warning != "none")
    quality_score = max(5, min(99, round(96 - missing_total / max(1, len(frame)) * 35 - duplicate_rows * 0.4 - warning_count * 2)))
    return DatasetProfile(
        file=FileProfile(
            dataset_id=dataset_id,
            file_name=dataset.file_name,
            size=dataset.size,
            rows=int(len(frame)),
            columns=int(len(frame.columns)),
            sheets=dataset.sheet_names,
            selected_sheet=dataset.selected_sheet,
            encoding=dataset.encoding,
            duplicate_file=duplicate_file,
        ),
        columns=columns,
        preview=frame.head(100).to_dict(orient="records"),
        duplicate_rows=duplicate_rows,
        quality_score=quality_score,
        assistant_suggestions=suggest_issues(frame, columns),
    )


def profile_column(name: str, series: pd.Series) -> ColumnProfile:
    normalized = series.map(lambda value: str(value).strip().lower() if value is not None else "")
    missing = int(series.isna().sum() + normalized.isin(MISSING_MARKERS).sum())
    unique = int(series.nunique(dropna=True))
    duplicates = int(series.duplicated(keep=False).sum())
    inferred = infer_type(name, series)
    outlier = outlier_level(series, inferred)
    examples = [value for value in series.dropna().head(5).tolist()]
    return ColumnProfile(
        name=str(name),
        inferred_type=inferred,
        missing_count=missing,
        unique_count=unique,
        duplicate_count=duplicates,
        outlier_warning=outlier,
        examples=examples,
    )


def infer_type(name: str, series: pd.Series) -> str:
    lower_name = name.lower()
    sample = series.dropna().astype(str).str.strip()
    if "district" in lower_name:
        return "District name"
    if lower_name in {"state", "state_name"} or "state" in lower_name:
        return "State name"
    if "lat" in lower_name:
        return "Latitude"
    if "lon" in lower_name or "lng" in lower_name:
        return "Longitude"
    if "date" in lower_name or parseable_dates(sample) > 0.75:
        return "Date"
    if sample.str.contains("%", regex=False).mean() > 0.35 or "pct" in lower_name or "percent" in lower_name:
        return "Percentage"
    if sample.str.contains(r"₹|\$|rs\.?|inr", regex=True, case=False).mean() > 0.25:
        return "Currency"
    numeric = pd.to_numeric(clean_numeric(sample), errors="coerce")
    numeric_ratio = float(numeric.notna().mean()) if len(sample) else 0
    if numeric_ratio > 0.86:
        if (numeric.dropna() % 1 == 0).all():
            return "Integer"
        return "Decimal"
    if unique_lower(sample) <= 2:
        return "Binary variable"
    if unique_lower(sample) <= max(20, len(sample) * 0.15):
        return "Categorical variable"
    return "Text"


def outlier_level(series: pd.Series, inferred: str) -> str:
    if inferred not in {"Integer", "Decimal", "Percentage", "Currency", "Latitude", "Longitude"}:
        return "none"
    numeric = pd.to_numeric(clean_numeric(series.dropna().astype(str)), errors="coerce").dropna()
    if len(numeric) < 8:
        return "none"
    impossible_percentage = inferred == "Percentage" and ((numeric < 0) | (numeric > 100)).mean() > 0
    invalid_geo = inferred == "Latitude" and ((numeric < -90) | (numeric > 90)).mean() > 0
    invalid_lon = inferred == "Longitude" and ((numeric < -180) | (numeric > 180)).mean() > 0
    q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
    iqr = q3 - q1
    extreme = ((numeric < q1 - 1.5 * iqr) | (numeric > q3 + 1.5 * iqr)).mean() if iqr else 0
    if impossible_percentage or invalid_geo or invalid_lon or extreme > 0.08:
        return "high"
    if extreme > 0.03:
        return "medium"
    if extreme > 0:
        return "low"
    return "none"


def clean_numeric(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"[₹,$%]|rs\.?|inr", "", regex=True, case=False).str.extract(r"(-?\d+(?:\.\d+)?)")[0]


def parseable_dates(series: pd.Series) -> float:
    if len(series) == 0:
        return 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(series, errors="coerce", dayfirst=True)
    return float(parsed.notna().mean())


def unique_lower(series: pd.Series) -> int:
    return int(series.astype(str).str.strip().str.lower().nunique())


def standardize_column_name(name: str) -> str:
    aliases = {
        "dist": "district",
        "dist_name": "district",
        "district_name": "district",
        "districtname": "district",
        "state_name": "state",
        "statename": "state",
    }
    normalized = "".join(char.lower() if char.isalnum() else "_" for char in str(name).strip())
    normalized = "_".join(part for part in normalized.split("_") if part)
    return aliases.get(normalized, normalized)


def fuzzy_duplicate_mask(frame: pd.DataFrame, columns: list[str], threshold: float = 0.94) -> pd.Series:
    try:
        from rapidfuzz import fuzz
    except ImportError:
        from difflib import SequenceMatcher

        def ratio(left: str, right: str) -> float:
            return SequenceMatcher(None, left, right).ratio()
    else:

        def ratio(left: str, right: str) -> float:
            return fuzz.token_sort_ratio(left, right) / 100

    keys = frame[columns].fillna("").astype(str).agg(" | ".join, axis=1)
    duplicate = pd.Series(False, index=frame.index)
    seen: list[str] = []
    for index, key in keys.items():
        if any(ratio(key, prior) >= threshold for prior in seen):
            duplicate.loc[index] = True
        else:
            seen.append(key)
    return duplicate


def isolation_forest_flags(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(clean_numeric(values.astype(str)), errors="coerce")
    flags = pd.Series(False, index=values.index)
    if numeric.notna().sum() < 12:
        return flags
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        z = (numeric - numeric.mean()) / numeric.std(ddof=0)
        return z.abs() > 3
    model = IsolationForest(contamination="auto", random_state=42)
    valid = numeric.dropna()
    predictions = model.fit_predict(valid.to_frame())
    flags.loc[valid.index] = predictions == -1
    return flags


def knn_impute(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    numeric = frame[columns].apply(lambda series: pd.to_numeric(clean_numeric(series.astype(str)), errors="coerce"))
    try:
        from sklearn.impute import KNNImputer
    except ImportError:
        return numeric.fillna(numeric.median(numeric_only=True))
    imputer = KNNImputer(n_neighbors=min(5, max(1, len(numeric) - 1)))
    return pd.DataFrame(imputer.fit_transform(numeric), columns=columns, index=frame.index)


def suggest_issues(frame: pd.DataFrame, columns: list[ColumnProfile]) -> list[str]:
    suggestions = []
    if any(column.inferred_type == "District name" for column in columns):
        suggestions.append("Run district harmonization before merging NFHS, Census, NSSO, or GIS attribute tables.")
    if any(column.missing_count for column in columns):
        suggestions.append("Normalize blank, NULL, NA, N/A, dash, 999, and 9999 markers before imputation.")
    if frame.duplicated().sum() > 0:
        suggestions.append("Review full-row duplicates and duplicate join keys before spatial joins.")
    if any(column.outlier_warning in {"medium", "high"} for column in columns):
        suggestions.append("Inspect statistical outliers using IQR and z-score before building composite indexes.")
    return suggestions or ["Dataset profile is clean enough for research-ready export."]


def apply_operation(dataset_id: str, operation: str, columns: list[str], options: dict[str, Any]) -> DatasetProfile:
    dataset = store.get(dataset_id)
    frame = dataset.frame.copy()
    targets = columns or list(frame.columns)
    if operation == "text_clean":
        for column in targets:
            frame[column] = frame[column].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
            case = options.get("case")
            if case == "upper":
                frame[column] = frame[column].str.upper()
            elif case == "lower":
                frame[column] = frame[column].str.lower()
            elif case == "proper":
                frame[column] = frame[column].str.title()
    elif operation == "missing":
        marker_mask = frame[targets].astype(str).map(lambda value: value.strip().lower() in MISSING_MARKERS)
        frame[targets] = frame[targets].mask(marker_mask)
        method = options.get("method", "blank")
        for column in targets:
            if method in {"mean", "median"}:
                values = pd.to_numeric(clean_numeric(frame[column].astype(str)), errors="coerce")
                replacement = values.mean() if method == "mean" else values.median()
                frame[column] = frame[column].fillna(replacement)
            elif method == "mode":
                mode = frame[column].mode(dropna=True)
                frame[column] = frame[column].fillna(mode.iloc[0] if not mode.empty else "")
            elif method == "zero":
                frame[column] = frame[column].fillna(0)
            elif method == "custom":
                frame[column] = frame[column].fillna(options.get("value", ""))
            elif method == "interpolation":
                values = pd.to_numeric(clean_numeric(frame[column].astype(str)), errors="coerce")
                frame[column] = values.interpolate(limit_direction="both")
        if method == "knn":
            frame[targets] = knn_impute(frame, targets)
    elif operation == "duplicates":
        keep = options.get("keep", "first")
        subset = targets or None
        if options.get("fuzzy"):
            mask = fuzzy_duplicate_mask(frame, targets, float(options.get("threshold", 0.94)))
            frame = frame.loc[~mask]
        else:
            frame = frame.drop_duplicates(subset=subset, keep=False if keep == "none" else keep)
    elif operation == "numeric":
        decimals = int(options.get("decimals", 2))
        for column in targets:
            frame[column] = pd.to_numeric(clean_numeric(frame[column].astype(str)), errors="coerce").round(decimals)
    elif operation == "dates":
        output_format = options.get("format", "%Y-%m-%d")
        for column in targets:
            frame[column] = pd.to_datetime(frame[column], errors="coerce", dayfirst=True).dt.strftime(output_format)
    elif operation == "harmonize_districts":
        state_col = options.get("state_column")
        for column in targets:
            frame[f"{column}_standard"] = [
                harmonize_district(value, frame[state_col].iloc[index] if state_col in frame.columns else None)["standard"]
                for index, value in enumerate(frame[column])
            ]
    elif operation == "standardize":
        method = options.get("method", "zscore")
        for column in targets:
            values = pd.to_numeric(clean_numeric(frame[column].astype(str)), errors="coerce")
            if method == "minmax":
                frame[f"{column}_minmax"] = (values - values.min()) / (values.max() - values.min())
            else:
                frame[f"{column}_z"] = (values - values.mean()) / values.std(ddof=0)
    elif operation == "standardize_columns":
        frame = frame.rename(columns={column: standardize_column_name(column) for column in frame.columns})
    elif operation == "outliers":
        method = options.get("method", "iqr")
        for column in targets:
            values = pd.to_numeric(clean_numeric(frame[column].astype(str)), errors="coerce")
            if method == "isolation_forest":
                frame[f"{column}_outlier"] = isolation_forest_flags(frame[column])
            elif method == "zscore":
                z = (values - values.mean()) / values.std(ddof=0)
                frame[f"{column}_outlier"] = z.abs() > float(options.get("threshold", 3))
            else:
                q1, q3 = values.quantile(0.25), values.quantile(0.75)
                iqr = q3 - q1
                frame[f"{column}_outlier"] = (values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)
    dataset.frame = frame
    summary = f"Applied {operation} on {', '.join(targets)}"
    dataset.log.insert(0, summary)
    store.save_cleaned(dataset_id)
    store.record_log(dataset_id, operation, targets, options, summary)
    return profile_dataset(dataset_id, dataset)


def merge_datasets(left_id: str, right_id: str, keys: list[str], how: str = "left") -> dict[str, Any]:
    left = store.get(left_id).frame
    right = store.get(right_id).frame
    merged = left.merge(right, on=keys, how=how, indicator=True, suffixes=("", "_right"))
    success = int((merged["_merge"] == "both").sum())
    dataset_id = str(uuid.uuid4())
    store.datasets[dataset_id] = StoredDataset(
        file_name="merged_research_dataset.csv",
        size=0,
        encoding="UTF-8",
        sheet_names=["Merged"],
        selected_sheet=None,
        frame=merged.drop(columns=["_merge"]),
        original=merged.drop(columns=["_merge"]).copy(),
        digest=dataset_id,
        log=[f"Merged {left_id} and {right_id} using {keys}"],
    )
    return {
        "dataset_id": dataset_id,
        "merge_success_rate": round(success / max(1, len(merged)) * 100, 2),
        "unmatched_rows": int((merged["_merge"] != "both").sum()),
        "duplicate_joins": int(merged.duplicated(subset=keys, keep=False).sum()),
        "missing_join_keys": int(merged[keys].isna().any(axis=1).sum()),
        "preview": merged.head(50).to_dict(orient="records"),
    }


def validation_report(dataset_id: str, state_column: str, district_column: str) -> list[dict[str, Any]]:
    frame = store.get(dataset_id).frame
    return [
        validate_state_district(row[state_column], row[district_column])
        for _, row in frame[[state_column, district_column]].head(500).iterrows()
    ]
