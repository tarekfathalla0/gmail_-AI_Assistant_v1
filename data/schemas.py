from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


class Memory(BaseModel):
    id: str
    type: MemoryType
    content: str
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime
    updated_at: datetime


class ExtractedMemories(BaseModel):
    semantic: list[str] = []
    episodic: list[str] = []
    procedural: list[str] = []