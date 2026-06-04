# main.py
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from api.routes import router
from core.logging_config import setup_logging
from core.config import settings
from pywebguard import FastAPIGuard, GuardConfig
from pywebguard.storage.memory import AsyncMemoryStorage
import os
import logging

# Configuración inicial de logging (debe ir antes de cualquier log)
setup_logging()

# ========== OpenTelemetry ==========
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter as HTTPLogExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

def configure_telemetry(app):
    resource = Resource.create(attributes={"service.name": "rag-api"})
    otlp_endpoint = "alloy:4317"   # Alloy recibe OTLP/gRPC

    # ---- Trazas (gRPC a Alloy) ----
    trace_provider = TracerProvider(resource=resource)
    trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)
    FastAPIInstrumentor.instrument_app(app)

    # ---- Logs (gRPC a Alloy) ----
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    log_provider = LoggerProvider(resource=resource)
    log_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
    log_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(log_provider)

    # Handler para logs de Python
    otel_handler = LoggingHandler(level=logging.INFO, logger_provider=log_provider)

    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(otel_handler)
    # Consola opcional
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(console)

    logging.info("Telemetría configurada: logs y trazas -> Alloy (OTLP/gRPC)")


    
# ========== Configuración de seguridad (pywebguard) ==========
security_config = GuardConfig(
    ip_filter={
        "enabled": True,
        "whitelist": [
            "127.0.0.1",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
        ],
        "blacklist": [
            "0.0.0.0/8",
            "169.254.0.0/16",
        ],
    },
    rate_limit={
        "enabled": True,
        "requests_per_minute": 100,
        "burst_size": 20,
        "auto_ban_threshold": 200,
        "auto_ban_duration": 300,
    },
    penetration={
        "enabled": False,
        "detect_sql_injection": True,
        "detect_xss": True,
        "detect_path_traversal": True,
    },
    logging={
        "enabled": True,
        "log_blocked_requests": True,
        "log_rate_limit_exceeded": True,
        "level": "INFO",
    }
)

# ========== Crear la aplicación FastAPI ==========
app = FastAPI(title="RAG Service")

# Inicializar telemetría (después de crear app, antes de los middlewares)
configure_telemetry(app)

# Middleware de seguridad (IP whitelist, rate limiting, etc.)
app.add_middleware(
    FastAPIGuard,
    config=security_config,
    storage=AsyncMemoryStorage()
)

# Middleware de hosts confiables (built-in de FastAPI)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "rag-api",
        "auth-ms",
        "*.internal.local",
    ]
)

# Incluir las rutas de la API
app.include_router(router, prefix="/api/rag")

# ========== Punto de entrada ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )