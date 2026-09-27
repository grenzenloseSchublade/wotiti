"""Tests für den HTTP-basierten Dashboard-Check (app._dashboard_http_ok).

Der frühere nackte ``connect_ex`` wertete jeden Lauscher auf dem Port als
laufendes Dashboard — inklusive fremder Dienste. Erst die erwartete Antwort
des Health-Endpunkts zählt.
"""

import contextlib
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app import DASHBOARD_HEALTH_BODY, DASHBOARD_HEALTH_PATH, _dashboard_http_ok


def _make_handler(health_body: bytes):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == DASHBOARD_HEALTH_PATH:
                body = health_body
                self.send_response(200)
            else:
                body = b"not found"
                self.send_response(404)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    return _Handler


@contextlib.contextmanager
def _http_server(health_body: bytes):
    server = HTTPServer(("127.0.0.1", 0), _make_handler(health_body))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


def test_http_ok_against_real_health_endpoint():
    with _http_server(DASHBOARD_HEALTH_BODY) as port:
        assert _dashboard_http_ok(port) is True


def test_http_ok_rejects_wrong_body():
    """HTTP-Dienst mit 200, aber fremdem Inhalt → kein Dashboard."""
    with _http_server(b"welcome to something else") as port:
        assert _dashboard_http_ok(port) is False


def test_http_ok_rejects_closed_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]
    assert _dashboard_http_ok(free_port) is False


def test_http_ok_rejects_silent_tcp_listener():
    """Nackter TCP-Lauscher ohne HTTP-Antwort (der alte False-Positive-Fall)."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    try:
        assert _dashboard_http_ok(listener.getsockname()[1], timeout=0.3) is False
    finally:
        listener.close()
