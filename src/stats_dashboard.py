import logging
import os
import socket
import sqlite3

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# from dash_extensions.enrich import Dash, Output, Input
import polars as pl
from dash import MATCH, Dash, Input, Output, State, dcc, html

from db_helper import migrate_legacy_user_tables
from stats_calculations import (
    analyze_daily_patterns,
    analyze_time_series,
    available_iso_weeks,
    calculate_average_hours_per_user,
    calculate_break_statistics,
    calculate_daily_project_hours,
    calculate_hour_weekday_matrix,
    calculate_hours_per_project,
    calculate_overview,
    calculate_project_switches,
    calculate_project_time_stats,
    calculate_session_duration_distribution,
    calculate_start_hour_distribution,
    calculate_total_hours_per_user,
    calculate_week_matrix,
    perform_anova_analysis,
)
from stats_plotting import (
    plot_anova_results,
    plot_average_hours_per_user,
    plot_break_analysis,
    plot_daily_patterns,
    plot_daily_project_hours,
    plot_hour_heatmap,
    plot_hours_per_project,
    plot_project_switches,
    plot_project_time_stats,
    plot_session_duration_distribution,
    plot_start_hour_distribution,
    plot_time_series_analysis,
    plot_total_hours_per_user,
)
from utils import (
    PATH_TO_DATA,
    browse_directory,
    find_latest_example_dataset,
    fmt_hours_hm,
    get_app_database_path,
    get_theme_colors,
    read_break_events,
    read_database,
    read_parameters,
)

logger = logging.getLogger(__name__)

# Theme-Farben laden
_colors, _sequence = get_theme_colors()

# Gemeinsame Stil-Definitionen
CARD_STYLE = {"backgroundColor": _colors["secondary"], "color": _colors["text"]}

GRAPH_STYLE = {"backgroundColor": _colors["background"]}

GRAPH_LAYOUT = {"plot_bgcolor": _colors["background"], "paper_bgcolor": _colors["background"]}

DROPDOWN_STYLE = {"color": _colors["text"], "backgroundColor": _colors["secondary"]}

# Assets standardmäßig LOKAL ausliefern — mit CDN bleibt die Seite offline
# komplett leer. Nur im devcontainer (Port-Forwarding erzeugt dort
# ERR_CONTENT_LENGTH_MISMATCH bei lokalen Assets) per Env-Var auf CDN schalten:
# WOTITI_CDN_ASSETS=1.
_serve_locally = os.getenv("WOTITI_CDN_ASSETS", "0") != "1"
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    serve_locally=_serve_locally,
)

_DATA_CACHE = {"db_path": None, "db_mtime": None, "data": None, "stats": {}}

# Letzter beim Auto-Refresh gesehener DB-Änderungszeitstempel; verhindert
# unnötige Chart-Neuberechnungen, wenn sich nichts geändert hat.
_last_autorefresh_mtime: float | None = None

# Aktiver globaler Filter (Datumsbereich + Projektauswahl). Wird von
# update_paths gesetzt; get_filtered_data wendet ihn an. Bei Änderung wird der
# Stats-Cache geleert, damit alle Diagramme neu berechnet werden.
_active_filter: dict = {"start": None, "end": None, "projects": None}


def get_cached_data(db_path, force=False):
    """Loads and caches DB data for reuse across callbacks."""
    if not db_path:
        return pl.DataFrame()

    try:
        db_mtime = os.path.getmtime(db_path)
    except OSError:
        return pl.DataFrame()

    if force or _DATA_CACHE["db_path"] != db_path or _DATA_CACHE["db_mtime"] != db_mtime:
        _DATA_CACHE["db_path"] = db_path
        _DATA_CACHE["db_mtime"] = db_mtime
        data = read_database(db_path)
        if data.is_empty():
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events';")
                    has_events = cursor.fetchone() is not None
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_events';")
                    has_legacy = cursor.fetchone() is not None
                    if not has_events and has_legacy:
                        migrate_legacy_user_tables(conn)
                        data = read_database(db_path)
            except sqlite3.Error:
                pass
        _DATA_CACHE["data"] = data
        _DATA_CACHE["stats"] = {}

    return _DATA_CACHE["data"] if _DATA_CACHE["data"] is not None else pl.DataFrame()


def _weekend_default_value() -> list:
    """Startzustand des Wochenend-Schalters aus der Config ableiten."""
    try:
        from stats_calculations import _workday_settings

        s = _workday_settings()
        if s["count_weekend_work"] or not s["exclude_weekends_in_averages"]:
            return ["include"]
    except Exception:  # noqa: BLE001 — Default darf den App-Start nie verhindern
        logger.exception("Wochenend-Default konnte nicht aus der Config gelesen werden.")
    return []


def _weekend_flag(weekend_include) -> bool:
    """Konvertiert den Checklist-Wert in einen bool."""
    return "include" in (weekend_include or [])


def get_scoped_data(db_path, apply_date_filter=True):
    """DB-Daten mit Datums-/Projektfilter, aber OHNE Wochenend-Filter.

    Für Ansichten, die alle Einträge des gewählten Bereichs zeigen sollen
    (Übersicht inkl. Datenqualitäts-Badges, KW-Report).

    ``apply_date_filter=False``: nur der Projektfilter greift. Der KW-Report
    nutzt das — seine KW-Auswahl IST der Zeitraum, und die Matrix schneidet
    Mitternachts-Sessions tagesgenau zu (identisch zur Wochenansicht der App).
    Der globale Datumsfilter würde Sessions dagegen GANZ (per Start-Tag)
    zuordnen und am Wochenrand Minuten verschieben.
    """
    from stats_calculations import filter_sessions_by_date_range

    data = get_cached_data(db_path)
    if data.is_empty():
        return data
    # Datumsfilter SESSIONWEISE anwenden (eine Session gehört zum Tag ihres
    # Starts) — ein Event-Level-Filter würde bei Mitternachts-Sessions eine
    # Hälfte des Start/Stop-Paars droppen und die Paarung verschieben.
    if apply_date_filter and (_active_filter.get("start") or _active_filter.get("end")):
        data = filter_sessions_by_date_range(data, _active_filter.get("start"), _active_filter.get("end"))
    if _active_filter.get("projects"):
        # Projektfilter droppt ganze (user, project)-Gruppen — paarungssicher.
        data = data.filter(pl.col("project").is_in(_active_filter["projects"]))
    return data


def get_filtered_data(db_path, weekend_include):
    """Gibt die DB-Daten zurück — gefiltert nach Datums-/Projekt-/Wochenend-Filter.

    Memoiziert im Stats-Cache: ~15 Chart-Callbacks rufen das pro Refresh mit
    identischen Parametern auf — der sessionweise Filter muss nur einmal
    laufen. Invalidierung: Cache wird bei Filteränderung (update_paths) und
    bei DB-Reload (get_cached_data) geleert.
    """
    from stats_calculations import _apply_workday_filter

    data = get_cached_data(db_path)  # setzt _DATA_CACHE aktuell (mtime-aware)
    if data.is_empty():
        return data
    count_we = _weekend_flag(weekend_include)
    cache_key = (
        "filtered",
        _active_filter.get("start"),
        _active_filter.get("end"),
        tuple(_active_filter.get("projects") or ()),
        count_we,
    )
    if cache_key not in _DATA_CACHE["stats"]:
        scoped = get_scoped_data(db_path)
        if scoped.is_empty():
            _DATA_CACHE["stats"][cache_key] = scoped
        else:
            # count_weekend_work=True → alles behalten; False → filtern.
            _DATA_CACHE["stats"][cache_key] = _apply_workday_filter(scoped, override_count_weekend_work=count_we)
    return _DATA_CACHE["stats"][cache_key]


def get_filtered_breaks(db_path, weekend_include=None):
    """Pausen (break_events) gefiltert nach Datums-/Projekt- UND Wochenend-Filter.

    Der Wochenend-Filter muss hier genauso greifen wie bei den Arbeitszeiten —
    sonst vergleicht „Arbeit vs. Pause" gefilterte Arbeit mit ungefilterten
    Pausen (Zähler und Nenner decken verschiedene Tage ab).
    """
    from utils import is_non_workday

    breaks = read_break_events(db_path)
    if breaks.is_empty():
        return breaks
    if _active_filter.get("start"):
        breaks = breaks.filter(pl.col("date") >= _active_filter["start"])
    if _active_filter.get("end"):
        breaks = breaks.filter(pl.col("date") <= _active_filter["end"])
    if _active_filter.get("projects"):
        breaks = breaks.filter(pl.col("project").is_in(_active_filter["projects"]))
    if weekend_include is not None and not _weekend_flag(weekend_include) and not breaks.is_empty():
        from datetime import date as _date

        from stats_calculations import _workday_settings

        # Dieselben Feiertags-Einstellungen wie beim Arbeitszeit-Filter —
        # sonst behalten regionale Feiertage ihre Pausen, verlieren aber
        # ihre Arbeit (Arbeit-vs-Pause-Vergleich schief).
        wd = _workday_settings()
        keep_dates = {
            d
            for d in breaks.select(pl.col("date").unique()).to_series().to_list()
            if d
            and not is_non_workday(
                _date.fromisoformat(str(d)[:10]),
                country=wd["country"],
                subdiv=wd["subdiv"],
                include_holidays=wd["include_holidays"],
            )
        }
        breaks = breaks.filter(pl.col("date").is_in(sorted(keep_dates)))
    return breaks


def get_cached_stat(key, compute_fn):
    """Caches expensive computations derived from DB data."""
    if key not in _DATA_CACHE["stats"]:
        _DATA_CACHE["stats"][key] = compute_fn()
    return _DATA_CACHE["stats"][key]


def create_card(header_text, content, md_value=6, col_id=None):
    """Hilfsfunktion zum Erstellen einer einheitlichen Card mit Toggle-Funktion.

    ``col_id``: optionale id der umgebenden Col — für Cards, die per Callback
    ein-/ausgeblendet werden (z. B. Vergleichs-Pie bei nur einem Benutzer).
    """
    card_id = header_text.lower().replace(" ", "-")
    col_kwargs = {"id": col_id} if col_id else {}
    return dbc.Col(
        [
            dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            html.Div(
                                [
                                    html.Span(header_text, style={"color": _colors["text"], "fontWeight": "500"}),
                                    dbc.Button(
                                        "\u25bc",
                                        id={"type": "toggle-card", "index": card_id},
                                        color="link",
                                        size="sm",
                                        style={
                                            "float": "right",
                                            "color": _colors["text"],
                                            "textDecoration": "none",
                                            "fontSize": "12px",
                                            "padding": "2px 8px",
                                            "opacity": "0.7",
                                        },
                                    ),
                                ],
                                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                            )
                        ],
                        style={"borderBottom": f"2px solid {_colors['primary']}"},
                    ),
                    dbc.Collapse(dbc.CardBody(content), id={"type": "collapse-card", "index": card_id}, is_open=True),
                ],
                className="mb-3 shadow-sm",
                style={**CARD_STYLE, "border": "none", "borderRadius": "8px"},
            )
        ],
        md=md_value,
        **col_kwargs,
    )


app.layout = dbc.Container(
    [
        # Modern header with gradient accent
        html.Div(
            [
                html.H1(
                    "WoTiTi Stats",
                    style={
                        "textAlign": "center",
                        "color": _colors["text"],
                        "fontWeight": "300",
                        "letterSpacing": "2px",
                        "marginBottom": "5px",
                    },
                ),
                html.P(
                    "Arbeitszeit-Auswertung",
                    style={"textAlign": "center", "color": _colors["primary"], "fontSize": "14px", "marginBottom": "0"},
                ),
            ],
            style={
                "paddingTop": "20px",
                "paddingBottom": "10px",
                "borderBottom": f"2px solid {_colors['primary']}",
                "marginBottom": "20px",
            },
        ),
        # Verzeichnisauswahl
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.ButtonGroup(
                                            [
                                                dbc.Button(
                                                    "Verzeichnis",
                                                    id="browse-button",
                                                    n_clicks=0,
                                                    color="primary",
                                                    className="mb-3",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    "Beispieldaten",
                                                    id="example-button",
                                                    n_clicks=0,
                                                    color="outline-primary",
                                                    className="mb-3",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    "Aktualisieren",
                                                    id="refresh-button",
                                                    n_clicks=0,
                                                    color="outline-info",
                                                    className="mb-3",
                                                    size="sm",
                                                ),
                                            ]
                                        ),
                                    ],
                                    width="auto",
                                ),
                                # Wochenend-Filter — global im Header, wirkt auf alle Tabs
                                dbc.Col(
                                    dbc.Checklist(
                                        id="weekend-include",
                                        options=[
                                            {"label": " Wochenenden einbeziehen", "value": "include"},
                                        ],
                                        # Default aus der Config: wer Wochenendarbeit zählt
                                        # (count_weekend_work) oder den Ausschluss deaktiviert
                                        # hat, startet mit eingeschaltetem Schalter. Der
                                        # Schalter selbst gewinnt danach immer (Override).
                                        value=_weekend_default_value(),
                                        switch=True,
                                        style={"color": _colors["text"], "fontSize": "13px"},
                                        className="mb-3",
                                    ),
                                    width="auto",
                                    style={"display": "flex", "alignItems": "center", "paddingLeft": "15px"},
                                ),
                                # Datumsbereich-Filter (global) + Schnellwahl für den
                                # Wochen-Workflow (Diese/Letzte Woche/Alles).
                                dbc.Col(
                                    [
                                        dcc.DatePickerRange(
                                            id="date-filter",
                                            display_format="DD.MM.YYYY",
                                            first_day_of_week=1,
                                            clearable=True,
                                            className="mb-3",
                                        ),
                                        dbc.ButtonGroup(
                                            [
                                                dbc.Button(
                                                    "Diese Woche",
                                                    id="preset-this-week",
                                                    n_clicks=0,
                                                    color="outline-secondary",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    "Letzte Woche",
                                                    id="preset-last-week",
                                                    n_clicks=0,
                                                    color="outline-secondary",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    "Alles",
                                                    id="preset-all",
                                                    n_clicks=0,
                                                    color="outline-secondary",
                                                    size="sm",
                                                ),
                                            ],
                                            className="mb-3",
                                            style={"marginLeft": "8px"},
                                        ),
                                    ],
                                    width="auto",
                                    style={"display": "flex", "alignItems": "center", "paddingLeft": "15px"},
                                ),
                                # Projektfilter (global, Mehrfachauswahl)
                                dbc.Col(
                                    dcc.Dropdown(
                                        id="project-filter",
                                        options=[],
                                        value=[],
                                        multi=True,
                                        placeholder="Projekte filtern",
                                        style={"minWidth": "200px", "color": "#000000"},
                                        className="mb-3",
                                    ),
                                    width="auto",
                                    style={"display": "flex", "alignItems": "center", "paddingLeft": "15px"},
                                ),
                                # Export der gefilterten Daten als CSV
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            "Export CSV",
                                            id="export-csv-button",
                                            n_clicks=0,
                                            color="outline-secondary",
                                            size="sm",
                                            className="mb-3",
                                        ),
                                        dcc.Download(id="download-csv"),
                                    ],
                                    width="auto",
                                    style={"display": "flex", "alignItems": "center", "paddingLeft": "15px"},
                                ),
                                # Statusanzeige: EIN Badge (Quelle + Zustand) statt der
                                # früheren dauerhaften Progress-Bar (Header-Rauschen).
                                dbc.Col(
                                    dbc.Badge(
                                        "Datenquelle: –",
                                        id="data-source-badge",
                                        color="secondary",
                                        className="mb-3",
                                        style={"fontSize": "13px"},
                                    ),
                                    width="auto",
                                    style={"display": "flex", "alignItems": "center", "paddingLeft": "15px"},
                                ),
                            ],
                            align="center",
                        ),
                        dcc.Store(id="db-path", data=None),
                        dcc.Store(id="param-path", data=None),
                        dcc.Interval(id="appdb-autoload", interval=1000, n_intervals=0, max_intervals=1),
                        # Periodischer Auto-Refresh: lädt die Daten alle 30 s neu,
                        # aktualisiert die Charts aber nur, wenn sich die DB
                        # tatsächlich geändert hat (mtime-Prüfung in update_paths).
                        dcc.Interval(id="auto-refresh-interval", interval=30000, n_intervals=0),
                        html.Div(id="parameters-table"),
                    ],
                    md=12,
                ),
            ]
        ),
        dbc.Tabs(
            [
                # ── KW-Report: die Ansicht für den Übertragungs-Workflow ──
                # Projekt × Wochentag in H:MM je Kalenderwoche — exakt die Werte,
                # die manuell ins Firmensystem übertragen werden. Inklusive
                # Übertragen-Status (✓) und Tagesnotizen (Tooltip).
                dbc.Tab(
                    [
                        html.Div(
                            [
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button("‹", id="kw-prev", n_clicks=0, color="outline-primary", size="sm"),
                                        dbc.Button(
                                            "KW –",
                                            id="kw-label",
                                            disabled=True,
                                            color="primary",
                                            size="sm",
                                            style={"minWidth": "220px", "opacity": "1"},
                                        ),
                                        dbc.Button("›", id="kw-next", n_clicks=0, color="outline-primary", size="sm"),
                                    ],
                                    className="mb-2",
                                ),
                                dcc.Store(id="kw-selected", data=None),
                            ],
                            style={"textAlign": "center", "marginTop": "25px"},
                        ),
                        html.Div(id="kw-open-hint", style={"textAlign": "center", "marginBottom": "10px"}),
                        html.Div(id="kw-report-content"),
                    ],
                    label="KW-Report",
                ),
                dbc.Tab(
                    [
                        html.H2(
                            "Übersicht",
                            style={"textAlign": "center", "color": _colors["text"], "marginTop": "30px"},
                        ),
                        html.P(
                            "Eckdaten — Datums-/Projektfilter aktiv, Wochenend-Schalter wirkt hier nicht",
                            style={"textAlign": "center", "color": _colors["text"], "marginBottom": "20px"},
                        ),
                        html.Div(id="overview-content"),
                    ],
                    label="Übersicht",
                ),
                dbc.Tab(
                    [
                        html.H2(
                            "Grundlegende Statistiken",
                            style={"textAlign": "center", "color": _colors["text"], "marginTop": "30px"},
                        ),
                        html.P(
                            "Vergleich der Arbeitszeiten zwischen Benutzern und Projekten",
                            style={"textAlign": "center", "color": _colors["text"], "marginBottom": "20px"},
                        ),
                        dbc.Row(
                            [
                                create_card(
                                    "Stunden pro Projekt",
                                    [
                                        # Bei genau einem Benutzer wird das Dropdown
                                        # ausgeblendet und automatisch gewählt
                                        # (update_single_user_layout).
                                        html.Div(
                                            dcc.Dropdown(
                                                id="left-user-dropdown",
                                                placeholder="Benutzer auswählen",
                                                style=DROPDOWN_STYLE,
                                                className="dropdown-custom",
                                            ),
                                            id="left-user-dropdown-wrap",
                                        ),
                                        dbc.Spinner(dcc.Graph(id="left-pie-chart", style=GRAPH_STYLE), size="sm"),
                                    ],
                                ),
                                # Vergleichs-Pie: nur bei mehreren Benutzern sichtbar.
                                create_card(
                                    "Stunden pro Projekt (Vergleich)",
                                    [
                                        dcc.Dropdown(
                                            id="right-user-dropdown",
                                            placeholder="Benutzer auswählen",
                                            style=DROPDOWN_STYLE,
                                            className="dropdown-custom",
                                        ),
                                        dbc.Spinner(
                                            dcc.Graph(
                                                id="right-pie-chart",
                                                style=GRAPH_STYLE,
                                                figure=go.Figure(layout=GRAPH_LAYOUT),
                                            ),
                                            size="sm",
                                        ),
                                    ],
                                    col_id="right-pie-col",
                                ),
                            ]
                        ),
                        html.H2(
                            "Zeitanalyse", style={"textAlign": "center", "color": _colors["text"], "marginTop": "30px"}
                        ),
                        html.P(
                            "Analyse der Arbeitszeiten über verschiedene Zeiträume",
                            style={"textAlign": "center", "color": _colors["text"], "marginBottom": "20px"},
                        ),
                        dbc.Row(
                            [
                                create_card(
                                    "Gesamtstunden pro Benutzer",
                                    [
                                        html.P(
                                            "Gesamtarbeitszeit pro Benutzer über den gesamten Zeitraum",
                                            style={"color": _colors["text"]},
                                        ),
                                        dbc.Spinner(dcc.Graph(id="total-hours-chart", style=GRAPH_STYLE), size="sm"),
                                    ],
                                ),
                                create_card(
                                    "Durchschnittliche Stunden pro Tag",
                                    [
                                        html.P(
                                            "Durchschnittliche tägliche Arbeitszeit pro Benutzer",
                                            style={"color": _colors["text"]},
                                        ),
                                        dbc.Spinner(
                                            dcc.Graph(id="average-hours-per-user-chart", style=GRAPH_STYLE), size="sm"
                                        ),
                                    ],
                                ),
                            ]
                        ),
                        # Hinweis: Die frühere Card „Durchschnitt pro Zeitraum" wurde
                        # entfernt — sie duplizierte „Wöchentliche Durchschnittsstunden"
                        # (Zeitreihen-Tab) mit irreführender Periodenzählung.
                    ],
                    label="Grundlagen",
                ),
                dbc.Tab(
                    [
                        html.H2(
                            "Projektanalyse",
                            style={"textAlign": "center", "color": _colors["text"], "marginTop": "30px"},
                        ),
                        html.P(
                            "Detaillierte Analyse der Projektzeiten und Wechsel",
                            style={"textAlign": "center", "color": _colors["text"], "marginBottom": "20px"},
                        ),
                        dbc.Row(
                            [
                                create_card(
                                    "Projektzeit-Statistiken",
                                    [
                                        html.P(
                                            "Durchschnittliche, minimale und maximale Arbeitsdauer pro Projekt",
                                            style={"color": _colors["text"]},
                                        ),
                                        dbc.Spinner(dcc.Graph(id="project-stats-chart", style=GRAPH_STYLE), size="sm"),
                                    ],
                                    md_value=12,
                                )
                            ]
                        ),
                        dbc.Row(
                            [
                                create_card(
                                    "Tägliche Projektstunden",
                                    [
                                        html.P(
                                            "Tägliche Arbeitszeit aufgeschlüsselt nach Projekten",
                                            style={"color": _colors["text"]},
                                        ),
                                        dbc.Spinner(dcc.Graph(id="daily-hours-chart", style=GRAPH_STYLE), size="sm"),
                                    ],
                                ),
                                create_card(
                                    "Projektwechsel",
                                    [
                                        html.P(
                                            "Analyse der Projektwechsel und Pausen zwischen Projekten",
                                            style={"color": _colors["text"]},
                                        ),
                                        dbc.Spinner(
                                            dcc.Graph(id="project-switches-chart", style=GRAPH_STYLE), size="sm"
                                        ),
                                    ],
                                ),
                            ]
                        ),
                        html.H2(
                            "Arbeitsmuster",
                            style={"textAlign": "center", "color": _colors["text"], "marginTop": "30px"},
                        ),
                        html.P(
                            "Analyse der individuellen Arbeitszeitmuster",
                            style={"textAlign": "center", "color": _colors["text"], "marginBottom": "20px"},
                        ),
                        dbc.Row(
                            [
                                create_card(
                                    "Arbeitsmuster",
                                    [
                                        html.P(
                                            "Durchschnittliche Startzeit pro Projekt",
                                            style={"color": _colors["text"]},
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        # Bei einem Benutzer ausgeblendet und
                                                        # automatisch vorbelegt.
                                                        html.Div(
                                                            dcc.Dropdown(
                                                                id="pattern-user-dropdown",
                                                                placeholder="Benutzer zum Vergleich auswählen",
                                                                multi=True,
                                                                style=DROPDOWN_STYLE,
                                                                className="dropdown-custom",
                                                            ),
                                                            id="pattern-user-dropdown-wrap",
                                                        ),
                                                    ],
                                                    width=6,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Spinner(
                                            dcc.Graph(
                                                id="daily-patterns-chart",
                                                style=GRAPH_STYLE,
                                                figure=go.Figure(layout=GRAPH_LAYOUT),
                                            ),
                                            size="sm",
                                        ),
                                    ],
                                    md_value=12,
                                )
                            ]
                        ),
                        dbc.Row(
                            [
                                create_card(
                                    "Startzeit-Verteilung",
                                    dbc.Spinner(
                                        dcc.Graph(
                                            id="start-hour-dist-chart",
                                            style=GRAPH_STYLE,
                                            figure=go.Figure(layout=GRAPH_LAYOUT),
                                        ),
                                        size="sm",
                                    ),
                                ),
                                create_card(
                                    "Session-Dauer-Verteilung",
                                    dbc.Spinner(
                                        dcc.Graph(
                                            id="session-duration-dist-chart",
                                            style=GRAPH_STYLE,
                                            figure=go.Figure(layout=GRAPH_LAYOUT),
                                        ),
                                        size="sm",
                                    ),
                                ),
                            ]
                        ),
                        dbc.Row(
                            [
                                create_card(
                                    "Projekt-Unterschiede (explorativ)",
                                    [
                                        html.P(
                                            "Verteilung der Session-Dauern je Projekt (Sessions sind nicht "
                                            "unabhängig — explorative Betrachtung).",
                                            style={"color": _colors["text"]},
                                        ),
                                        dbc.Spinner(
                                            dcc.Graph(
                                                id="anova-project-chart",
                                                style=GRAPH_STYLE,
                                                figure=go.Figure(layout=GRAPH_LAYOUT),
                                            ),
                                            size="sm",
                                        ),
                                    ],
                                    md_value=12,
                                ),
                            ]
                        ),
                    ],
                    label="Projekte & Muster",
                ),
                dbc.Tab(
                    [
                        html.H2(
                            "Zeitreihen & Trends",
                            style={"textAlign": "center", "color": _colors["text"], "marginTop": "30px"},
                        ),
                        html.P(
                            "Analyse der Arbeitszeiten über verschiedene Zeiträume",
                            style={"textAlign": "center", "color": _colors["text"], "marginBottom": "20px"},
                        ),
                        # Hinweis: „Täglicher Arbeitsstunden-Trend" wurde entfernt —
                        # redundant zu „Tägliche Projektstunden" (Projekte-Tab).
                        dbc.Row(
                            [
                                create_card(
                                    "Wöchentliche Durchschnittsstunden",
                                    dbc.Spinner(
                                        dcc.Graph(
                                            id="weekly-trend-chart",
                                            style=GRAPH_STYLE,
                                            figure=go.Figure(layout=GRAPH_LAYOUT),
                                        ),
                                        size="sm",
                                    ),
                                ),
                                create_card(
                                    "Wochentags-Muster",
                                    dbc.Spinner(
                                        dcc.Graph(
                                            id="weekday-pattern-chart",
                                            style=GRAPH_STYLE,
                                            figure=go.Figure(layout=GRAPH_LAYOUT),
                                        ),
                                        size="sm",
                                    ),
                                ),
                            ]
                        ),
                        dbc.Row(
                            [
                                create_card(
                                    "Aktivitäts-Heatmap",
                                    dbc.Spinner(
                                        dcc.Graph(
                                            id="hour-heatmap-chart",
                                            style=GRAPH_STYLE,
                                            figure=go.Figure(layout=GRAPH_LAYOUT),
                                        ),
                                        size="sm",
                                    ),
                                    md_value=12,
                                )
                            ]
                        ),
                        dbc.Row(
                            [
                                create_card(
                                    "Arbeit vs. Pause",
                                    dbc.Spinner(
                                        dcc.Graph(
                                            id="break-analysis-chart",
                                            style=GRAPH_STYLE,
                                            figure=go.Figure(layout=GRAPH_LAYOUT),
                                        ),
                                        size="sm",
                                    ),
                                    md_value=12,
                                )
                            ]
                        ),
                    ],
                    label="Zeitreihen",
                ),
                # Hinweis: Der frühere Tab „Erweitert" (Benutzer-Cluster, Regression,
                # Benutzer-ANOVA) wurde entfernt — für den Single-User-Betrieb
                # ohne Aussagekraft. Erhalten blieb nur „Projekt-Unterschiede"
                # (ANOVA über Projekte), verschoben in den Tab „Projekte & Muster".
            ],
            className="mt-4",
        ),
    ],
    fluid=True,
    style={
        "backgroundColor": _colors["background"],
        "color": _colors["text"],
        "padding": "20px 30px",
        "minHeight": "100vh",
    },
)


def _load_dashboard_data(db_path, param_path, label, params_required=True, badge_color="success"):
    """Lädt die Datenquelle; Rückgabe passend zu den update_paths-Outputs.

    Status lebt komplett im Badge (Text + Farbe) — die frühere dauerhafte
    Progress-Bar war Header-Rauschen ohne Informationsgewinn.
    """
    if not db_path or (params_required and not param_path):
        return None, None, f"Datenquelle: {label} — Dateien nicht gefunden", "danger", [], None, [], None

    # get_cached_data ist mtime-aware — ein force-Reload würde die DB nur
    # unnötig doppelt lesen.
    data = get_cached_data(db_path)
    if data.is_empty():
        return db_path, param_path, f"Keine Daten in {label}", "warning", [], None, [], None

    # Stabile (sortierte) Benutzerliste: sonst wechseln Dropdown-Defaults und
    # Legenden-Reihenfolge zwischen Requests.
    users = sorted(user for user in data.select(pl.col("user").unique()).to_series().to_list() if user != "users")
    left_user = "user_1" if "user_1" in users else users[0] if len(users) > 0 else None
    right_user = "user_2" if "user_2" in users else users[1] if len(users) > 1 else None
    options = [{"label": user, "value": user} for user in users]

    return db_path, param_path, f"Datenquelle: {label}", badge_color, options, left_user, options, right_user


@app.callback(
    [
        Output("db-path", "data"),
        Output("param-path", "data"),
        Output("data-source-badge", "children"),
        Output("data-source-badge", "color"),
        Output("left-user-dropdown", "options"),
        Output("left-user-dropdown", "value"),
        Output("right-user-dropdown", "options"),
        Output("right-user-dropdown", "value"),
    ],
    [
        Input("browse-button", "n_clicks"),
        Input("example-button", "n_clicks"),
        Input("refresh-button", "n_clicks"),
        Input("appdb-autoload", "n_intervals"),
        Input("auto-refresh-interval", "n_intervals"),
        Input("date-filter", "start_date"),
        Input("date-filter", "end_date"),
        Input("project-filter", "value"),
    ],
    [
        State("left-user-dropdown", "value"),
        State("right-user-dropdown", "value"),
        State("db-path", "data"),
    ],
)
def update_paths(
    browse_clicks,
    example_clicks,
    refresh_clicks,
    autoload_intervals,
    autorefresh_intervals,
    filter_start,
    filter_end,
    filter_projects,
    left_value,
    right_value,
    current_db,
):
    """Updates database and parameter paths based on selected source."""
    global _last_autorefresh_mtime
    ctx = dash.callback_context
    if not ctx.triggered:
        return None, None, "Datenquelle: –", "secondary", [], None, [], None

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id in ("date-filter", "project-filter"):
        # Globalen Filter aktualisieren, Stats-Cache leeren und db-path neu
        # emittieren → alle Chart-Callbacks rechnen mit dem neuen Filter neu.
        _active_filter["start"] = filter_start
        _active_filter["end"] = filter_end
        _active_filter["projects"] = filter_projects or None
        _DATA_CACHE["stats"] = {}
        nu = dash.no_update
        return (current_db, nu, nu, nu, nu, left_value, nu, right_value)

    if trigger_id == "auto-refresh-interval":
        # Die AKTUELL GEWÄHLTE Quelle prüfen — nicht die App-DB. Sonst würde
        # eine per „Verzeichnis" gewählte Datenbank beim nächsten Tick still
        # durch die App-DB ersetzt.
        if not current_db:
            raise dash.exceptions.PreventUpdate
        try:
            current_mtime = os.path.getmtime(current_db)
        except OSError:
            raise dash.exceptions.PreventUpdate from None
        if current_mtime == _last_autorefresh_mtime:
            raise dash.exceptions.PreventUpdate
        _last_autorefresh_mtime = current_mtime
        # DB hat sich geändert: db-path neu emittieren — das löst die Chart-Callbacks
        # aus, die via get_cached_data (mtime-aware) frisch laden. Alles andere bleibt
        # unverändert (no_update), insbesondere die ausgewählten Benutzer im Dropdown.
        nu = dash.no_update
        return (current_db, nu, nu, nu, nu, left_value, nu, right_value)

    if trigger_id in ("appdb-autoload", "refresh-button"):
        # Bewusst KEIN stiller Beispieldaten-Fallback bei leerer App-DB —
        # Beispieldaten nur über den expliziten Button (sonst hält man
        # Demo-Zahlen für echte).
        db_path = get_app_database_path(PATH_TO_DATA)
        return _load_dashboard_data(db_path, None, "app_database.db", params_required=False)

    if trigger_id == "browse-button":
        directory = browse_directory()
        if not directory:
            return None, None, "Kein Verzeichnis ausgewählt", "secondary", [], None, [], None
        db_path = get_app_database_path(directory)
        label = f"app_database.db ({directory})"
        return _load_dashboard_data(db_path, None, label, params_required=False)

    if trigger_id == "example-button":
        directory = browse_directory()
        if not directory:
            return None, None, "Kein Verzeichnis ausgewählt", "secondary", [], None, [], None
        db_path, param_path = find_latest_example_dataset(directory)
        label = f"BEISPIELDATEN: {os.path.dirname(db_path)}" if db_path else "Beispieldaten"
        # Auffällige Badge-Farbe: niemand soll Demo-Zahlen mit echten verwechseln.
        return _load_dashboard_data(db_path, param_path, label, params_required=True, badge_color="warning")

    return None, None, "Datenquelle: –", "secondary", [], None, [], None


@app.callback(Output("parameters-table", "children"), [Input("param-path", "data")])
def update_parameters_table(param_path):
    """Updates parameters table based on selected parameter file."""
    if param_path:
        parameters = read_parameters(param_path)
        if parameters:
            # Stil-Definitionen
            table_style = {
                "width": "100%",
                "border": "1px solid black",
                "border-collapse": "collapse",
                "margin-bottom": "10px",
                "color": _colors["text"],
                "background-color": _colors["background"],
                "font-size": "0.9em",  # Kleinere Schriftgröße
            }
            header_style = {
                "backgroundColor": _colors["secondary"],
                "color": _colors["text"],
                "padding": "4px 6px",  # Reduziertes Padding
                "font-weight": "bold",
                "text-align": "center",
                "border": f"1px solid {_colors['accent']}",
            }
            cell_style = {
                "border": f"1px solid {_colors['secondary']}",
                "padding": "3px 6px",  # Reduziertes Padding
                "text-align": "center",
            }

            # Container mit Flex-Layout
            return html.Div(
                [
                    # Kompakter Header mit Dropdown für Details
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H4(
                                        "Generierungsparameter",
                                        style={"color": _colors["text"], "margin": "5px 0", "display": "inline-block"},
                                    ),
                                    dbc.Button(
                                        "Details ein/ausblenden",
                                        id="toggle-params",
                                        color="secondary",
                                        size="sm",
                                        className="ml-2",
                                        style={"margin-left": "10px"},
                                    ),
                                ]
                            )
                        ],
                        className="mb-2",
                    ),
                    # Collapse-Container für die Tabellen
                    dbc.Collapse(
                        [
                            # Zwei-Spalten-Layout für die Tabellen
                            dbc.Row(
                                [
                                    # Linke Spalte: General Parameters
                                    dbc.Col(
                                        [
                                            html.Table(
                                                [
                                                    html.Tr(
                                                        [
                                                            html.Th(label_text, style=header_style)
                                                            for label_text in (
                                                                "Anzahl Benutzer",
                                                                "Speichertyp",
                                                                "Start",
                                                                "Ende",
                                                            )
                                                        ]
                                                    ),
                                                    html.Tr(
                                                        [
                                                            html.Td(str(value), style=cell_style)
                                                            for value in [
                                                                parameters.get("num_users"),
                                                                parameters.get("storage_type"),
                                                                parameters.get("start_date"),
                                                                parameters.get("end_date"),
                                                            ]
                                                        ]
                                                    ),
                                                ],
                                                style=table_style,
                                            )
                                        ],
                                        md=12,
                                        lg=12,
                                    ),
                                    # Rechte Spalte: User Parameters
                                    dbc.Col(
                                        [
                                            html.Table(
                                                [
                                                    # Header
                                                    html.Tr(
                                                        [
                                                            html.Th("Benutzer", style=header_style),
                                                            *[
                                                                html.Th(
                                                                    key.replace("_", " ").title(), style=header_style
                                                                )
                                                                for key in parameters.get(
                                                                    "user_specific_params", {}
                                                                ).get("user_1", {})
                                                            ],
                                                        ]
                                                    ),
                                                    # User Zeilen
                                                    *[
                                                        html.Tr(
                                                            [
                                                                html.Th(
                                                                    user, style={**header_style, "font-size": "0.9em"}
                                                                ),
                                                                *[
                                                                    html.Td(str(config[key]), style=cell_style)
                                                                    for key in config
                                                                ],
                                                            ]
                                                        )
                                                        for user, config in parameters.get(
                                                            "user_specific_params", {}
                                                        ).items()
                                                    ],
                                                ],
                                                style=table_style,
                                            )
                                        ],
                                        md=12,
                                        lg=12,
                                    ),
                                ]
                            )
                        ],
                        id="collapse-params",
                        # Entwickler-Detail: nur bei Beispieldaten relevant → default zu.
                        is_open=False,
                    ),
                ]
            )

        return html.Div("Keine Parameter gefunden.", style={"color": _colors["text"]})
    return html.Div("Verzeichnis auswählen, um Parameter zu laden.", style={"color": _colors["text"]})


# Callback für Toggle-Button
@app.callback(
    Output("collapse-params", "is_open"),
    [Input("toggle-params", "n_clicks")],
    [State("collapse-params", "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


@app.callback(
    Output("left-pie-chart", "figure"),
    [Input("left-user-dropdown", "value"), Input("db-path", "data"), Input("weekend-include", "value")],
)
def update_left_pie_chart(selected_user, db_path, weekend_include):
    """Updates the left pie chart based on the selected user."""
    if db_path and selected_user:
        data = get_filtered_data(db_path, weekend_include)
        we = _weekend_flag(weekend_include)
        hours = get_cached_stat(f"hours_per_project_we={int(we)}", lambda: calculate_hours_per_project(data))
        return plot_hours_per_project(hours, selected_user)
    else:
        return go.Figure(layout=GRAPH_LAYOUT)


@app.callback(
    Output("right-pie-chart", "figure"),
    [Input("right-user-dropdown", "value"), Input("db-path", "data"), Input("weekend-include", "value")],
)
def update_right_pie_chart(selected_user, db_path, weekend_include):
    """Updates the right pie chart based on the selected user."""
    if db_path and selected_user:
        data = get_filtered_data(db_path, weekend_include)
        we = _weekend_flag(weekend_include)
        hours = get_cached_stat(f"hours_per_project_we={int(we)}", lambda: calculate_hours_per_project(data))
        return plot_hours_per_project(hours, selected_user)
    # Kein (zweiter) Benutzer gewählt — Hinweis statt leerem Diagramm.
    fig = go.Figure(
        layout=go.Layout(
            plot_bgcolor=_colors["background"],
            paper_bgcolor=_colors["background"],
            font_color=_colors["text"],
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
    )
    fig.add_annotation(
        text="Benutzer auswählen",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color=_colors["text"]),
        opacity=0.5,
    )
    return fig


@app.callback(
    Output("total-hours-chart", "figure"),
    [Input("total-hours-chart", "id"), Input("db-path", "data"), Input("weekend-include", "value")],
)
def update_total_hours_chart(_, db_path, weekend_include):
    """Updates the total hours chart."""
    if db_path:
        data = get_filtered_data(db_path, weekend_include)
        we = _weekend_flag(weekend_include)
        total_hours, date_range = get_cached_stat(
            f"total_hours_per_user_we={int(we)}", lambda: calculate_total_hours_per_user(data)
        )
        return plot_total_hours_per_user(total_hours, date_range)
    else:
        return go.Figure(layout=GRAPH_LAYOUT)


@app.callback(
    Output("average-hours-per-user-chart", "figure"),
    [Input("average-hours-per-user-chart", "id"), Input("db-path", "data"), Input("weekend-include", "value")],
)
def update_average_hours_per_user_chart(_, db_path, weekend_include):
    """Updates the average hours per user chart."""
    if db_path:
        data = get_filtered_data(db_path, weekend_include)
        we = _weekend_flag(weekend_include)
        average_hours = get_cached_stat(
            f"average_hours_per_user_we={int(we)}", lambda: calculate_average_hours_per_user(data)
        )
        return plot_average_hours_per_user(average_hours)
    else:
        return go.Figure(layout=GRAPH_LAYOUT)


# Callback für alle Card-Toggles
@app.callback(
    Output({"type": "collapse-card", "index": MATCH}, "is_open"),
    Input({"type": "toggle-card", "index": MATCH}, "n_clicks"),
    State({"type": "collapse-card", "index": MATCH}, "is_open"),
)
def toggle_card(n_clicks, is_open):
    """Toggle die Sichtbarkeit einer Card."""
    if n_clicks:
        return not is_open
    return is_open


@app.callback(
    [
        Output("project-stats-chart", "figure"),
        Output("daily-hours-chart", "figure"),
        Output("project-switches-chart", "figure"),
        Output("pattern-user-dropdown", "options"),
        Output("pattern-user-dropdown", "value"),
    ],
    [Input("db-path", "data"), Input("weekend-include", "value")],
    [State("pattern-user-dropdown", "value")],
)
def update_advanced_stats(db_path, weekend_include, pattern_value):
    """Aktualisiert die erweiterten Statistik-Visualisierungen."""
    empty_fig = go.Figure(layout=GRAPH_LAYOUT)
    empty_options = []

    if not db_path:
        return empty_fig, empty_fig, empty_fig, empty_options, []

    try:
        data = get_filtered_data(db_path, weekend_include)
        we = _weekend_flag(weekend_include)

        # Projekt-Zeitstatistiken
        stats = get_cached_stat(f"project_time_stats_we={int(we)}", lambda: calculate_project_time_stats(data))
        stats_fig = plot_project_time_stats(stats)

        # Tägliche Projektstunden
        daily_hours = get_cached_stat(f"daily_project_hours_we={int(we)}", lambda: calculate_daily_project_hours(data))
        daily_fig = plot_daily_project_hours(daily_hours, weekend_included=we)

        # Projektwechsel
        switches = get_cached_stat(f"project_switches_we={int(we)}", lambda: calculate_project_switches(data))
        switches_fig = plot_project_switches(switches)

        # User-Optionen für Dropdown (sortiert = stabile Reihenfolge); Default:
        # alle Benutzer vorausgewählt, damit der Arbeitsmuster-Chart nicht leer startet.
        user_names = sorted(
            user for user in data.select(pl.col("user").unique()).to_series().to_list() if user != "users"
        )
        users = [{"label": user, "value": user} for user in user_names]

        # Bestehende Nutzer-Auswahl respektieren (Auto-Refresh darf sie nicht
        # zurücksetzen); nur beim ersten Laden alle Benutzer vorbelegen.
        current = [u for u in (pattern_value or []) if u in user_names]
        pattern_out = current if current else user_names

        return stats_fig, daily_fig, switches_fig, users, pattern_out

    except Exception as e:
        logger.error("Fehler beim Laden der erweiterten Statistiken: %s", e)
        return empty_fig, empty_fig, empty_fig, empty_options, []


@app.callback(
    Output("daily-patterns-chart", "figure"),
    [Input("db-path", "data"), Input("pattern-user-dropdown", "value"), Input("weekend-include", "value")],
)
def update_daily_patterns(db_path, selected_users, weekend_include):
    """Aktualisiert die Visualisierung der tageszeitlichen Muster."""
    if db_path and selected_users:
        try:
            data = get_filtered_data(db_path, weekend_include)
            if selected_users:
                data = data.filter(pl.col("user").is_in(selected_users))

            patterns = analyze_daily_patterns(data)
            return plot_daily_patterns(patterns)

        except Exception as e:
            logger.error("Fehler beim Laden der Tagesmuster: %s", e)
            return go.Figure(layout=GRAPH_LAYOUT)

    return go.Figure(layout=GRAPH_LAYOUT)


@app.callback(
    [
        Output("weekly-trend-chart", "figure"),
        Output("weekday-pattern-chart", "figure"),
    ],
    [Input("db-path", "data"), Input("weekend-include", "value")],
)
def update_time_series_analysis(db_path, weekend_include):
    """Aktualisiert die Zeitreihenanalyse-Visualisierungen.

    Der frühere Tages-Trend-Chart wurde entfernt (redundant zu „Tägliche
    Projektstunden") — plot_time_series_analysis liefert ihn weiterhin,
    er wird hier nur nicht mehr ausgegeben.
    """
    empty_fig = go.Figure(layout=GRAPH_LAYOUT)

    if not db_path:
        return empty_fig, empty_fig

    try:
        data = get_filtered_data(db_path, weekend_include)
        we = _weekend_flag(weekend_include)
        daily_df, weekly_avg, weekday_avg = get_cached_stat(
            f"time_series_we={int(we)}", lambda: analyze_time_series(data)
        )
        _daily_fig, weekly_fig, weekday_fig = plot_time_series_analysis(
            daily_df, weekly_avg, weekday_avg, weekend_included=we
        )
        return weekly_fig, weekday_fig

    except Exception as e:
        logger.error("Fehler bei der Zeitreihenanalyse: %s", e)
        return empty_fig, empty_fig


# Hinweis: Cluster- und Regressions-Callbacks wurden mit dem Tab „Erweitert"
# entfernt (für Single-User ohne Aussagekraft). Von der ANOVA bleibt nur der
# Projekt-Vergleich (Karte im Tab „Projekte & Muster").
@app.callback(
    Output("anova-project-chart", "figure"),
    [Input("db-path", "data"), Input("weekend-include", "value")],
)
def update_anova_analysis(db_path, weekend_include):
    """Aktualisiert den Projekt-Unterschiede-Chart (explorative ANOVA)."""
    empty_fig = go.Figure(layout=GRAPH_LAYOUT)

    if not db_path:
        return empty_fig

    try:
        data = get_filtered_data(db_path, weekend_include)
        we = _weekend_flag(weekend_include)
        anova_results = get_cached_stat(f"anova_analysis_we={int(we)}", lambda: perform_anova_analysis(data))
        if not anova_results:
            return empty_fig
        _user_fig, project_fig = plot_anova_results(anova_results)
        return project_fig

    except Exception as e:
        logger.error("Fehler bei der ANOVA-Analyse: %s", e)
        return empty_fig


@app.callback(
    Output("hour-heatmap-chart", "figure"),
    [Input("db-path", "data"), Input("weekend-include", "value")],
)
def update_hour_heatmap(db_path, weekend_include):
    """Aktualisiert die Aktivitäts-Heatmap (Wochentag × Stunde)."""
    if not db_path:
        return go.Figure(layout=GRAPH_LAYOUT)
    try:
        data = get_filtered_data(db_path, weekend_include)
        we = _weekend_flag(weekend_include)
        matrix = get_cached_stat(f"hour_weekday_matrix_we={int(we)}", lambda: calculate_hour_weekday_matrix(data))
        return plot_hour_heatmap(matrix)
    except Exception as e:
        logger.error("Fehler bei der Heatmap: %s", e)
        return go.Figure(layout=GRAPH_LAYOUT)


@app.callback(
    Output("break-analysis-chart", "figure"),
    [Input("db-path", "data"), Input("weekend-include", "value")],
)
def update_break_analysis(db_path, weekend_include):
    """Aktualisiert die Arbeit-vs-Pause-Analyse aus break_events."""
    if not db_path:
        return go.Figure(layout=GRAPH_LAYOUT)
    try:
        data = get_filtered_data(db_path, weekend_include)
        breaks = get_filtered_breaks(db_path, weekend_include)
        we = _weekend_flag(weekend_include)
        stats = get_cached_stat(f"break_statistics_we={int(we)}", lambda: calculate_break_statistics(breaks, data))
        return plot_break_analysis(stats)
    except Exception as e:
        logger.error("Fehler bei der Pausen-Analyse: %s", e)
        return go.Figure(layout=GRAPH_LAYOUT)


@app.callback(
    Output("start-hour-dist-chart", "figure"),
    [Input("db-path", "data"), Input("weekend-include", "value")],
)
def update_start_hour_dist(db_path, weekend_include):
    """Aktualisiert die Startzeit-Verteilung."""
    if not db_path:
        return go.Figure(layout=GRAPH_LAYOUT)
    try:
        data = get_filtered_data(db_path, weekend_include)
        we = _weekend_flag(weekend_include)
        dist = get_cached_stat(f"start_hour_dist_we={int(we)}", lambda: calculate_start_hour_distribution(data))
        return plot_start_hour_distribution(dist)
    except Exception as e:
        logger.error("Fehler bei der Startzeit-Verteilung: %s", e)
        return go.Figure(layout=GRAPH_LAYOUT)


@app.callback(
    Output("session-duration-dist-chart", "figure"),
    [Input("db-path", "data"), Input("weekend-include", "value")],
)
def update_session_duration_dist(db_path, weekend_include):
    """Aktualisiert die Session-Dauer-Verteilung."""
    if not db_path:
        return go.Figure(layout=GRAPH_LAYOUT)
    try:
        data = get_filtered_data(db_path, weekend_include)
        we = _weekend_flag(weekend_include)
        dist = get_cached_stat(
            f"session_duration_dist_we={int(we)}", lambda: calculate_session_duration_distribution(data)
        )
        return plot_session_duration_distribution(dist)
    except Exception as e:
        logger.error("Fehler bei der Dauer-Verteilung: %s", e)
        return go.Figure(layout=GRAPH_LAYOUT)


@app.callback(
    Output("project-filter", "options"),
    [Input("db-path", "data")],
)
def update_project_filter_options(db_path):
    """Befüllt den Projektfilter mit den Projekten der geladenen Daten."""
    if not db_path:
        return []
    data = get_cached_data(db_path)
    if data.is_empty():
        return []
    projects = sorted(p for p in data.select(pl.col("project").unique()).to_series().to_list() if p)
    return [{"label": p, "value": p} for p in projects]


@app.callback(
    Output("download-csv", "data"),
    [Input("export-csv-button", "n_clicks")],
    [State("db-path", "data"), State("weekend-include", "value")],
    prevent_initial_call=True,
)
def export_filtered_csv(n_clicks, db_path, weekend_include):
    """Exportiert die aktuell gefilterten Arbeits-Events als CSV."""
    if not n_clicks or not db_path:
        raise dash.exceptions.PreventUpdate
    data = get_filtered_data(db_path, weekend_include)
    if data is None or data.is_empty():
        raise dash.exceptions.PreventUpdate
    import io

    buffer = io.StringIO()
    data.write_csv(buffer)
    return {"content": buffer.getvalue(), "filename": "wotiti_export.csv"}


# ---------------------------------------------------------------------------
# Datums-Schnellwahl, Single-User-Layout, KW-Report
# ---------------------------------------------------------------------------


@app.callback(
    [Output("date-filter", "start_date"), Output("date-filter", "end_date")],
    [
        Input("preset-this-week", "n_clicks"),
        Input("preset-last-week", "n_clicks"),
        Input("preset-all", "n_clicks"),
    ],
    prevent_initial_call=True,
)
def apply_date_preset(_this, _last, _all):
    """Schnellwahl passend zum Wochen-Workflow: Diese/Letzte Woche/Alles."""
    from datetime import date, timedelta

    trigger_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    if trigger_id == "preset-this-week":
        return monday.isoformat(), (monday + timedelta(days=6)).isoformat()
    if trigger_id == "preset-last-week":
        last_monday = monday - timedelta(days=7)
        return last_monday.isoformat(), (last_monday + timedelta(days=6)).isoformat()
    return None, None  # "Alles" = Filter löschen


@app.callback(
    [
        Output("right-pie-col", "style"),
        Output("left-user-dropdown-wrap", "style"),
        Output("pattern-user-dropdown-wrap", "style"),
    ],
    [Input("db-path", "data")],
)
def update_single_user_layout(db_path):
    """Blendet Multi-User-Controls aus, wenn die Daten nur EINEN Benutzer enthalten.

    Vergleichs-Pie und Benutzer-Dropdowns sind für den Single-User-Betrieb
    Ballast — die Charts funktionieren dann ohne Auswahl.
    """
    hidden = {"display": "none"}
    visible = {}
    if not db_path:
        return hidden, hidden, hidden
    data = get_cached_data(db_path)
    if data.is_empty():
        return hidden, hidden, hidden
    n_users = data.filter(pl.col("user") != "users").select(pl.col("user").n_unique()).item()
    if n_users <= 1:
        return hidden, hidden, hidden
    return visible, visible, visible


def _week_meta(db_path, iso_dates):
    """Übertragen-Status + Notizen je (Projekt, ISO-Tag) über alle Benutzer.

    Direktabfrage der ``daily_notes``-Tabelle (Single-User-Realität: Meta wird
    benutzerübergreifend zusammengeführt; bei Konflikt gilt „übertragen", wenn
    ALLE Einträge des Schlüssels übertragen sind).
    """
    meta: dict = {}
    if not db_path or not iso_dates:
        return meta
    try:
        with sqlite3.connect(db_path) as conn:
            placeholders = ",".join("?" for _ in iso_dates)
            rows = conn.execute(
                f"SELECT project, date, note, transferred, transferred_at FROM daily_notes "
                f"WHERE date IN ({placeholders})",
                list(iso_dates),
            ).fetchall()
    except sqlite3.Error as e:
        logger.warning("daily_notes konnten nicht gelesen werden: %s", e)
        return meta
    for project, date_iso, note, transferred, transferred_at in rows:
        key = (project, date_iso)
        prev = meta.get(key)
        if prev is None:
            meta[key] = {"note": note or "", "transferred": bool(transferred), "transferred_at": transferred_at}
        else:
            prev["transferred"] = prev["transferred"] and bool(transferred)
            if note:
                prev["note"] = (prev["note"] + " | " + note).strip(" |")
    return meta


@app.callback(
    Output("kw-selected", "data"),
    [Input("kw-prev", "n_clicks"), Input("kw-next", "n_clicks"), Input("db-path", "data")],
    [State("kw-selected", "data")],
)
def update_selected_week(_prev, _next, db_path, selected):
    """Hält die gewählte ISO-KW; Default = jüngste KW mit Daten."""
    if not db_path:
        return None
    weeks = get_cached_stat("iso_weeks", lambda: available_iso_weeks(get_scoped_data(db_path, apply_date_filter=False)))
    if not weeks:
        return None
    trigger_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
    current = tuple(selected) if selected else weeks[-1]
    if current not in weeks:
        current = weeks[-1]
    idx = weeks.index(current)
    if trigger_id == "kw-prev":
        idx = max(0, idx - 1)
    elif trigger_id == "kw-next":
        idx = min(len(weeks) - 1, idx + 1)
    else:
        # db-path-Trigger (Neuladen/Filter): Auswahl beibehalten, wenn möglich.
        pass
    return list(weeks[idx])


_WDAY_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


@app.callback(
    [
        Output("kw-label", "children"),
        Output("kw-open-hint", "children"),
        Output("kw-report-content", "children"),
    ],
    [Input("kw-selected", "data"), Input("db-path", "data")],
)
def update_kw_report(selected, db_path):
    """Rendert die KW-Matrix: Projekt × Wochentag in H:MM, mit ✓/Notizen.

    Genau die Tabelle, die wöchentlich ins Firmensystem übertragen wird.
    """
    from datetime import datetime

    empty_hint = html.Div(
        "Keine Daten für den KW-Report.",
        style={"color": _colors["text"], "textAlign": "center", "padding": "30px"},
    )
    if not db_path or not selected:
        return "KW –", "", empty_hint

    iso_year, iso_week = int(selected[0]), int(selected[1])
    data = get_scoped_data(db_path, apply_date_filter=False)
    matrix = get_cached_stat(
        f"week_matrix_{iso_year}_{iso_week}", lambda: calculate_week_matrix(data, iso_year, iso_week)
    )
    days = matrix["days"]
    first = datetime.strptime(days[0], "%Y-%m-%d")
    last = datetime.strptime(days[-1], "%Y-%m-%d")
    label = f"KW {iso_week:02d}/{iso_year} · {first:%d.%m.} – {last:%d.%m.%Y}"

    # Offene (nicht übertragene) Tage über die letzten Wochen als Hinweis.
    meta = _week_meta(db_path, days)

    if not matrix["projects"]:
        return label, "", empty_hint

    header_style = {
        "backgroundColor": _colors["secondary"],
        "color": _colors["text"],
        "padding": "6px 10px",
        "textAlign": "center",
        "border": f"1px solid {_colors['background']}",
    }
    cell_base = {
        "padding": "6px 10px",
        "textAlign": "center",
        "border": f"1px solid {_colors['secondary']}",
        "color": _colors["text"],
    }

    def _cell(project, iso_day):
        hours = matrix["hours"].get((project, iso_day))
        if not hours:
            return html.Td("–", style={**cell_base, "opacity": "0.35"})
        m = meta.get((project, iso_day), {})
        transferred = m.get("transferred", False)
        text = fmt_hours_hm(hours)
        title = m.get("note") or ""
        if transferred and m.get("transferred_at"):
            title = (title + f"\nübertragen am {m['transferred_at']}").strip()
        style = dict(cell_base)
        if transferred:
            style["opacity"] = "0.6"
        content = f"{text} ✓" if transferred else text
        # Notiz als Marker (°) sichtbar machen, Volltext im Tooltip.
        if m.get("note"):
            content += " °"
        return html.Td(content, title=title or None, style=style)

    weekday_headers = [
        html.Th(f"{_WDAY_DE[i]} {datetime.strptime(d, '%Y-%m-%d'):%d.%m.}", style=header_style)
        for i, d in enumerate(days)
    ]
    rows = []
    for project in matrix["projects"]:
        cells = [html.Th(project, style={**header_style, "textAlign": "left"})]
        cells += [_cell(project, d) for d in days]
        cells.append(
            html.Td(
                fmt_hours_hm(matrix["project_totals"].get(project, 0.0)),
                style={**cell_base, "fontWeight": "bold"},
            )
        )
        rows.append(html.Tr(cells))
    total_row = [html.Th("Σ", style={**header_style, "textAlign": "left"})]
    total_row += [
        html.Td(
            fmt_hours_hm(matrix["day_totals"].get(d, 0.0)) if matrix["day_totals"].get(d) else "–",
            style={**cell_base, "fontWeight": "bold"},
        )
        for d in days
    ]
    total_row.append(html.Td(fmt_hours_hm(matrix["total"]), style={**cell_base, "fontWeight": "bold"}))
    rows.append(html.Tr(total_row))

    table = html.Table(
        [
            html.Tr(
                [
                    html.Th("Projekt", style={**header_style, "textAlign": "left"}),
                    *weekday_headers,
                    html.Th("Σ", style=header_style),
                ]
            ),
            *rows,
        ],
        style={"margin": "0 auto", "borderCollapse": "collapse", "fontSize": "15px"},
    )

    # Offen-Hinweis: Tage der KW mit Stunden, deren Projekte nicht (alle) übertragen sind.
    open_days = []
    for iso_day in days:
        day_projects = [p for p in matrix["projects"] if matrix["hours"].get((p, iso_day))]
        if day_projects and not all(meta.get((p, iso_day), {}).get("transferred") for p in day_projects):
            open_days.append(datetime.strptime(iso_day, "%Y-%m-%d"))
    if open_days:
        hint = dbc.Badge(
            "Offen (nicht übertragen): " + ", ".join(f"{_WDAY_DE[d.weekday()]} {d:%d.%m.}" for d in open_days),
            color="warning",
        )
    else:
        hint = dbc.Badge("Alle Tage dieser KW übertragen ✓", color="success")

    legend = html.Div(
        "✓ = übertragen · ° = Notiz (Tooltip) · Zeiten in H:MM",
        style={
            "color": _colors["text"],
            "opacity": "0.6",
            "fontSize": "12px",
            "textAlign": "center",
            "marginTop": "8px",
        },
    )
    return label, hint, html.Div([table, legend])


def _find_available_port(start_port):
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


# ---------------------------------------------------------------------------
# Übersichts-Tab Callback
# ---------------------------------------------------------------------------


def _badge_list(items, color="info"):
    if not items:
        return html.Span("—", style={"color": _colors["text"], "fontStyle": "italic"})
    return [dbc.Badge(str(x), color=color, className="me-1 mb-1") for x in items]


def _stat_card(title, value, sub=""):
    return dbc.Col(
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div(title, style={"color": _colors["text"], "fontSize": "12px", "opacity": "0.7"}),
                    html.H3(
                        str(value),
                        style={"color": _colors["accent"], "marginTop": "4px", "marginBottom": "2px"},
                    ),
                    html.Div(sub, style={"color": _colors["text"], "fontSize": "11px", "opacity": "0.7"}),
                ]
            ),
            style={**CARD_STYLE, "border": "none", "borderRadius": "8px"},
        ),
        md=4,
        className="mb-3",
    )


@app.callback(Output("overview-content", "children"), [Input("db-path", "data")])
def update_overview(db_path):
    if not db_path:
        return html.Div(
            "Keine Datenbank geladen.", style={"color": _colors["text"], "textAlign": "center", "padding": "30px"}
        )
    # Datums-/Projektfilter respektieren; Wochenend-Schalter bewusst NICHT —
    # die Datenqualitäts-Badges (Wochenend-/Feiertags-Einträge) wären sonst
    # per Definition immer 0. Der Untertitel des Tabs benennt das.
    data = get_scoped_data(db_path)
    ov = calculate_overview(data)
    if not ov or not ov.get("users"):
        return html.Div(
            "Keine Daten in der Datenbank.",
            style={"color": _colors["text"], "textAlign": "center", "padding": "30px"},
        )

    zeitraum = f"{ov['date_min']} – {ov['date_max']}" if ov["date_min"] else "—"
    quality = ov["data_quality"]
    open_color = "danger" if quality["open_sessions"] > 0 else "success"
    we_color = "warning" if quality["weekend_entries"] > 0 else "secondary"
    fy_color = "warning" if quality["holiday_entries"] > 0 else "secondary"

    return [
        dbc.Row(
            [
                _stat_card("Gesamtstunden", f"{ov['total_hours']:.2f} h"),
                _stat_card("Zeitraum", zeitraum),
                _stat_card("Arbeitstage (mit Einträgen)", ov["n_workdays_with_entries"]),
            ]
        ),
        dbc.Row(
            [
                _stat_card("Sessions (gepaart)", ov["n_sessions"]),
                _stat_card("Projekte", len(ov["projects"])),
                _stat_card("Benutzer", len(ov["users"])),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Projekte", style={"color": _colors["text"]}),
                                html.Div(_badge_list(ov["projects"], "info")),
                            ]
                        ),
                        style={**CARD_STYLE, "border": "none", "borderRadius": "8px"},
                    ),
                    md=6,
                    className="mb-3",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Benutzer", style={"color": _colors["text"]}),
                                html.Div(_badge_list(ov["users"], "primary")),
                            ]
                        ),
                        style={**CARD_STYLE, "border": "none", "borderRadius": "8px"},
                    ),
                    md=6,
                    className="mb-3",
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Datenqualität", style={"color": _colors["text"]}),
                                dbc.Badge(
                                    f"Offene Sessions: {quality['open_sessions']}",
                                    color=open_color,
                                    className="me-2",
                                ),
                                dbc.Badge(
                                    f"Wochenend-Einträge: {quality['weekend_entries']}",
                                    color=we_color,
                                    className="me-2",
                                ),
                                dbc.Badge(
                                    f"Feiertags-Einträge: {quality['holiday_entries']}",
                                    color=fy_color,
                                ),
                            ]
                        ),
                        style={**CARD_STYLE, "border": "none", "borderRadius": "8px"},
                    ),
                    md=12,
                    className="mb-3",
                ),
            ]
        ),
    ]


if __name__ == "__main__":
    debug_mode = os.getenv("DASH_DEBUG", "0") == "1"
    base_port = int(os.getenv("DASH_PORT", "8052"))
    port = _find_available_port(base_port)
    if port != base_port:
        logger.info("Port %d belegt, starte auf %d", base_port, port)
    app.run(debug=debug_mode, use_reloader=False, port=port)
