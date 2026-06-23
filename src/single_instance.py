"""
Single-instance IPC for the WoTITI tkinter GUI only.

A dedicated localhost TCP port carries a short magic payload so a second process
can ask the first to raise the main (or mini) window. This is not related to the
Dash dashboard or browser.

On Windows, a named mutex (CreateMutexW) provides a hard guarantee that only one
process runs; the socket is used to raise the existing window.
"""

from __future__ import annotations

import contextlib
import errno
import logging
import socket
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Magic line sent by a second process; first process raises the main window only.
FOCUS_MESSAGE = b"WOTITI_FOCUS\n"
FOCUS_PREFIX = b"WOTITI_FOCUS"

# Windows named mutex — kernel-level single instance (Local namespace).
_WIN_MUTEX_NAME = "Local\\WoTitiSingleInstance"
_win_mutex_handle: int | None = None


def ipc_port_from_config(config: dict) -> int:
    """Port used only for single-instance signalling (not the dashboard port)."""
    derived = int(config.get("dashboard_port", 8052)) + 9731
    explicit = config.get("single_instance_port")
    if explicit is not None:
        # single_instance_port ist ein optionaler Hand-Edit-Override und nicht
        # Teil von DEFAULT_CONFIG/_validate_config. Ein Nicht-Zahl-Wert darf den
        # Start nicht crashen — bei ungültiger Eingabe auf den abgeleiteten Port
        # zurückfallen.
        try:
            p = int(explicit)
        except (TypeError, ValueError):
            p = derived
    else:
        p = derived
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


def _notify_existing_with_retries(
    port: int,
    logger: logging.Logger,
    attempts: int = 12,
    delay_sec: float = 0.15,
) -> bool:
    """Try to reach the primary instance; return True if any attempt succeeded."""
    for i in range(attempts):
        try:
            _notify_existing(port, logger)
            return True
        except OSError as e:
            logger.debug("IPC notify attempt %s/%s: %s", i + 1, attempts, e)
            if i + 1 < attempts:
                time.sleep(delay_sec)
    return False


def windows_single_instance_mutex_guard_or_exit(config: dict, logger: logging.Logger) -> None:
    """
    Windows only: if another WoTITI process already holds the mutex, notify via TCP
    and exit. Otherwise acquire the mutex for the lifetime of this process.

    Call after logging is configured, before ``tk.Tk()`` and before socket bind.
    """
    global _win_mutex_handle

    if not sys.platform.startswith("win"):
        return
    if not config.get("single_instance", True):
        return

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    CreateMutexW = kernel32.CreateMutexW
    CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    CreateMutexW.restype = wintypes.HANDLE

    ERROR_ALREADY_EXISTS = 183
    mutex = CreateMutexW(None, False, _WIN_MUTEX_NAME)
    last_err = kernel32.GetLastError()

    if not mutex:
        logger.warning("CreateMutexW failed; continuing without Windows mutex guard.")
        return

    if last_err == ERROR_ALREADY_EXISTS:
        port = ipc_port_from_config(config)
        if _notify_existing_with_retries(port, logger):
            logger.info("WoTITI läuft bereits (Mutex) — Hauptfenster in den Vordergrund angefordert.")
        else:
            logger.warning(
                "WoTITI-Mutex zeigt zweite Instanz, IPC auf Port %s nicht erreichbar — beende ohne zweites Fenster.",
                port,
            )
        kernel32.CloseHandle(mutex)
        sys.exit(0)

    _win_mutex_handle = int(mutex)


def release_windows_singleton_mutex() -> None:
    """Release the Windows mutex handle if held (call on shutdown)."""
    global _win_mutex_handle

    if _win_mutex_handle is None or not sys.platform.startswith("win"):
        return
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    with contextlib.suppress(Exception):
        kernel32.CloseHandle(wintypes.HANDLE(_win_mutex_handle))
    _win_mutex_handle = None


def try_acquire_single_instance(config: dict, logger: logging.Logger) -> SingleInstanceOutcome:
    """
    Before ``tk.Tk()``:
    - Bind localhost IPC port -> we are primary; return listen socket + stop_event.
    - Port busy -> notify primary (with retries); ``should_exit=True`` or ``sys.exit(0)``.
    """
    if not config.get("single_instance", True):
        return SingleInstanceOutcome(False, None, 0, None)

    port = ipc_port_from_config(config)
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # SO_REUSEADDR on Windows can weaken exclusivity for listeners; use only on non-Windows.
    if not sys.platform.startswith("win"):
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listen_sock.bind(("127.0.0.1", port))
    except OSError as e:
        in_use = e.errno == errno.EADDRINUSE or getattr(e, "winerror", None) == 10048
        if not in_use:
            listen_sock.close()
            raise
        listen_sock.close()
        if _notify_existing_with_retries(port, logger):
            logger.info("WoTITI läuft bereits — Hauptfenster in den Vordergrund angefordert.")
            return SingleInstanceOutcome(True, None, port, None)
        logger.warning(
            "Single-Instance-Port %s belegt, IPC nicht erreichbar — beende ohne zweites Fenster.",
            port,
        )
        sys.exit(0)

    listen_sock.listen(128)
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
    release_windows_singleton_mutex()
