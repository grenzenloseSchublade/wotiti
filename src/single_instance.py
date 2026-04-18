"""
Single-instance IPC for the WoTITI tkinter GUI only.

A dedicated localhost TCP port carries a short magic payload so a second process
can ask the first to raise the main (or mini) window. This is not related to the
Dash dashboard or browser.
"""

from __future__ import annotations

import contextlib
import errno
import logging
import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Magic line sent by a second process; first process raises the main window only.
FOCUS_MESSAGE = b"WOTITI_FOCUS\n"
FOCUS_PREFIX = b"WOTITI_FOCUS"


def ipc_port_from_config(config: dict) -> int:
    """Port used only for single-instance signalling (not the dashboard port)."""
    explicit = config.get("single_instance_port")
    if explicit is not None:
        p = int(explicit)
    else:
        p = int(config.get("dashboard_port", 8052)) + 9731
    return max(1024, min(65535, p))


@dataclass
class SingleInstanceOutcome:
    """If ``should_exit`` is True, the caller must ``sys.exit(0)`` before creating ``tk.Tk``."""

    should_exit: bool
    listen_socket: socket.socket | None
    port: int
    stop_event: threading.Event | None


def _notify_existing(port: int, logger: logging.Logger) -> None:
    with socket.create_connection(("127.0.0.1", port), timeout=2.0) as sock:
        sock.sendall(FOCUS_MESSAGE)


def try_acquire_single_instance(config: dict, logger: logging.Logger) -> SingleInstanceOutcome:
    """
    Before ``tk.Tk()``:
    - Bind localhost IPC port -> we are primary; return listen socket + stop_event.
    - Port busy -> try to notify primary and return ``should_exit=True``.
    - Port busy but notify fails -> log warning and run without single-instance (return no socket).
    """
    if not config.get("single_instance", True):
        return SingleInstanceOutcome(False, None, 0, None)

    port = ipc_port_from_config(config)
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listen_sock.bind(("127.0.0.1", port))
    except OSError as e:
        in_use = e.errno == errno.EADDRINUSE or getattr(e, "winerror", None) == 10048
        if not in_use:
            listen_sock.close()
            raise
        listen_sock.close()
        try:
            _notify_existing(port, logger)
            logger.info("WoTITI läuft bereits — Hauptfenster in den Vordergrund angefordert.")
            return SingleInstanceOutcome(True, None, port, None)
        except OSError:
            logger.warning(
                "Single-Instance-Port %s ist belegt, aber keine WoTITI-Instanz hat geantwortet — "
                "Start ohne Single-Instance-Schutz.",
                port,
            )
            return SingleInstanceOutcome(False, None, port, None)

    listen_sock.listen(1)
    stop_event = threading.Event()
    return SingleInstanceOutcome(False, listen_sock, port, stop_event)


def start_ipc_server_thread(
    listen_sock: socket.socket,
    stop_event: threading.Event,
    schedule_on_ui_thread: Callable[[Callable[[], None]], Any],
    on_raise: Callable[[], None],
    logger: logging.Logger,
) -> threading.Thread:
    """Run accept loop in a daemon thread; *on_raise* runs on the UI thread."""

    def _run() -> None:
        listen_sock.settimeout(0.4)
        while not stop_event.is_set():
            try:
                conn, _ = listen_sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            try:
                with conn:
                    data = conn.recv(64)
                    if FOCUS_PREFIX in data:

                        def _do() -> None:
                            try:
                                on_raise()
                            except Exception as ex:
                                logger.warning("raise_main_window callback failed: %s", ex)

                        schedule_on_ui_thread(_do)
            except OSError as e:
                logger.debug("IPC recv: %s", e)

    t = threading.Thread(target=_run, name="wotiti-ipc", daemon=True)
    t.start()
    return t


def shutdown_ipc(listen_sock: socket.socket | None, stop_event: threading.Event | None) -> None:
    if stop_event:
        stop_event.set()
    if listen_sock:
        with contextlib.suppress(OSError):
            listen_sock.close()
