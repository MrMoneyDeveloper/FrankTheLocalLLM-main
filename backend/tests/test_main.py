import socket

from ..app.main import port_available


def test_port_available_free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        host, port = s.getsockname()
    assert port_available(host, port)


def test_port_available_busy_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    try:
        assert not port_available(host, port)
    finally:
        sock.close()
