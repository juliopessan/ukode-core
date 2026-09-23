"""Configuração mínima de OpenTelemetry. Sem exportador configurado, os spans
ficam no processo (útil em dev); com `OTEL_EXPORTER_OTLP_ENDPOINT`, exporta
para o coletor do lab ou do cliente (Langfuse, Grafana Tempo, etc.)."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_configured = False


def configure_telemetry(service_name: str = "ukode-core", otlp_endpoint: str = "") -> None:
    global _configured
    if _configured:
        return

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))

    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _configured = True


def get_tracer(name: str = "ukode_core"):
    return trace.get_tracer(name)
