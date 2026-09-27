"""Tests für die Load-Time-Validierung neuer Config-Felder."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from utils import DEFAULT_CONFIG, _validate_config


def test_note_field_lines_default():
    assert DEFAULT_CONFIG["note_field_lines"] == 2


def test_note_field_lines_invalid_string_falls_back():
    assert _validate_config({"note_field_lines": "abc"})["note_field_lines"] == 2


def test_note_field_lines_out_of_range_falls_back():
    assert _validate_config({"note_field_lines": 9})["note_field_lines"] == 2
    assert _validate_config({"note_field_lines": 0})["note_field_lines"] == 2


def test_note_field_lines_valid_value_kept():
    assert _validate_config({"note_field_lines": 4})["note_field_lines"] == 4
    # Strings mit gültiger Zahl werden koerziert (hand-editierte config.json).
    assert _validate_config({"note_field_lines": "5"})["note_field_lines"] == 5


def test_load_config_setdefault_does_not_alias_default(tmp_path, monkeypatch):
    """Fehlender Schlüssel → Kopie des Defaults, kein Alias auf DEFAULT_CONFIG.

    Regression: ``setdefault(key, value)`` reichte das mutable Default-Dict
    ``project_colors`` durch — die Farbzuweisung der Wochenansicht vergiftete
    damit DEFAULT_CONFIG prozessweit.
    """
    import json

    import utils

    cfg_path = tmp_path / "cfg_ohne_farben.json"
    cfg_path.write_text(json.dumps({"default_user": "X"}), encoding="utf-8")
    monkeypatch.setattr(utils, "CONFIG_PATH", str(cfg_path))

    cfg = utils.load_config()
    cfg["project_colors"]["ProjektX"] = "#123456"
    assert DEFAULT_CONFIG["project_colors"] == {}
    assert "ProjektX" not in utils.load_config()["project_colors"]


def test_load_config_without_file_does_not_alias_default(tmp_path, monkeypatch):
    """Auch der Defaults-Pfad (keine config.json) liefert eine echte Kopie."""
    import utils

    monkeypatch.setattr(utils, "CONFIG_PATH", str(tmp_path / "gibts_nicht.json"))
    cfg = utils.load_config()
    cfg["project_colors"]["ProjektY"] = "#654321"
    assert DEFAULT_CONFIG["project_colors"] == {}
