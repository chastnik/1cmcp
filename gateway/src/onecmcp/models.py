from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Health(BaseModel):
    status: str
    service: str
    version: str
    api: str
    time: str


class DiagCheck(BaseModel):
    id: str
    ok: bool
    detail: str | None = None


class Compatibility(BaseModel):
    platform: str
    modes: list[str]


class PublicationInfo(BaseModel):
    root_url: str
    reuse_sessions: str
    session_max_age: int


class AdapterDiag(BaseModel):
    status: str
    service: str
    version: str
    api: str
    time: str
    product_license: str
    compatibility: Compatibility
    publication: PublicationInfo
    checks: list[DiagCheck]


class GatewayInfo(BaseModel):
    preset: str
    meta_cache_ttl_seconds: float
    tenant: str
    adapter_host: str
    mcp_http_path: str = "/mcp"
    rate_limit_per_minute: int = 120
    tenants: list[str] = Field(default_factory=lambda: ["default"])


class GatewayDiag(BaseModel):
    status: str
    service: str
    version: str
    api: str
    product_license: str
    gateway: GatewayInfo
    adapter: AdapterDiag | None = None
    checks: list[DiagCheck]


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


class QueryResult(BaseModel):
    content_kind: str = "data"
    columns: list[str]
    rows: list[list[Any]]
    named_query: str | None = None


class ReportResult(BaseModel):
    content_kind: str = "data"
    format: str
    body: Any


class JobAccepted(BaseModel):
    job_id: str
    status: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: Problem | None = None


class WriteResult(BaseModel):
    ref: Ref
    posted: bool | None = None
    warnings: list[str] = Field(default_factory=list)


class DryRunResult(BaseModel):
    confirm_token: str
    preview: dict[str, Any]
    expires_at: str | None = None
    fill_check: list[str] = Field(default_factory=list)
    posting_effects: list[str] = Field(default_factory=list)


class RollbackResult(BaseModel):
    session_id: str
    undone: list[Ref]
