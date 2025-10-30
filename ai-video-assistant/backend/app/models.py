"""SQLModel tables for persisting video analysis state."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class VideoRecord(SQLModel, table=True):
    video_id: str = Field(primary_key=True, index=True)
    filename: str
    status: str = Field(default="pending")
    message: Optional[str] = None
    result_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class ScriptRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: str = Field(index=True)
    style: str
    script_text: str = Field(sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

