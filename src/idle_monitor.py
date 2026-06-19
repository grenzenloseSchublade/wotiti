"""Plattformübergreifende Erkennung der OS-weiten Benutzer-Inaktivität (Idle-Zeit).

Die einzige öffentliche Funktion ist :func:`get_idle_seconds`. Sie liefert die
Zeit in Sekunden seit der letzten Maus-/Tastatureingabe — systemweit, nicht nur
innerhalb des WoTiTi-Fensters. Ist auf der aktuellen Plattform keine Erkennung
möglich, wird ``None`` zurückgegeben (der Aufrufer behandelt das als
"Idle unbekannt" und unternimmt nichts).

Unterstützung:
- Windows: ``GetLastInputInfo`` / ``GetTickCount`` (user32/kernel32).
- Linux/X11: ``XScreenSaverQueryInfo`` (libXss); Fallback ``xprintidle``.
- Sonst / Wayland ohne XWayland: nicht verfügbar → ``None``.
"""

from __future__ import annotations

import ctypes
import logging
import shutil
import subprocess
import sys

logger = logging.getLogger(__name__)

# Einmalige Warnung, falls keine Erkennung verfügbar ist (verhindert Log-Spam).
_warned_unavailable = False


def _warn_once(msg: str) -> None:
    global _warned_unavailable
    if not _warned_unavailable:
        logger.warning(msg)
        _warned_unavailable = True


def _idle_seconds_windows() -> float | None:
    """Idle-Zeit unter Windows via GetLastInputInfo."""

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    try:
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):  # type: ignore[attr-defined]
            return None
        tick = ctypes.windll.kernel32.GetTickCount()  # type: ignore[attr-defined]
        # GetTickCount läuft nach ~49.7 Tagen über; bei Überlauf konservativ 0.
        millis = tick - info.dwTime
        if millis < 0:
            return 0.0
        return millis / 1000.0
    except Exception as e:  # noqa: BLE001
        _warn_once(f"Idle-Erkennung (Windows) nicht verfügbar: {e}")
        return None


# X11-Strukturen für XScreenSaverQueryInfo (einmalig definiert).
class _XScreenSaverInfo(ctypes.Structure):
    _fields_ = [
        ("window", ctypes.c_ulong),
        ("state", ctypes.c_int),
        ("kind", ctypes.c_int),
        ("since", ctypes.c_ulong),
        ("idle", ctypes.c_ulong),  # ms seit letzter Eingabe
        ("event_mask", ctypes.c_ulong),
    ]


_xss_state: dict | None = None


def _load_x11():
    """Lädt libX11/libXss einmalig; gibt ein Cache-Dict oder ``None`` zurück."""
    global _xss_state
    if _xss_state is not None:
        return _xss_state or None
    try:
        xlib = ctypes.CDLL("libX11.so.6")
        xss = ctypes.CDLL("libXss.so.1")
    except OSError:
        _xss_state = {}  # markiert "nicht verfügbar"
        return None

    xlib.XOpenDisplay.restype = ctypes.c_void_p
    xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
    xlib.XDefaultRootWindow.restype = ctypes.c_ulong
    xlib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(_XScreenSaverInfo)
    xss.XScreenSaverQueryInfo.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_XScreenSaverInfo)]

    display = xlib.XOpenDisplay(None)
    if not display:
        _xss_state = {}
        return None
    _xss_state = {
        "xlib": xlib,
        "xss": xss,
        "display": display,
        "root": xlib.XDefaultRootWindow(display),
        "info": xss.XScreenSaverAllocInfo(),
    }
    return _xss_state


def _idle_seconds_x11() -> float | None:
    """Idle-Zeit unter X11 via XScreenSaverQueryInfo."""
    state = _load_x11()
    if not state:
        return None
    try:
        if not state["xss"].XScreenSaverQueryInfo(state["display"], state["root"], state["info"]):
            return None
        return float(state["info"].contents.idle) / 1000.0
    except Exception as e:  # noqa: BLE001
        _warn_once(f"Idle-Erkennung (X11) nicht verfügbar: {e}")
        return None


_xprintidle_path = shutil.which("xprintidle")


def _idle_seconds_xprintidle() -> float | None:
    """Fallback: idle-Zeit über das Tool ``xprintidle`` (ms auf stdout)."""
    if not _xprintidle_path:
        return None
    try:
        out = subprocess.run(  # noqa: S603
            [_xprintidle_path], capture_output=True, text=True, timeout=2
        )
        if out.returncode != 0:
            return None
        return float(out.stdout.strip()) / 1000.0
    except (ValueError, OSError, subprocess.SubprocessError):
        return None


def get_idle_seconds() -> float | None:
    """Sekunden seit der letzten systemweiten Eingabe, oder ``None`` falls unbekannt."""
    if sys.platform.startswith("win"):
        return _idle_seconds_windows()
    if sys.platform.startswith("linux"):
        secs = _idle_seconds_x11()
        if secs is not None:
            return secs
        secs = _idle_seconds_xprintidle()
        if secs is not None:
            return secs
        _warn_once(
            "Idle-Erkennung nicht verfügbar (kein X11/XScreenSaver, kein xprintidle) "
            "— Auto-Stop bei Inaktivität ist deaktiviert."
        )
        return None
    # macOS o. Ä. werden derzeit nicht als Build-Ziel unterstützt.
    _warn_once(f"Idle-Erkennung für Plattform '{sys.platform}' nicht implementiert.")
    return None
