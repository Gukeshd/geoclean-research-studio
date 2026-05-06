from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.datasets import clean_numeric


def statistical_dashboard(frame: pd.DataFrame) -> dict[str, object]:
    numeric = frame.apply(lambda series: pd.to_numeric(clean_numeric(series.astype(str)), errors="coerce"))
    numeric = numeric.dropna(axis=1, how="all")
    if numeric.empty:
        return {"numeric_columns": [], "summary": [], "correlation": [], "pca_preview": []}
    summary = []
    for column in numeric.columns:
        values = numeric[column].dropna()
        if values.empty:
            continue
        summary.append(
            {
                "column": column,
                "mean": float(values.mean()),
                "median": float(values.median()),
                "std": float(values.std(ddof=0)),
                "skewness": float(values.skew()),
                "kurtosis": float(values.kurtosis()),
            }
        )
    correlation = numeric.corr(numeric_only=True).fillna(0).round(4).to_dict()
    return {
        "numeric_columns": list(numeric.columns),
        "summary": summary,
        "correlation": correlation,
        "pca_preview": pca_preview(numeric),
    }


def pca_preview(numeric: pd.DataFrame) -> list[dict[str, float | str]]:
    clean = numeric.fillna(numeric.median(numeric_only=True))
    if clean.shape[1] < 2 or clean.shape[0] < 2:
        return []
    standardized = (clean - clean.mean()) / clean.std(ddof=0).replace(0, 1)
    matrix = standardized.to_numpy()
    _, _, vh = np.linalg.svd(matrix, full_matrices=False)
    loadings = vh[:2]
    return [
        {"column": str(column), "pc1": float(loadings[0, index]), "pc2": float(loadings[1, index])}
        for index, column in enumerate(clean.columns)
    ]
