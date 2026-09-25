"""OpenTelemetry instrumentation — optional, enabled when OTEL_EXPORTER_OTLP_ENDPOINT is set."""
from __future__ import annotations

import os

import structlog

logger = structlog.get_logger(__name__)


def setup_tracing(app) -> None:
    """Attach OpenTelemetry instrumentation to the FastAPI app if configured."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if not endpoint:
        logger.info("otel_tracing_disabled", reason="OTEL_EXPORTER_OTLP_ENDPOINT not set")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        service_name = os.environ.get("OTEL_SERVICE_NAME", "release-doctor")
        provider = TracerProvider()
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app)
        logger.info("otel_tracing_enabled", endpoint=endpoint, service=service_name)

    except ImportError:
        logger.warning("otel_not_installed", hint="pip install opentelemetry-sdk opentelemetry-exporter-otlp opentelemetry-instrumentation-fastapi")
    except Exception as exc:
        logger.error("otel_setup_failed", error=str(exc))
