"""Tests für den Single-Instance-ACK-Handshake (single_instance.py).

Kern-Szenario: Auf dem IPC-Port kann ein beliebiger fremder Dienst lauschen.
Ohne ACK-Handshake würde die zweite Instanz nach Connect+Send kommentarlos
``sys.exit(0)`` laufen — die App wäre wegen eines Fremd-Listeners unstartbar.
"""

import contextlib
import logging
import os
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from single_instance import (
    FOCUS_MESSAGE,
    _notify_existing,
    _notify_existing_with_retries,
    ipc_port_from_config,
    shutdown_ipc,
    start_ipc_server_thread,
    try_acquire_single_instance,
)

logger = logging.getLogger("test_single_instance")


class _ForeignServer:
    """Fremder TCP-Dienst: nimmt Verbindungen an, antwortet aber nie mit ACK."""

    def __init__(self, reply: bytes | None = b"NOPE\n"):
        self._reply = reply
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with contextlib.suppress(OSError), conn:
                conn.recv(64)
                if self._reply:
                    conn.sendall(self._reply)

    def close(self):
        with contextlib.suppress(OSError):
            self.sock.close()
        self._thread.join(timeout=2.0)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_notify_foreign_service_no_ack():
    """Fremddienst antwortet ohne ACK-Token → Notify gilt als fehlgeschlagen."""
    srv = _ForeignServer(reply=b"NOPE\n")
    try:
        assert _notify_existing(srv.port, logger) is False
        assert _notify_existing_with_retries(srv.port, logger, attempts=2, delay_sec=0.01) is False
    finally:
        srv.close()


def test_notify_foreign_service_closes_silently():
    """Fremddienst schließt kommentarlos (recv → b'') → kein ACK."""
    srv = _ForeignServer(reply=None)
    try:
        assert _notify_existing(srv.port, logger) is False
    finally:
        srv.close()


def test_try_acquire_continues_when_port_held_by_foreign_service():
    """Belegter Port ohne ACK ist kein Instanz-Beweis: App startet weiter (kein Exit)."""
    srv = _ForeignServer(reply=b"NOPE\n")
    config = {"single_instance": True, "single_instance_port": srv.port}
    try:
        outcome = try_acquire_single_instance(config, logger)
        assert outcome.should_exit is False
        assert outcome.listen_socket is None  # ohne IPC, aber lauffähig
    finally:
        srv.close()


def test_second_instance_gets_ack_and_primary_raises_window():
    """Echte Bestandsinstanz: ACK kommt an, Fokus-Callback feuert, Exit-Pfad greift."""
    port = _free_port()
    config = {"single_instance": True, "single_instance_port": port}
    assert ipc_port_from_config(config) == port

    primary = try_acquire_single_instance(config, logger)
    assert primary.should_exit is False
    assert primary.listen_socket is not None
    raised = threading.Event()
    try:
        start_ipc_server_thread(
            primary.listen_socket,
            primary.stop_event,
            lambda fn: fn(),  # UI-Thread-Stub: sofort ausführen
            raised.set,
            logger,
        )
        second = try_acquire_single_instance(config, logger)
        assert second.should_exit is True
        assert second.listen_socket is None
        assert raised.wait(2.0)
    finally:
        shutdown_ipc(primary.listen_socket, primary.stop_event)


def test_ipc_thread_survives_schedule_exception():
    """``root.after`` wirft beim Shutdown RuntimeError/TclError — Thread lebt weiter."""
    port = _free_port()
    config = {"single_instance": True, "single_instance_port": port}
    primary = try_acquire_single_instance(config, logger)
    assert primary.listen_socket is not None

    def _schedule_raises(_fn):
        raise RuntimeError("main thread is not in main loop")

    try:
        thread = start_ipc_server_thread(
            primary.listen_socket,
            primary.stop_event,
            _schedule_raises,
            lambda: None,
            logger,
        )
        # Zwei Pings: das ACK muss trotz werfendem Scheduler ankommen und der
        # Thread darf an der Exception nicht sterben.
        for _ in range(2):
            assert _notify_existing(port, logger) is True
        time.sleep(0.1)
        assert thread.is_alive()
    finally:
        shutdown_ipc(primary.listen_socket, primary.stop_event)


def _client_sends_focus_and_reads(port: int) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=2.0) as sock:
        sock.sendall(FOCUS_MESSAGE)
        sock.settimeout(1.0)
        try:
            return sock.recv(64)
        except OSError:
            return b""


def test_server_acks_focus_message():
    """Roh-Protokoll: FOCUS rein → ACK-Token raus."""
    port = _free_port()
    config = {"single_instance": True, "single_instance_port": port}
    primary = try_acquire_single_instance(config, logger)
    assert primary.listen_socket is not None
    try:
        start_ipc_server_thread(
            primary.listen_socket,
            primary.stop_event,
            lambda fn: fn(),
            lambda: None,
            logger,
        )
        assert b"WOTITI_ACK" in _client_sends_focus_and_reads(port)
    finally:
        shutdown_ipc(primary.listen_socket, primary.stop_event)
