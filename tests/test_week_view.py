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


def test_week_button_marks_week_and_untoggles(app_instance, monkeypatch):
    """„✓ Woche" markiert dialogfrei; „↺ Woche" (Reset) fragt vorher nach.

    Der Wochen-Reset löscht auch einzeln gesetzte Marker samt ursprünglichem
    Übertragungsdatum — daher askyesno NUR in Reset-Richtung; „Nein" lässt
    alles unverändert.
    """
    import week_view as week_view_module

    asks = []
    answer = {"value": True}

    def _ask(*a, **k):
        asks.append(a)
        return answer["value"]

    monkeypatch.setattr(week_view_module.messagebox, "askyesno", _ask)

    iso_today = _seed_today(app_instance, projects=("A", "B"))
    week_view = app_instance.week_view
    week_view.refresh()
    assert week_view._btn_transfer.cget("state") == "normal"
    assert week_view._btn_transfer.cget("text") == "✓ Woche"
    assert set(week_view._week_items) == {("A", iso_today), ("B", iso_today)}

    week_view._on_week_transfer()
    assert asks == []  # Setzen bleibt dialogfrei
    for project in ("A", "B"):
        assert get_daily_meta(app_instance.db_conn, "test_user", project, iso_today)["transferred"] is True
    assert week_view._btn_transfer.cget("text") == "↺ Woche"

    # Reset mit „Nein": Rückfrage kommt, Status bleibt unangetastet.
    answer["value"] = False
    week_view._on_week_transfer()
    assert len(asks) == 1
    for project in ("A", "B"):
        assert get_daily_meta(app_instance.db_conn, "test_user", project, iso_today)["transferred"] is True
    assert week_view._btn_transfer.cget("text") == "↺ Woche"

    # Reset mit „Ja": zurückgesetzt.
    answer["value"] = True
    week_view._on_week_transfer()
    assert len(asks) == 2
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


def test_week_cell_tooltip_flattens_multiline_note(app_instance):
    """Mehrzeilige Notiz erscheint in der Tages-Kompaktzeile mit »·« statt Umbruch."""
    from db_helper import set_daily_note

    iso_today = _seed_today(app_instance, projects=("A",))
    set_daily_note(app_instance.db_conn, "test_user", "A", iso_today, "erste Zeile\nzweite Zeile")
    week_view = app_instance.week_view
    week_view.refresh()

    tips = [tip._text for tip in week_view._cell_tips if "A:" in tip._text]
    assert tips
    proj_line = next(ln for ln in tips[0].splitlines() if ln.strip().startswith("A:"))
    assert "erste Zeile · zweite Zeile" in proj_line


# ---------------------------------------------------------------------------
# Zeitmaschinen-Navigation (offset ≠ 0) + ISO-KW über die Jahresgrenze
# ---------------------------------------------------------------------------


def _goto_week_of(app, target_day):
    """Stellt die Zeitmaschine auf die ISO-Woche von ``target_day``.

    Der Offset wird als Montag-zu-Montag-Differenz berechnet und ist damit
    automatisch ein Vielfaches von 7 (wie durch scroll_back/-forward).
    """
    today = datetime.now().date()
    cur_monday = today - timedelta(days=today.weekday())
    tgt_monday = target_day - timedelta(days=target_day.weekday())
    app.week_view.offset = (tgt_monday - cur_monday).days
    app.week_view.refresh()
    return tgt_monday


def _cell_texts(cell):
    from tkinter import Label

    return [c.cget("text") for c in cell.winfo_children() if isinstance(c, Label)]


def _seed_hour(app, day, project="A", start_hour=9):
    """Legt eine 1h-Session am gegebenen Tag an (Nutzer 'test_user')."""
    ts = datetime(day.year, day.month, day.day, start_hour, 0)
    log_start(project=project, name="test_user", timestamp=ts, conn=app.db_conn)
    log_stop(project=project, name="test_user", timestamp=ts + timedelta(hours=1), conn=app.db_conn)


def test_time_machine_scroll_back_and_forward_clamp(app_instance):
    """‹/›-Navigation: offset in 7er-Schritten, KW-Titel folgt, ›-Klemme bei 0."""
    _seed_today(app_instance)
    wv = app_instance.week_view
    wv.refresh()
    assert wv.offset == 0
    assert wv._btn_forward.cget("state") == "disabled"

    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    wv.scroll_back()
    assert wv.offset == -7
    # Vorwoche: KW des Sonntags (monday − 1) der angezeigten Woche.
    prev_kw = (monday - timedelta(days=1)).isocalendar()[1]
    assert wv._title_label.cget("text") == f"Zeitmaschine · KW {prev_kw}"
    assert wv._btn_forward.cget("state") == "normal"

    wv.scroll_forward()
    assert wv.offset == 0
    wv.scroll_forward()  # Klemme: nie in die Zukunft
    assert wv.offset == 0
    assert wv._btn_forward.cget("state") == "disabled"


def test_time_machine_offset_week_shows_only_that_weeks_data(app_instance):
    """Bei offset ≠ 0 zeigt die Legende die Daten der Zielwoche, nicht der
    aktuellen — und umgekehrt."""
    today = datetime.now().date()
    two_weeks_ago = today - timedelta(days=14)
    _seed_hour(app_instance, two_weeks_ago, project="Alt")
    _seed_today(app_instance, projects=("Neu",))
    wv = app_instance.week_view

    wv.refresh()  # aktuelle Woche
    texts = [c.cget("text") for c in wv._legend_frame.winfo_children()]
    assert any("Neu" in t for t in texts)
    assert not any("Alt" in t for t in texts)

    _goto_week_of(app_instance, two_weeks_ago)
    assert wv.offset == -14
    texts = [c.cget("text") for c in wv._legend_frame.winfo_children()]
    assert any("Alt 1:00" in t for t in texts)
    assert not any("Neu" in t for t in texts)


def test_time_machine_iso_kw1_spans_year_boundary(app_instance):
    """ISO-KW 1 kann Tage des Vorjahres enthalten (z. B. Mo 29.12. – So 04.01.):
    Titel zeigt KW 1, die Zellen laufen Mo–So über die Jahresgrenze und
    Sessions BEIDER Kalenderjahre derselben ISO-Woche sind sichtbar."""
    from datetime import date

    year = datetime.now().date().year
    jan4 = date(year, 1, 4)  # der 4. Januar liegt immer in ISO-KW 1
    tgt_monday = jan4 - timedelta(days=jan4.weekday())
    sunday = tgt_monday + timedelta(days=6)
    # Je 1h am Montag (ggf. Vorjahr!) und am Sonntag der KW 1.
    _seed_hour(app_instance, tgt_monday, project="A")
    _seed_hour(app_instance, sunday, project="A")
    app_instance.name_entry.set("test_user")

    assert _goto_week_of(app_instance, jan4) == tgt_monday
    wv = app_instance.week_view
    assert wv._title_label.cget("text") == "Zeitmaschine · KW 1"
    assert wv._week_kw == 1

    # Montag-Grenzen: erste Zelle = Montag, letzte = Sonntag der ISO-Woche.
    mo_texts = _cell_texts(wv._day_frames[0])
    assert mo_texts[0] == "Mo" and mo_texts[1] == tgt_monday.strftime("%d.%m")
    so_texts = _cell_texts(wv._day_frames[6])
    assert so_texts[0] == "So" and so_texts[1] == sunday.strftime("%d.%m")
    # Beide Sessions (altes und neues Kalenderjahr) sind in ihren Zellen sichtbar.
    assert any(t.startswith("1:00") for t in mo_texts)
    assert any(t.startswith("1:00") for t in so_texts)
    legend = [c.cget("text") for c in wv._legend_frame.winfo_children()]
    assert any(t.startswith("Σ") and "2:00 h" in t for t in legend)


def test_time_machine_last_iso_week_of_previous_year(app_instance):
    """Die letzte ISO-KW des Vorjahres heißt KW 52 oder KW 53 — nie KW 0/1."""
    from datetime import date

    year = datetime.now().date().year
    dec28 = date(year - 1, 12, 28)  # der 28. Dezember liegt immer in der letzten ISO-KW
    expected_kw = dec28.isocalendar()[1]
    assert expected_kw in (52, 53)

    tgt_monday = dec28 - timedelta(days=dec28.weekday())
    _seed_hour(app_instance, tgt_monday, project="A")
    app_instance.name_entry.set("test_user")

    assert _goto_week_of(app_instance, dec28) == tgt_monday
    wv = app_instance.week_view
    assert wv.offset < 0 and wv.offset % 7 == 0
    assert wv._title_label.cget("text") == f"Zeitmaschine · KW {expected_kw}"
    mo_texts = _cell_texts(wv._day_frames[0])
    assert mo_texts[0] == "Mo" and mo_texts[1] == tgt_monday.strftime("%d.%m")
    assert any(t.startswith("1:00") for t in mo_texts)
    # In der Vergangenheit ist der ›-Button aktiv (zurück Richtung Gegenwart).
    assert wv._btn_forward.cget("state") == "normal"


def test_week_sums_from_minute_rounded_values(app_instance):
    """Wochensummen aus minutengerundeten Einzelwerten: 3 × 20:20 min → Σ 1:00 h.

    Die Summe der ungerundeten Floats wäre 61,0 min („1:01 h") und wiche damit
    um 1 min von der Summe der drei angezeigten 0:20-Zellwerte ab — genau die
    Falle beim Abgleich mit dem Firmensystem.
    """
    from tkinter import Label

    today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    for i, project in enumerate(("A", "B", "C")):
        start = today + timedelta(hours=i)
        stop = start + timedelta(minutes=20, seconds=20)  # 20:20 → angezeigt „0:20"
        log_start(project=project, name="test_user", timestamp=start, conn=app_instance.db_conn)
        log_stop(project=project, name="test_user", timestamp=stop, conn=app_instance.db_conn)
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("A")

    week_view = app_instance.week_view
    week_view.refresh()

    texts = [c.cget("text") for c in week_view._legend_frame.winfo_children()]
    for project in ("A", "B", "C"):
        assert f"█ {project} 0:20" in texts
    assert any(t.startswith("Σ") and "1:00 h" in t for t in texts)  # nicht 1:01 h

    # Auch die Tageszelle summiert die gerundeten Projektwerte (1:00, nicht 1:01).
    col = datetime.now().date().weekday()
    cell_texts = [c.cget("text") for c in week_view._day_frames[col].winfo_children() if isinstance(c, Label)]
    assert any(t.startswith("1:00 h") for t in cell_texts)
