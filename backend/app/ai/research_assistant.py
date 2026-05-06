from __future__ import annotations

import pandas as pd

from app.schemas import ColumnProfile


def understand_dataset(frame: pd.DataFrame, columns: list[ColumnProfile]) -> dict[str, object]:
    names = {column.name.lower(): column for column in columns}
    date_like = [column.name for column in columns if column.inferred_type == "Date" or "year" in column.name.lower()]
    district_like = [column.name for column in columns if column.inferred_type == "District name"]
    state_like = [column.name for column in columns if column.inferred_type == "State name"]
    id_like = [column for column in frame.columns if "id" in str(column).lower() or "code" in str(column).lower()]

    data_shape = "cross-sectional"
    if district_like and date_like:
        data_shape = "district panel data"
    elif date_like:
        data_shape = "time-series"
    elif district_like or state_like:
        data_shape = "spatial cross-sectional"
    elif any("weight" in key or "cluster" in key or "psu" in key for key in names):
        data_shape = "survey data"

    suggestions = []
    if data_shape in {"district panel data", "time-series"}:
        suggestions.append("Check temporal gaps and use interpolation only for continuous indicators with stable measurement definitions.")
    if district_like:
        suggestions.append("Harmonize district names and reconcile post-2011 splits before merging Census, NFHS, NSSO, or LULC outputs.")
    if id_like:
        suggestions.append("Preserve ID/code columns as join keys for R, Stata, SPSS, QGIS, ArcGIS, and GeoDa workflows.")
    if any(column.missing_count for column in columns):
        suggestions.append("Create a missing value report and document the imputation method in the methodology chapter.")
    if not suggestions:
        suggestions.append("Dataset is ready for descriptive statistics, visualization, and export.")

    visualizations = ["missing value heatmap", "correlation matrix"]
    if district_like:
        visualizations.extend(["choropleth map", "district cluster map"])
    if date_like:
        visualizations.extend(["time slider", "yearly comparison lines"])

    statistical_tests = ["descriptive statistics"]
    if data_shape == "district panel data":
        statistical_tests.extend(["fixed effects screening", "trend analysis"])
    elif data_shape == "spatial cross-sectional":
        statistical_tests.extend(["Moran's I screening", "spatial autocorrelation diagnostics"])
    elif data_shape == "survey data":
        statistical_tests.extend(["weighted frequency tables", "design-aware cross tabulation"])

    return {
        "detected_dataset_type": data_shape,
        "suggested_cleaning_steps": suggestions,
        "recommended_visualizations": visualizations,
        "recommended_statistical_tests": statistical_tests,
    }
