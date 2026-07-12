"""Gemeinsame Test-Fixtures: Config- und DB-Isolation.

Ohne diese Isolation schreiben App-Tests über ``save_config`` die **echte**
``config.json`` des Nutzers um (z. B. Projektfarben) und arbeiten auf der
echten Datenbank. ``load_config``/``save_config`` lesen ``utils.CONFIG_PATH``
zur Laufzeit, daher genügt ein Monkeypatch des Pfads.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import utils


@pytest.fixture(autouse=True)
def _isolate_config_and_db(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    cfg = dict(utils.DEFAULT_CONFIG)
    cfg["database_path"] = str(tmp_path / "test_app_database.db")
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(utils, "CONFIG_PATH", str(cfg_path))
