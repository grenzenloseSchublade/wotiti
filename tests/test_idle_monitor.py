"""Tests für die plattformübergreifende Idle-Erkennung (src/idle_monitor.py).

Alle OS-Abhängigkeiten (subprocess, ctypes.windll, X11) werden gemonkeypatcht —
die Tests laufen dadurch deterministisch auf jeder Plattform.
"""

import ctypes
import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import idle_monitor


class _Completed:
    """Minimale Nachbildung eines subprocess.CompletedProcess."""

    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout


# --- xprintidle-Fallback: Parsing der Millisekunden-Ausgabe ----------------


def test_xprintidle_parses_millis_to_seconds(monkeypatch):
    monkeypatch.setattr(idle_monitor, "_xprintidle_path", "/usr/bin/xprintidle")
    monkeypatch.setattr(idle_monitor.subprocess, "run", lambda *a, **k: _Completed(0, "1500\n"))
    assert idle_monitor._idle_seconds_xprintidle() == 1.5


def test_xprintidle_garbage_output_returns_none(monkeypatch):
    monkeypatch.setattr(idle_monitor, "_xprintidle_path", "/usr/bin/xprintidle")
    monkeypatch.setattr(idle_monitor.subprocess, "run", lambda *a, **k: _Completed(0, "kein-zahlwert\n"))
    assert idle_monitor._idle_seconds_xprintidle() is None


def test_xprintidle_nonzero_returncode_returns_none(monkeypatch):
    monkeypatch.setattr(idle_monitor, "_xprintidle_path", "/usr/bin/xprintidle")
    monkeypatch.setattr(idle_monitor.subprocess, "run", lambda *a, **k: _Completed(1, ""))
    assert idle_monitor._idle_seconds_xprintidle() is None


def test_xprintidle_missing_binary_skips_subprocess(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("subprocess.run darf ohne Binary nicht aufgerufen werden")

    monkeypatch.setattr(idle_monitor, "_xprintidle_path", None)
    monkeypatch.setattr(idle_monitor.subprocess, "run", _boom)
    assert idle_monitor._idle_seconds_xprintidle() is None


def test_xprintidle_oserror_returns_none(monkeypatch):
    def _raise(*a, **k):
        raise OSError("exec fehlgeschlagen")

    monkeypatch.setattr(idle_monitor, "_xprintidle_path", "/usr/bin/xprintidle")
    monkeypatch.setattr(idle_monitor.subprocess, "run", _raise)
    assert idle_monitor._idle_seconds_xprintidle() is None


# --- Windows: GetTickCount-Überlauf (~49,7 Tage) ----------------------------


def _fake_windll(last_input_tick, current_tick):
    class _User32:
        @staticmethod
        def GetLastInputInfo(ref):
            ref._obj.dwTime = last_input_tick
            return 1

    class _Kernel32:
        @staticmethod
        def GetTickCount():
            return current_tick

    return types.SimpleNamespace(user32=_User32(), kernel32=_Kernel32())


def test_windows_idle_normal_case(monkeypatch):
    monkeypatch.setattr(ctypes, "windll", _fake_windll(1_000, 6_000), raising=False)
    assert idle_monitor._idle_seconds_windows() == 5.0


def test_windows_tick_overflow_clamps_to_zero(monkeypatch):
    # Nach dem 32-Bit-Überlauf liegt der aktuelle Tick UNTER dem letzten
    # Input-Tick → konservativ 0.0 statt riesiger negativer Idle-Zeit.
    monkeypatch.setattr(ctypes, "windll", _fake_windll(4_000_000_000, 100), raising=False)
    assert idle_monitor._idle_seconds_windows() == 0.0


def test_windows_api_failure_returns_none(monkeypatch):
    class _User32:
        @staticmethod
        def GetLastInputInfo(ref):
            return 0  # API-Fehlschlag

    windll = types.SimpleNamespace(user32=_User32(), kernel32=None)
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)
    assert idle_monitor._idle_seconds_windows() is None


# --- Fallback-Kette in get_idle_seconds -------------------------------------


def test_linux_prefers_x11(monkeypatch):
    def _boom():
        raise AssertionError("xprintidle darf nicht aufgerufen werden, wenn X11 liefert")

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(idle_monitor, "_idle_seconds_x11", lambda: 7.0)
    monkeypatch.setattr(idle_monitor, "_idle_seconds_xprintidle", _boom)
    assert idle_monitor.get_idle_seconds() == 7.0


def test_linux_falls_back_to_xprintidle(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(idle_monitor, "_idle_seconds_x11", lambda: None)
    monkeypatch.setattr(idle_monitor, "_idle_seconds_xprintidle", lambda: 2.5)
    assert idle_monitor.get_idle_seconds() == 2.5


def test_linux_all_backends_unavailable_returns_none(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(idle_monitor, "_idle_seconds_x11", lambda: None)
    monkeypatch.setattr(idle_monitor, "_idle_seconds_xprintidle", lambda: None)
    assert idle_monitor.get_idle_seconds() is None


def test_windows_platform_routes_to_windows_backend(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(idle_monitor, "_idle_seconds_windows", lambda: 3.0)
    assert idle_monitor.get_idle_seconds() == 3.0


def test_unknown_platform_returns_none(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert idle_monitor.get_idle_seconds() is None
