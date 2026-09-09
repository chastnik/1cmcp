from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Health(BaseModel):
    status: str
    service: str
    version: str
    api: str
    time: str


class Problem(BaseModel):
    type: str
    title: str
    status: int
    code: str
    detail: str | None = None
    instance: str | None = None


class Ref(BaseModel):
    ref: str
    id: str
    presentation: str | None = None


class MetaSummary(BaseModel):
    kind: str
    name: str
    synonym: str | None = None
    description: str | None = None
    examples: list[str] = Field(default_factory=list)


class MetaField(BaseModel):
    name: str
    type: str
    synonym: str | None = None
    required: bool | None = None
    description: str | None = None
    examples: list[str] = Field(default_factory=list)


class MetaObject(BaseModel):
    kind: str
    name: str
    fields: list[MetaField]
    synonym: str | None = None
    description: str | None = None
    examples: list[str] = Field(default_factory=list)
    tabular_sections: list[dict[str, Any]] = Field(default_factory=list)
    json_schema: dict[str, Any] | None = None
