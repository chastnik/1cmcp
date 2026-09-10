from __future__ import annotations

from pathlib import Path

from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "openapi.yaml"


def test_openapi_is_valid_31() -> None:
    spec, _ = read_from_filename(str(SPEC))
    validate(spec)


def test_openapi_covers_v1_surface() -> None:
    spec, _ = read_from_filename(str(SPEC))
    paths = spec["paths"]
    required = {
        "/v1/health",
        "/v1/meta",
        "/v1/meta/search",
        "/v1/meta/{kind}/{name}",
        "/v1/data/{kind}/{name}",
        "/v1/data/{kind}/{name}/{id}",
        "/v1/data/{kind}/{name}/dry-run",
        "/v1/data/{kind}/{name}/{id}/post",
        "/v1/query",
        "/v1/report",
        "/v1/action",
        "/v1/job",
        "/v1/job/{id}",
        "/v1/session/rollback",
        "/v1/diag",
        "/guide",
    }
    assert required <= set(paths)
    assert spec["openapi"].startswith("3.1")
    assert "Ref" in spec["components"]["schemas"]
    assert spec["components"]["schemas"]["Ref"]["required"] == ["ref", "id"]
