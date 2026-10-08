import logging
import sys

import structlog

from config.config import settings


class HealthCheckFilter(logging.Filter):
    """Filter to suppress health check endpoint logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to suppress health check logs."""
        return "/health" not in record.getMessage()


def get_log_level() -> int:
    """Convert string log level to logging constant."""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(settings.log_level.upper(), logging.INFO)


def configure_logging() -> None:
    """
    Configure structlog for the application.

    - Development: Colorful, human-readable console output
    - Production: JSON output for log aggregation

    All logs (including uvicorn) use the same format.
    """
    log_level = get_log_level()

    # Processors shared between dev and prod
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.dev:
        final_processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        final_processor = structlog.processors.JSONRenderer()

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            final_processor,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure root logger with structlog formatting
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    # Create handler that formats ALL logs through structlog
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # ProcessorFormatter routes stdlib logs through structlog processors
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=final_processor,
            foreign_pre_chain=shared_processors,
        )
    )

    root_logger.addHandler(handler)

    # Configure uvicorn loggers to use our formatting
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True  # Use root logger's handler

    # Filter out noisy health check logs from uvicorn access
    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

    # Quiet down noisy third-party loggers
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance."""
    return structlog.get_logger(name)
