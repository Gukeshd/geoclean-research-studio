from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.ai import understand_dataset
from app.core.config import get_settings
from app.core.database import init_db
from app.core.security import create_access_token, hash_password, verify_password
from app.exports import export_dataset, metadata_document
from app.models import ExportHistory, MetadataReport, User
from app.schemas import BatchRequest, CleaningOperation, ExportRequest, MergeRequest, UserCreate, UserLogin, WorkflowRunRequest, WorkflowSaveRequest
from app.services.analytics import statistical_dashboard
from app.services.datasets import apply_operation, merge_datasets, profile_dataset, store, validation_report
from app.services.geospatial import geospatial_capabilities
from app.services.workflows import list_workflows, run_batch, run_workflow, save_workflow
from app.core.database import SessionLocal


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.1.0",
    description="Persistent, modular research data cleaning backend for dissertation, GIS, NFHS, public health, and socio-economic datasets.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "storage": str(settings.upload_root)}


@app.post("/api/auth/register")
def register(request: UserCreate):
    with SessionLocal() as db:
        if db.query(User).filter(User.username == request.username).first() is not None:
            raise HTTPException(status_code=409, detail="Username already exists.")
        user = User(username=request.username, hashed_password=hash_password(request.password), role=request.role)
        db.add(user)
        db.commit()
        return {"user_id": user.id, "username": user.username, "role": user.role}


@app.post("/api/auth/login")
def login(request: UserLogin):
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == request.username).first()
        if user is None or not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid username or password.")
        return {"access_token": create_access_token(user.username, user.role), "token_type": "bearer", "role": user.role}


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...), sheet: str | None = Form(default=None)):
    extension = file.filename.lower().rsplit(".", 1)[-1]
    if extension not in {"csv", "xlsx", "xls", "tsv"}:
        raise HTTPException(status_code=400, detail="Only CSV, XLSX, XLS, and TSV files are supported.")
    payload = await file.read()
    try:
        return store.add(file.filename, payload, sheet)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Unable to parse dataset: {exc}") from exc


@app.get("/api/datasets/{dataset_id}/profile")
def get_profile(dataset_id: str):
    try:
        return profile_dataset(dataset_id, store.get(dataset_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/clean")
def clean_dataset(operation: CleaningOperation):
    try:
        return apply_operation(operation.dataset_id, operation.operation, operation.columns, operation.options)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Cleaning operation failed: {exc}") from exc


@app.post("/api/merge")
def merge_dataset(request: MergeRequest):
    try:
        return merge_datasets(request.left_dataset_id, request.right_dataset_id, request.keys, request.how)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Merge failed: {exc}") from exc


@app.get("/api/datasets/{dataset_id}/validate-districts")
def validate_districts(dataset_id: str, state_column: str = "state", district_column: str = "district"):
    try:
        return validation_report(dataset_id, state_column, district_column)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Validation failed: {exc}") from exc


@app.get("/api/datasets/{dataset_id}/ai-understanding")
def ai_understanding(dataset_id: str):
    try:
        dataset = store.get(dataset_id)
        profile = profile_dataset(dataset_id, dataset)
        return understand_dataset(dataset.frame, profile.columns)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/datasets/{dataset_id}/analytics")
def analytics(dataset_id: str):
    try:
        return statistical_dashboard(store.get(dataset_id).frame)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/geospatial/capabilities")
def geospatial():
    return geospatial_capabilities()


@app.post("/api/workflows")
def create_workflow(request: WorkflowSaveRequest):
    return save_workflow(request.name, request.description, request.steps)


@app.get("/api/workflows")
def workflows():
    return list_workflows()


@app.post("/api/workflows/run")
def execute_workflow(request: WorkflowRunRequest):
    try:
        return run_workflow(request.workflow_id, request.dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/batch/run")
def execute_batch(request: BatchRequest):
    try:
        return run_batch(request.dataset_ids, request.operations, request.workflow_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/export")
def export_file(request: ExportRequest):
    try:
        dataset = store.get(request.dataset_id)
        payload, media_type, extension = export_dataset(dataset, request.format)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    output_path = settings.export_dir / f"{request.dataset_id}_{request.format}.{extension}"
    output_path.write_bytes(payload)
    with SessionLocal() as db:
        db.add(ExportHistory(dataset_id=request.dataset_id, format=request.format, output_path=str(output_path)))
        db.commit()
    file_name = f"geoclean_{request.format}_dataset.{extension}"
    return StreamingResponse(
        iter([payload]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@app.get("/api/datasets/{dataset_id}/documentation/{kind}")
def documentation(dataset_id: str, kind: str):
    if kind not in {"pdf", "docx"}:
        raise HTTPException(status_code=400, detail="Documentation kind must be pdf or docx.")
    try:
        dataset = store.get(dataset_id)
        payload, media_type, extension = metadata_document(dataset_id, dataset, kind)  # type: ignore[arg-type]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    output_path = settings.export_dir / f"{dataset_id}_metadata_report.{extension}"
    output_path.write_bytes(payload)
    with SessionLocal() as db:
        db.add(MetadataReport(dataset_id=dataset_id, kind=kind, output_path=str(output_path), report_json={"format": kind}))
        db.commit()
    return StreamingResponse(
        iter([payload]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="geoclean_metadata_report.{extension}"'},
    )
