from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_tracing() -> TracerProvider:
    """Configures Opentelemtry for the application"""
    provider = TracerProvider()

    otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4317")

    # Use a BatchSpanProcessor to send spans in batches
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    trace.set_tracer_provider(provider)

    # Instrument logging to include trace context
    LoggingInstrumentor().instrument(set_logging_format=True)

    return provider
