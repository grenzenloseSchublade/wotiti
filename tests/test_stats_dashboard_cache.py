"""Tests für die WAL-bewusste Cache-Invalidierung des Dashboards.

Die App schreibt im WAL-Modus (db_helper.create_connection): Commits landen
bis zum Checkpoint nur in der ``-wal``-Datei, die mtime der Haupt-DB bleibt
konstant. Der Daten-Cache muss daher BEIDE Dateien beobachten — sonst zeigt
die Auswertung bis zum App-Neustart veraltete Zahlen (auch nach Refresh-Klick).
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import polars as pl


def test_db_change_stamp_prefers_newer_wal(tmp_path):
    """Der Änderungs-Zeitstempel ist das Maximum aus Haupt-DB und WAL-Datei."""
    import stats_dashboard as sd

    db = tmp_path / "app.db"
    db.write_bytes(b"")
    os.utime(db, (1000, 1000))
    assert sd._db_change_stamp(str(db)) == 1000

    wal = tmp_path / "app.db-wal"
    wal.write_bytes(b"")
    os.utime(wal, (2000, 2000))
    assert sd._db_change_stamp(str(db)) == 2000


def test_wal_touch_invalidates_dashboard_cache(tmp_path, monkeypatch):
    """„Commit" nur in die WAL-Datei (Haupt-DB-mtime unverändert) → der nächste
    get_cached_data-Aufruf liest neu statt den alten Cache zu liefern."""
    import stats_dashboard as sd

    db = tmp_path / "app.db"
    db.write_bytes(b"")
    os.utime(db, (1000, 1000))

    reads = []
    monkeypatch.setattr(sd, "read_database", lambda p: reads.append(p) or pl.DataFrame({"user": ["u"]}))
    monkeypatch.setattr(sd, "_DATA_CACHE", {"db_path": None, "db_mtime": None, "data": None, "stats": {}})

    assert not sd.get_cached_data(str(db)).is_empty()
    assert len(reads) == 1
    sd.get_cached_data(str(db))
    assert len(reads) == 1  # nichts geändert → Cache-Treffer

    wal = tmp_path / "app.db-wal"
    wal.write_bytes(b"")
    os.utime(wal, (2000, 2000))
    sd.get_cached_data(str(db))
    assert len(reads) == 2  # WAL-Touch invalidiert den Cache
