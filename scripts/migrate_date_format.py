"""Optionales Migrations-Skript: ``events.date`` von ``DD-MM-YYYY`` nach ISO 8601.

Normalfall: WoTiTi speichert ``events.timestamp`` als ``YYYY-MM-DD HH:MM:SS``
(ISO-konform) und ``events.date`` als ``DD-MM-YYYY`` (deutsche UI-Konvention).
Wer aus eigenen Reports / SQL-Abfragen heraus konsequent ISO 8601 in der
``date``-Spalte will, kann dieses Skript einmalig ausführen.

Das Skript:
- legt eine Backup-Datei ``<db>.backup-<timestamp>`` an,
- konvertiert ``date`` von ``DD-MM-YYYY`` nach ``YYYY-MM-DD``,
- markiert den Vorgang in ``migration_log`` (Marker: ``date_format_iso_v1``).

ACHTUNG: Nach Ausführung muss die App-seitige Logik (UI-Felder, Filter,
Stats-Gruppierung) ebenfalls auf ISO umgestellt werden — siehe Hinweis am
Skriptende. Daher: nur ausführen, wenn ein entsprechender Code-Branch aktiv
ist. Solange die App in der Default-Konfiguration läuft (DD-MM-YYYY in
Listbox, Tagesfilter, Statistiken), wird ``migrate_repair_dates`` beim
nächsten Start die Spalte zurück auf ``DD-MM-YYYY`` setzen und damit diese
Migration neutralisieren.

Aufruf:
    python scripts/migrate_date_format.py /pfad/zur/app_database.db
    python scripts/migrate_date_format.py --dry-run /pfad/zur/app_database.db
    python scripts/migrate_date_format.py --revert /pfad/zur/app_database.db
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ISO_MARKER = "date_format_iso_v1"


def _backup(db_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = db_path.with_suffix(db_path.suffix + f".backup-{stamp}")
    shutil.copy2(db_path, backup)
    return backup


def _ensure_log(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS migration_log (
            table_name TEXT PRIMARY KEY,
            migrated_at DATETIME NOT NULL
        )"""
    )


def _already_migrated(conn: sqlite3.Connection) -> bool:
    cur = conn.execute("SELECT 1 FROM migration_log WHERE table_name = ?", (ISO_MARKER,))
    return cur.fetchone() is not None


def to_iso(conn: sqlite3.Connection, dry_run: bool) -> int:
    """Konvertiert ``DD-MM-YYYY`` → ``YYYY-MM-DD`` für alle ``events.date``-Zeilen."""
    expr = "substr(date,7,4) || '-' || substr(date,4,2) || '-' || substr(date,1,2)"
    cur = conn.execute(f"SELECT COUNT(*) FROM events WHERE date LIKE '__-__-____' AND date != ({expr})")
    affected = cur.fetchone()[0]
    if dry_run:
        return affected
    conn.execute(f"UPDATE events SET date = {expr} WHERE date LIKE '__-__-____'")
    conn.execute(
        "INSERT OR REPLACE INTO migration_log (table_name, migrated_at) VALUES (?, ?)",
        (ISO_MARKER, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    return affected


def revert(conn: sqlite3.Connection, dry_run: bool) -> int:
    """Konvertiert ``YYYY-MM-DD`` → ``DD-MM-YYYY`` zurück."""
    expr = "substr(date,9,2) || '-' || substr(date,6,2) || '-' || substr(date,1,4)"
    cur = conn.execute(f"SELECT COUNT(*) FROM events WHERE date LIKE '____-__-__' AND date != ({expr})")
    affected = cur.fetchone()[0]
    if dry_run:
        return affected
    conn.execute(f"UPDATE events SET date = {expr} WHERE date LIKE '____-__-__'")
    conn.execute("DELETE FROM migration_log WHERE table_name = ?", (ISO_MARKER,))
    return affected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("db_path", help="Pfad zur SQLite-Datenbank (z. B. data/app_database.db)")
    parser.add_argument("--dry-run", action="store_true", help="Nur Anzahl betroffener Zeilen ausgeben.")
    parser.add_argument("--revert", action="store_true", help="ISO → DD-MM-YYYY zurück migrieren.")
    parser.add_argument("--no-backup", action="store_true", help="Backup überspringen (nicht empfohlen).")
    args = parser.parse_args(argv)

    db_path = Path(args.db_path)
    if not db_path.is_file():
        print(f"FEHLER: {db_path} existiert nicht.", file=sys.stderr)
        return 2

    if not args.dry_run and not args.no_backup:
        backup = _backup(db_path)
        print(f"Backup: {backup}")

    conn = sqlite3.connect(db_path)
    try:
        _ensure_log(conn)
        if args.revert:
            count = revert(conn, args.dry_run)
            verb = "würden zurückkonvertiert" if args.dry_run else "zurückkonvertiert"
        else:
            if _already_migrated(conn) and not args.dry_run:
                print("Bereits ISO-migriert (Marker vorhanden). Nichts zu tun.")
                return 0
            count = to_iso(conn, args.dry_run)
            verb = "würden konvertiert" if args.dry_run else "konvertiert"
        if not args.dry_run:
            conn.commit()
        print(f"{count} Zeile(n) {verb}.")
        if not args.dry_run and not args.revert and count:
            print(
                "\nHINWEIS: Die laufende App erwartet weiterhin ``DD-MM-YYYY``.\n"
                "Beim nächsten Start wird ``migrate_repair_dates`` diese Migration\n"
                "neutralisieren. Bitte erst die App-Code-Anpassungen einspielen,\n"
                "die ISO-konforme Filter und Anzeige aktivieren, bevor das hier\n"
                "produktiv läuft."
            )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
