from typing import Any, Literal

from pydantic import BaseModel, Field


ResearchType = Literal[
    "Text",
    "Integer",
    "Decimal",
    "Date",
    "District name",
    "State name",
    "Latitude",
    "Longitude",
    "Percentage",
    "Currency",
    "Binary variable",
    "Categorical variable",
]


class FileProfile(BaseModel):
    dataset_id: str
    file_name: str
    size: int
    rows: int
    columns: int
    sheets: list[str] = Field(default_factory=list)
    selected_sheet: str | None = None
    encoding: str
    duplicate_file: bool


class ColumnProfile(BaseModel):
    name: str
    inferred_type: ResearchType
    missing_count: int
    unique_count: int
    duplicate_count: int
    outlier_warning: Literal["none", "low", "medium", "high"]
    examples: list[Any]


class DatasetProfile(BaseModel):
    file: FileProfile
    columns: list[ColumnProfile]
    preview: list[dict[str, Any]]
    duplicate_rows: int
    quality_score: int
    assistant_suggestions: list[str]


class CleaningOperation(BaseModel):
    dataset_id: str
    operation: str
    columns: list[str] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)


class MergeRequest(BaseModel):
    left_dataset_id: str
    right_dataset_id: str
    keys: list[str]
    how: Literal["left", "right", "inner", "outer"] = "left"


class ExportRequest(BaseModel):
    dataset_id: str
    format: Literal["csv", "xlsx", "tsv", "r", "spss", "gis", "stata"]

