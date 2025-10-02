from __future__ import annotations

import asyncio
import json
import signal
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from prometheus_client import start_http_server
from src.core.config import settings
from src.core.logger import get_logger
from src.infrastructure.kafka.topic_waiter import ensure_topics_available
from src.services.processor import process_batches

from shared.logging.json import configure_logging as shared_configure_logging

logger = get_logger("app")


async def _run() -> None:
    shared_configure_logging(
        service=settings.otel_service_name,
        level=settings.app_log_level,
        environment=settings.app_environment,
        redaction_patterns=settings.app_log_redaction_patterns,
    )
    logger.info("storage_service_starting")

    metrics_port = getattr(settings, "metrics_port", 8001)
    start_http_server(metrics_port)
    logger.info("metrics_listening", extra={"port": metrics_port})

    logger.info("waiting_for_topics", extra={"topics": settings.kafka_consumer_topics})
    ensure_topics_available(settings.kafka_consumer_topics)

    # Start auxiliary health server (simple stdlib) for /healthz
    def _health_handler_factory():
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path != "/healthz":
                    self.send_response(404)
                    self.end_headers()
                    return
                payload = {"status": "ok", "service": settings.otel_service_name}
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return  # suppress default stdout noise

        return Handler

    def _start_health_server():
        try:
            server = HTTPServer(
                ("0.0.0.0", settings.health_port), _health_handler_factory()
            )
            logger.info("health_server_listening", extra={"port": settings.health_port})
            server.serve_forever()
        except Exception as exc:  # noqa: BLE001
            logger.exception("health_server_error", extra={"error": str(exc)})

    threading.Thread(target=_start_health_server, name="healthz", daemon=True).start()

    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    # Support double signal: first gentle, second immediate
    state = {"signalled": False}

    def _on_signal(signum, frame):  # noqa: D401
        if not state["signalled"]:
            logger.info("signal_received", extra={"signal": signum, "action": "drain"})
            loop.call_soon_threadsafe(shutdown_event.set)
            state["signalled"] = True
        else:
            logger.warning(
                "second_signal_exit", extra={"signal": signum, "action": "cancel"}
            )
            for task in asyncio.all_tasks(loop):
                task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _on_signal)
        except Exception:  # noqa: BLE001
            logger.debug("signal_handler_install_failed", extra={"signal": sig})

    try:
        await process_batches(shutdown_event)
    except asyncio.CancelledError:  # pragma: no cover
        logger.info("app_cancelled")
    finally:
        logger.info("storage_service_stopping")


def main() -> None:  # pragma: no cover - small wrapper
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:  # noqa: PIE786
        logger.info("keyboard_interrupt_shutdown")
    except Exception:  # noqa: BLE001
        logger.exception("fatal_error_main")


if __name__ == "__main__":  # pragma: no cover
    main()
