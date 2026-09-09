from __future__ import annotations

from onecmcp.models import (
    Health,
    JobAccepted,
    JobStatus,
    MetaField,
    MetaObject,
    MetaSummary,
    Problem,
    QueryResult,
    Ref,
    ReportResult,
)


def test_contract_models() -> None:
    health = Health(status="ok", service="1cmcp", version="0.1.0", api="v1", time="2026-09-09T17:00:00Z")
    assert health.service == "1cmcp"

    problem = Problem(type="https://1cmcp.dev/errors/x", title="X", status=400, code="x")
    assert problem.detail is None

    ref = Ref(ref="Catalog.DemoCounterparties", id="8a996f93-36c8-4bcf-b707-f75b8b4bc5e3", presentation="ООО")
    assert ref.presentation == "ООО"

    summary = MetaSummary(kind="catalog", name="DemoCounterparties")
    field = MetaField(name="INN", type="string")
    obj = MetaObject(kind="catalog", name="DemoCounterparties", fields=[field], synonym=summary.synonym)
    assert obj.fields[0].name == "INN"
    assert obj.json_schema is None

    query = QueryResult(columns=["Value"], rows=[[1]])
    assert query.content_kind == "data"
    accepted = JobAccepted(job_id="00000000-0000-0000-0000-000000000000", status="queued")
    assert accepted.status == "queued"
    status = JobStatus(job_id=accepted.job_id, status="succeeded", result={"ok": True})
    assert status.result == {"ok": True}
    rendered = ReportResult(format="csv", body="a,b\n")
    assert rendered.content_kind == "data"
