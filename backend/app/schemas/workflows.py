from typing import Any

from pydantic import BaseModel, Field


class WorkflowSaveRequest(BaseModel):
    name: str
    description: str = ""
    steps: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowRunRequest(BaseModel):
    workflow_id: str
    dataset_id: str


class BatchRequest(BaseModel):
    dataset_ids: list[str]
    workflow_id: str | None = None
    operations: list[dict[str, Any]] = Field(default_factory=list)
