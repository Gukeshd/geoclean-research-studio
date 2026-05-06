import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255), default="Untitled research session")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="session")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="researcher")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("research_sessions.id"), nullable=True)
    original_name: Mapped[str] = mapped_column(String(512))
    raw_path: Mapped[str] = mapped_column(String(1024))
    cleaned_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    encoding: Mapped[str] = mapped_column(String(80), default="UTF-8")
    sheet_names: Mapped[list[str]] = mapped_column(JSON, default=list)
    selected_sheet: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rows: Mapped[int] = mapped_column(Integer, default=0)
    columns: Mapped[int] = mapped_column(Integer, default=0)
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped[ResearchSession | None] = relationship(back_populates="datasets")
    logs: Mapped[list["CleaningLog"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")
    exports: Mapped[list["ExportHistory"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class CleaningLog(Base):
    __tablename__ = "cleaning_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    operation: Mapped[str] = mapped_column(String(120))
    columns_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    options_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dataset: Mapped[Dataset] = relationship(back_populates="logs")


class DistrictAlias(Base):
    __tablename__ = "district_aliases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    original: Mapped[str] = mapped_column(String(255), index=True)
    standard: Mapped[str] = mapped_column(String(255), index=True)
    source: Mapped[str] = mapped_column(String(120), default="district_alias_master.csv")
    confidence: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExportHistory(Base):
    __tablename__ = "export_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    format: Mapped[str] = mapped_column(String(40))
    output_path: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dataset: Mapped[Dataset] = relationship(back_populates="exports")


class MetadataReport(Base):
    __tablename__ = "metadata_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    output_path: Mapped[str] = mapped_column(String(1024))
    report_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SavedWorkflow(Base):
    __tablename__ = "saved_workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    steps_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
