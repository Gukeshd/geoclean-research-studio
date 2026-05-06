<<<<<<< HEAD
# GeoClean Research Studio

Professional AI-powered research data cleaning and harmonization web application for dissertation, thesis, GIS, NFHS, Census, NSSO, public health, socio-economic, food security, and spatial datasets.

## Stack

- Frontend: React, TypeScript, Vite, TailwindCSS, ShadCN-inspired local UI patterns, Lucide icons, Recharts
- Backend: FastAPI, SQLAlchemy, Alembic, Pandas, NumPy, OpenPyXL
- Persistence: SQLite by default, PostgreSQL-ready through `DATABASE_URL`
- Storage: local `uploads/raw`, `uploads/cleaned`, `uploads/exports`, `uploads/temp`
- Exports: CSV, Excel, TSV, R-ready CSV, SPSS-ready CSV, GIS-ready CSV, Stata-ready CSV, PDF metadata, DOCX metadata

## Run Locally

Install backend dependencies:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Install frontend dependencies and start the studio:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Production Structure

The backend is organized for growth:

```text
backend/app/
  api/
  ai/
  cleaning/
  core/
  exports/
  harmonization/
  models/
  schemas/
  services/
  utils/
  main.py
```

## Persistent Data

The app now stores:

- uploaded file metadata and paths
- raw files under `uploads/raw`
- cleaned snapshots under `uploads/cleaned`
- export artifacts under `uploads/exports`
- cleaning logs
- export history
- metadata report history
- saved workflows
- JWT-ready users and roles
- district aliases from `backend/data/district_alias_master.csv`

## Added API Areas

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/datasets/{dataset_id}/ai-understanding`
- `GET /api/datasets/{dataset_id}/analytics`
- `GET /api/geospatial/capabilities`
- `POST /api/workflows`
- `POST /api/workflows/run`
- `POST /api/batch/run`

## Core Features

- Multi-file upload for `.csv`, `.xlsx`, `.xls`, and `.tsv`
- Encoding detection, sheet discovery, duplicate file detection
- First 100 rows preview and column profiling
- Type inference for text, numeric, date, district, state, latitude, longitude, percentage, currency, binary, and categorical variables
- Manual data type override controls
- Text, missing value, duplicate, numeric, percentage, and date cleaning operations
- India district harmonization with fuzzy matching and state-district validation
- Z-score, min-max, reverse coding, and composite index preparation
- Multi-file merge diagnostics with success rate, unmatched rows, duplicate joins, and missing join keys
- IQR, z-score, impossible percentage, invalid negative, and geospatial outlier warnings
- Data quality dashboard with before/after KPIs, timeline, charts, matrix, and choropleth preview
- Automatic cleaning log, transformation history, variable dictionary, and metadata reports
- Advanced missing value handling: mean, median, mode, interpolation, KNN
- Advanced duplicate handling: exact and fuzzy duplicates
- Advanced outliers: IQR, z-score, Isolation Forest
- Automatic column name standardization
- AI dataset understanding for panel, time-series, cross-sectional, spatial, and survey datasets
- Statistical dashboard backend for skewness, kurtosis, correlation, and PCA preview
- Geospatial extension points for GeoPandas, Rasterio, and Folium/Leaflet workflows
- Reusable workflow and batch processing APIs

## Docker

```powershell
docker compose up --build
```

The compose stack includes frontend, backend, PostgreSQL, and nginx.

## API

FastAPI docs are available at http://127.0.0.1:8000/docs after starting the backend.
=======
# geoclean-research-studio
>>>>>>> 1d80389ccb8ffbd07b898068483553fdcf50283c
