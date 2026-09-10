from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace

from onecmcp.config import Settings

_CAPTURE = False
_TEST_SPANS: list[Any] = []


class MemorySpan:
    def __init__(self, name: str) -> None:
        self.name = name


class MemoryExporter:
    def get_finished_spans(self) -> list[MemorySpan]:
        return list(_TEST_SPANS)

    def clear(self) -> None:
        _TEST_SPANS.clear()


def install_memory_tracer() -> MemoryExporter:
    global _CAPTURE
    _CAPTURE = True
    _TEST_SPANS.clear()
    return MemoryExporter()


def reset_tracing() -> None:
    global _CAPTURE
    _CAPTURE = False
    _TEST_SPANS.clear()


def configure_tracing(settings: Settings) -> None:
    endpoint = (settings.otel_exporter_otlp_endpoint or "").strip()
    if not endpoint:
        return
    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        return
    provider = TracerProvider()
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    except ImportError:
        return
    trace.set_tracer_provider(provider)


@contextmanager
def http_span(method: str, path: str, tenant: str) -> Iterator[None]:
    tracer = trace.get_tracer("onecmcp.gateway")
    with tracer.start_as_current_span("http.request") as span:
        span.set_attribute("http.method", method)
        span.set_attribute("url.path", path)
        span.set_attribute("1cmcp.tenant", tenant)
        if _CAPTURE:
            _TEST_SPANS.append(MemorySpan("http.request"))
        yield
