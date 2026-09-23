"""Tests für Wochenend-/Feiertags-Helfer in utils.py."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import utils
from utils import is_holiday, is_non_workday, is_weekend


def test_is_weekend_saturday_sunday():
    assert is_weekend(date(2024, 1, 6)) is True  # Samstag
    assert is_weekend(date(2024, 1, 7)) is True  # Sonntag
    assert is_weekend(date(2024, 1, 8)) is False  # Montag


def test_is_holiday_de_unification_day():
    # Tag der Deutschen Einheit
    assert is_holiday(date(2024, 10, 3), country="DE", subdiv="") is True


def test_is_holiday_subdiv_fronleichnam_bw():
    # Fronleichnam 2024 in Baden-Württemberg.
    assert is_holiday(date(2024, 5, 30), country="DE", subdiv="BW") is True
    # Aber nicht in Hamburg (kein gesetzlicher Feiertag).
    assert is_holiday(date(2024, 5, 30), country="DE", subdiv="HH") is False


def test_is_non_workday_combinations():
    sat = date(2024, 1, 6)
    mon = date(2024, 1, 8)
    unification = date(2024, 10, 3)
    # Mit Feiertagen
    assert is_non_workday(sat, country="DE", subdiv="", include_holidays=True) is True
    assert is_non_workday(unification, country="DE", subdiv="", include_holidays=True) is True
    assert is_non_workday(mon, country="DE", subdiv="", include_holidays=True) is False
    # Ohne Feiertage
    assert is_non_workday(unification, country="DE", subdiv="", include_holidays=False) is False


def test_holidays_import_failure_fallback(monkeypatch):
    """Bei fehlendem holidays-Modul soll is_holiday False zurückgeben."""
    # Cache leeren, sonst greift Memoization.
    utils._holiday_set_cached.cache_clear()
    monkeypatch.setattr(utils, "_try_import_holidays", lambda: None)
    assert is_holiday(date(2024, 10, 3), country="DE", subdiv="") is False
    utils._holiday_set_cached.cache_clear()


def test_clamp_note_limits_to_44_words():
    """clamp_note begrenzt auf 44 Wörter gesamt und kollabiert Whitespace je Zeile."""
    from utils import clamp_note

    words = [f"w{i}" for i in range(60)]
    out = clamp_note(" ".join(words))
    assert len(out.split()) == 44
    assert out.split() == words[:44]
    # Zeilenumbrüche bleiben erhalten; Tab/Mehrfach-Spaces kollabieren je Zeile.
    assert clamp_note("a\n  b\t c") == "a\nb c"
    assert clamp_note("") == ""


def test_clamp_note_preserves_newlines_and_caps_lines():
    """clamp_note erhält Umbrüche, trimmt Randzeilen und cappt auf 6 Zeilen."""
    from utils import clamp_note

    # Leere Zeilen am Rand entfallen, innere bleiben.
    assert clamp_note("\n erste  Zeile \n\n zweite \n") == "erste Zeile\n\nzweite"
    # Mehr als 6 Zeilen werden abgeschnitten.
    many = "\n".join(f"z{i}" for i in range(10))
    assert clamp_note(many) == "\n".join(f"z{i}" for i in range(6))
    # Wort-Limit gilt über alle Zeilen hinweg.
    two_lines = " ".join(f"a{i}" for i in range(30)) + "\n" + " ".join(f"b{i}" for i in range(30))
    out = clamp_note(two_lines)
    assert len(out.split()) == 44
    assert out.splitlines()[1].split() == [f"b{i}" for i in range(14)]
