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
