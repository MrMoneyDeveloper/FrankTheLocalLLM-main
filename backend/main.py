"""Entry point for launching the full FastAPI application.

This module simply exposes the application defined in ``app`` and binds it to
an available port.  Previously this file constructed a bare ``FastAPI``
instance with a single ``/`` route, which meant running ``python main.py`` did
not expose any of the routers described in ``agents.md`` such as the status
endpoint.

Importing the application from :mod:`app` ensures the CLI entry point mirrors
the behaviour of the package and keeps the executable aligned with the
AGENTS.md specification.
"""

import socket

import uvicorn

from app import app  # Import the fully configured FastAPI app

def get_free_port() -> int:
    """Return an available port bound to localhost."""

    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]

if __name__ == "__main__":
    port = get_free_port()
    print(port, flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port)
