from __future__ import annotations

from typing import Any

from app.core.database import SessionLocal
from app.models import SavedWorkflow
from app.services.datasets import apply_operation


def save_workflow(name: str, description: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    with SessionLocal() as db:
        workflow = SavedWorkflow(name=name, description=description, steps_json=steps)
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        return {"workflow_id": workflow.id, "name": workflow.name, "steps": workflow.steps_json}


def list_workflows() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        return [
            {"workflow_id": workflow.id, "name": workflow.name, "description": workflow.description, "steps": workflow.steps_json}
            for workflow in db.query(SavedWorkflow).order_by(SavedWorkflow.created_at.desc()).all()
        ]


def run_workflow(workflow_id: str, dataset_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        workflow = db.get(SavedWorkflow, workflow_id)
        if workflow is None:
            raise KeyError(f"Unknown workflow_id: {workflow_id}")
        profile = None
        for step in workflow.steps_json:
            profile = apply_operation(
                dataset_id,
                step.get("operation", ""),
                step.get("columns", []),
                step.get("options", {}),
            )
        return {"workflow_id": workflow_id, "dataset_id": dataset_id, "profile": profile}


def run_batch(dataset_ids: list[str], operations: list[dict[str, Any]], workflow_id: str | None = None) -> list[dict[str, Any]]:
    results = []
    if workflow_id:
        for dataset_id in dataset_ids:
            results.append(run_workflow(workflow_id, dataset_id))
        return results
    for dataset_id in dataset_ids:
        profile = None
        for operation in operations:
            profile = apply_operation(
                dataset_id,
                operation.get("operation", ""),
                operation.get("columns", []),
                operation.get("options", {}),
            )
        results.append({"dataset_id": dataset_id, "profile": profile})
    return results
