from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def geospatial_capabilities() -> dict[str, object]:
    return {
        "vector": ["Shapefile", "GeoJSON", "spatial joins", "CRS conversion"],
        "raster": ["GeoTIFF", "raster statistics", "NDVI-ready bands", "change detection hooks"],
        "maps": ["Leaflet/Folium district previews", "choropleths", "cluster maps"],
        "optional_libraries": {
            "geopandas": _available("geopandas"),
            "rasterio": _available("rasterio"),
            "folium": _available("folium"),
        },
    }


def vector_profile(path: Path) -> dict[str, Any]:
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise RuntimeError("GeoPandas is required for shapefile/GeoJSON profiling.") from exc
    gdf = gpd.read_file(path)
    return {
        "features": int(len(gdf)),
        "crs": str(gdf.crs),
        "columns": list(gdf.columns),
        "bounds": list(gdf.total_bounds),
        "geometry_types": gdf.geometry.geom_type.value_counts().to_dict(),
    }


def raster_profile(path: Path) -> dict[str, Any]:
    try:
        import rasterio
    except ImportError as exc:
        raise RuntimeError("Rasterio is required for GeoTIFF profiling.") from exc
    with rasterio.open(path) as src:
        return {
            "bands": src.count,
            "crs": str(src.crs),
            "width": src.width,
            "height": src.height,
            "bounds": list(src.bounds),
            "dtypes": list(src.dtypes),
        }


def district_join_preview(attributes: pd.DataFrame, district_column: str, spatial_key_column: str) -> dict[str, Any]:
    return {
        "attribute_rows": int(len(attributes)),
        "district_column": district_column,
        "spatial_key_column": spatial_key_column,
        "missing_districts": int(attributes[district_column].isna().sum()) if district_column in attributes else None,
        "missing_spatial_keys": int(attributes[spatial_key_column].isna().sum()) if spatial_key_column in attributes else None,
    }


def _available(package: str) -> bool:
    try:
        __import__(package)
        return True
    except ImportError:
        return False
