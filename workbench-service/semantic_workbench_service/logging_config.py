import logging
import re
from time import perf_counter
from typing import Awaitable, Callable

import asgi_correlation_id
from fastapi import Request, Response
from pydantic_settings import BaseSettings
from pythonjsonlogger import json as jsonlogger
from rich.logging import RichHandler


class LoggingSettings(BaseSettings):
    json_format: bool = False
    log_level: str = "INFO"


class JSONHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__()
        self.setFormatter(
            jsonlogger.JsonFormatter(
                "%(filename)s %(name)s %(lineno)s %(levelname)s %(correlation_id)s %(message)s %(taskName)s"
                " %(process)d",
                timestamp=True,
            )
        )


class DebugLevelForNoisyLogFilter(logging.Filter):
    """Lowers logs for specific routes to DEBUG level."""

    def __init__(self, log_level: int, *names_and_patterns: tuple[str, re.Pattern]):
        self._log_level = log_level
        self._names_and_patterns = names_and_patterns

    def filter(self, record: logging.LogRecord) -> bool:
        if not any(
            record.name == name and pattern.search(record.getMessage()) for name, pattern in self._names_and_patterns
        ):
            return True

        record.levelname = logging.getLevelName(logging.DEBUG)
        record.levelno = logging.DEBUG

        return self._log_level <= record.levelno


def config(settings: LoggingSettings):
    log_level = logging.getLevelNamesMapping()[settings.log_level.upper()]

    handler = RichHandler(rich_tracebacks=True)
    if settings.json_format:
        handler = JSONHandler()

    handler.addFilter(
        DebugLevelForNoisyLogFilter(
            log_level,
            # noisy assistant-service pings
            ("uvicorn.access", re.compile(r"PUT /assistant-service-registrations/[^\s]+ HTTP")),
        )
    )
    handler.addFilter(asgi_correlation_id.CorrelationIdFilter(uuid_length=8, default_value="-"))

    logging.basicConfig(
        level=log_level,
        format="%(name)35s [%(correlation_id)s] %(message)s",
        datefmt="[%X]",
        handlers=[handler],
    )


def log_request_middleware(
    logger: logging.Logger | None = None,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    access_logger = logger or logging.getLogger("access_log")

    async def middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """
        This middleware will log all requests and their processing time.
        E.g. log:
        0.0.0.0:1234 - "GET /ping HTTP/1.1" 200 OK 1.00ms 0b
        """
        url = f"{request.url.path}?{request.query_params}" if request.query_params else request.url.path
        start_time = perf_counter()
        response = await call_next(request)
        process_time = (perf_counter() - start_time) * 1000
        formatted_process_time = "{0:.2f}".format(process_time)
        host = getattr(getattr(request, "client", None), "host", None)
        port = getattr(getattr(request, "client", None), "port", None)
        http_version = f"HTTP/{request.scope.get('http_version', '1.1')}"
        content_length = response.headers.get("content-length", 0)
        access_logger.info(
            f'{host}:{port} - "{request.method} {url} {http_version}" {response.status_code} {formatted_process_time}ms {content_length}b',
        )
        return response

    return middleware
