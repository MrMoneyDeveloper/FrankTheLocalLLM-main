import logging
import socket
import sys

from uvicorn import run
from . import app, settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def port_available(host: str, port: int) -> bool:
    """Return True if the given host/port can be bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError as exc:
            logger.error("Cannot bind to %s:%s - %s", host, port, exc)
            return False
        logger.debug("Port %s on %s is free", port, host)
        return True

if __name__ == "__main__":
    start_port = port = settings.port
    logger.info(
        "Starting %s on %s:%s", settings.app_name, settings.host, start_port
    )
    if not port_available(settings.host, port):
        while not port_available(settings.host, port):
            port += 1
            if port - start_port > 50:
                logger.error(
                    "Port %s is busy and no free ports found after %s attempts.",
                    start_port,
                    port - start_port,
                )
                sys.exit(1)
        logger.warning("Port %s busy, switching to %s", start_port, port)

    logger.info(
        "%s bound to %s:%s", settings.app_name, settings.host, port
    )

    run(
        "backend.app:app",
        host=settings.host,
        port=port,
        reload=settings.debug,
    )
