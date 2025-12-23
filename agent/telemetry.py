"""
Tiny OpenTelemetry helper for Phase 1.
If no OTel exporter is configured the spans become no-ops.
"""
from contextlib import contextmanager
from typing import Iterator

# from opentelemetry import trace

# from livekit.agents.telemetry import tracer

# tracer = trace.get_tracer("livekit-agent")


# @contextmanager
# def start_telemetry_span(name: str) -> Iterator[trace.Span]:
#     with tracer.start_as_current_span(name) as span:
#         yield span

# @contextmanager
# def start_telemetry_span(name: str) -> Iterator[object]:
#     with tracer.start_as_current_span(name) as span:
#         yield span

class _DummySpan:
    def set_attribute(self, _key: str, _value) -> None:
        pass


@contextmanager
def start_telemetry_span(name: str) -> Iterator[_DummySpan]:
    """Yield a dummy span; real OTel can be plugged in later."""
    yield _DummySpan()