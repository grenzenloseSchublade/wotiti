"""Tests für die Wochen-Kachel (WeekView): Übertragen-Toggles, Tooltip-Leak, KW."""

from datetime import datetime, timedelta
from tkinter import Tk

import pytest

# sys.path auf src/ setzt bereits tests/conftest.py (läuft vor allen Testmodulen).
from app import App
from db_helper import get_daily_meta, log_start, log_stop


@pytest.fixture
def app_instance():
    root = Tk()
    app = App(root)
    yield app
    root.destroy()


def _seed_today(app, projects=("A", "B")):
    """Legt für heute je Projekt eine 1h-Session an und wählt den Nutzer aus."""
    today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    for i, project in enumerate(projects):
        log_start(project=project, name="test_user", timestamp=today + timedelta(hours=i * 2), conn=app.db_conn)
        log_stop(project=project, name="test_user", timestamp=today + timedelta(hours=i * 2 + 1), conn=app.db_conn)
    app.name_entry.set("test_user")
    app.project_entry.set(projects[0])
    return today.strftime("%Y-%m-%d")


def test_week_cell_tooltip_bindings_do_not_accumulate(app_instance):
    """Wiederholte refresh()-Aufrufe dürfen keine neuen Bindings auf den Zellen anlegen.

    Regression für den Freeze-Bug: früher band jeder Refresh drei weitere
    Event-Handler (add="+") pro persistenter Tageszelle — unbegrenzt wachsend.
    """
    _seed_today(app_instance)
    week_view = app_instance.week_view
    week_view.refresh()
    counts_before = [len(cell.bind("<Enter>").split("\n")) for cell in week_view._day_frames]
    for _ in range(5):
        week_view.refresh()
    counts_after = [len(cell.bind("<Enter>").split("\n")) for cell in week_view._day_frames]
    assert counts_after == counts_before


def test_week_day_click_toggles_all_projects(app_instance):
    """Tages-Klick setzt alle Projekte des Tages auf übertragen — und zurück."""
    iso_today = _seed_today(app_instance, projects=("A", "B"))
    app_instance.week_view.refresh()

    app_instance.week_view._on_day_transfer(iso_today, ["A", "B"], "Testtag")
    for project in ("A", "B"):
        meta = get_daily_meta(app_instance.db_conn, "test_user", project, iso_today)
        assert meta["transferred"] is True
        assert meta["transferred_at"] == datetime.now().strftime("%Y-%m-%d")

    app_instance.week_view._on_day_transfer(iso_today, ["A", "B"], "Testtag")
    for project in ("A", "B"):
        assert get_daily_meta(app_instance.db_conn, "test_user", project, iso_today)["transferred"] is False


def test_week_day_click_mixed_state_sets_all(app_instance):
    """Bei Mischzustand (ein Projekt übertragen, eins offen) setzt der Klick alle."""
    from db_helper import set_daily_transferred

    iso_today = _seed_today(app_instance, projects=("A", "B"))
    set_daily_transferred(app_instance.db_conn, "test_user", "A", iso_today, True, transferred_at="2025-01-01")

    app_instance.week_view._on_day_transfer(iso_today, ["A", "B"], "Testtag")
    for project in ("A", "B"):
        assert get_daily_meta(app_instance.db_conn, "test_user", project, iso_today)["transferred"] is True
    # A behält sein ursprüngliches transferred_at (kein Überschreiben).
    assert get_daily_meta(app_instance.db_conn, "test_user", "A", iso_today)["transferred_at"] == "2025-01-01"


def test_week_button_marks_week_and_untoggles(app_instance):
    """„✓ Woche" markiert alle sichtbaren Einträge; danach bietet er „↺ Woche" an."""
    iso_today = _seed_today(app_instance, projects=("A", "B"))
    week_view = app_instance.week_view
    week_view.refresh()
    assert week_view._btn_transfer.cget("state") == "normal"
    assert week_view._btn_transfer.cget("text") == "✓ Woche"
    assert set(week_view._week_items) == {("A", iso_today), ("B", iso_today)}

    week_view._on_week_transfer()
    for project in ("A", "B"):
        assert get_daily_meta(app_instance.db_conn, "test_user", project, iso_today)["transferred"] is True
    assert week_view._btn_transfer.cget("text") == "↺ Woche"

    week_view._on_week_transfer()
    for project in ("A", "B"):
        assert get_daily_meta(app_instance.db_conn, "test_user", project, iso_today)["transferred"] is False
    assert week_view._btn_transfer.cget("text") == "✓ Woche"


def test_week_button_disabled_without_hours(app_instance):
    """Ohne Zeiten in der Woche bleibt der Wochen-Button deaktiviert."""
    app_instance.name_entry.set("test_user")
    from db_helper import check_user

    check_user(app_instance.db_conn, "test_user")
    app_instance.week_view.refresh()
    assert app_instance.week_view._btn_transfer.cget("state") == "disabled"


def test_status_bar_shows_kw(app_instance):
    """Die Statusleiste zeigt die Kalenderwoche des angezeigten Datums."""
    app_instance.set_today_date()
    app_instance.update_db_content()
    expected_kw = datetime.now().isocalendar()[1]
    assert f"· KW {expected_kw}" in app_instance._status_date_label.cget("text")


def test_ensure_project_colors_saves_once(app_instance, monkeypatch):
    """Neue Projektfarben werden gebatcht persistiert: max. 1 save_config pro Refresh."""
    import week_view as week_view_module

    calls = []
    monkeypatch.setattr(week_view_module, "save_config", lambda cfg: calls.append(1))

    colors = app_instance.week_view._ensure_project_colors(["Neu1", "Neu2", "Neu3"])
    assert len(calls) == 1
    assert len({colors[p] for p in ("Neu1", "Neu2", "Neu3")}) == 3  # distinkte Farben

    # Zweiter Aufruf: alles bekannt → kein weiterer Save.
    app_instance.week_view._ensure_project_colors(["Neu1", "Neu2", "Neu3"])
    assert len(calls) == 1


def test_week_view_starts_on_monday(app_instance):
    """Die Zeitmaschine zeigt die Kalenderwoche Mo–So, nicht ein rollierendes Fenster."""
    from tkinter import Label

    _seed_today(app_instance)
    week_view = app_instance.week_view
    week_view.refresh()

    labels = [c for c in week_view._day_frames[0].winfo_children() if isinstance(c, Label)]
    assert labels and labels[0].cget("text") == "Mo"

    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    assert f"KW {monday.isocalendar()[1]}" in week_view._title_label.cget("text")


def test_week_legend_shows_project_totals(app_instance):
    """Die Legende zeigt pro Projekt die Wochensumme (H:MM) plus Σ-Gesamt."""
    _seed_today(app_instance, projects=("A", "B"))  # je 1h heute
    week_view = app_instance.week_view
    week_view.refresh()

    texts = [c.cget("text") for c in week_view._legend_frame.winfo_children()]
    assert "█ A 1:00" in texts
    assert "█ B 1:00" in texts
    assert any(t.startswith("Σ") and "2:00 h" in t for t in texts)
