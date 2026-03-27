import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html, State, Input, Output, Dash, MATCH
import os
import socket
import sqlite3
#from dash_extensions.enrich import Dash, Output, Input
import polars as pl
from stats_calculations import (
    calculate_hours_per_project, 
    calculate_total_hours_per_user, 
    calculate_average_hours_per_user, 
    calculate_average_hours_per_period,
    calculate_project_time_stats,
    calculate_daily_project_hours,
    calculate_project_switches,
    analyze_daily_patterns,
    analyze_time_series,
    perform_cluster_analysis,
    perform_regression_analysis,
    perform_anova_analysis
)
from stats_plotting import (
    plot_hours_per_project, 
    plot_total_hours_per_user, 
    plot_average_hours_per_user,
    plot_average_hours_per_period,
    plot_project_time_stats,
    plot_daily_project_hours,
    plot_project_switches,
    plot_daily_patterns,
    plot_time_series_analysis,
    plot_cluster_analysis,
    plot_regression_analysis,
    plot_anova_results
)
from utils import read_database, browse_directory, read_parameters, get_app_database_path, find_latest_example_dataset, PATH_TO_DATA
from db_helper import migrate_legacy_user_tables
from utils import MODERN_COLORS, SYNTHWAVE_COLORS

# Gemeinsame Stil-Definitionen
CARD_STYLE = {
    'backgroundColor': MODERN_COLORS['secondary'],
    'color': MODERN_COLORS['text']
}

GRAPH_STYLE = {
    'backgroundColor': MODERN_COLORS['background']
}

GRAPH_LAYOUT = {
    'plot_bgcolor': MODERN_COLORS['background'],
    'paper_bgcolor': MODERN_COLORS['background']
}

DROPDOWN_STYLE = {
    'color': MODERN_COLORS['text'],
    'backgroundColor': MODERN_COLORS['secondary']
}

# Dash App — serve_locally=False so plotly.min.js loads from CDN
# (avoids ERR_CONTENT_LENGTH_MISMATCH in devcontainer port forwarding)
app = Dash(__name__, 
           external_stylesheets=[dbc.themes.DARKLY],
           suppress_callback_exceptions=True,
           serve_locally=False)

_DATA_CACHE = {
    "db_path": None,
    "db_mtime": None,
    "data": None,
    "stats": {}
}

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

def get_cached_stat(key, compute_fn):
    """Caches expensive computations derived from DB data."""
    if key not in _DATA_CACHE["stats"]:
        _DATA_CACHE["stats"][key] = compute_fn()
    return _DATA_CACHE["stats"][key]

def create_card(header_text, content, md_value=6):
    """Hilfsfunktion zum Erstellen einer einheitlichen Card mit Toggle-Funktion."""
    card_id = header_text.lower().replace(" ", "-")
    return dbc.Col([
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.Span(header_text, style={'color': MODERN_COLORS['text'], 'fontWeight': '500'}),
                    dbc.Button(
                        "\u25BC",
                        id={'type': 'toggle-card', 'index': card_id},
                        color="link",
                        size="sm",
                        style={'float': 'right', 'color': MODERN_COLORS['text'], 'textDecoration': 'none',
                               'fontSize': '12px', 'padding': '2px 8px', 'opacity': '0.7'}
                    )
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'})
            ], style={'borderBottom': f'2px solid {MODERN_COLORS["primary"]}'}),
            dbc.Collapse(
                dbc.CardBody(content),
                id={'type': 'collapse-card', 'index': card_id},
                is_open=True
            )
        ], className="mb-3 shadow-sm", style={**CARD_STYLE, 'border': 'none', 'borderRadius': '8px'})
    ], md=md_value)

app.layout = dbc.Container([
    # Modern header with gradient accent
    html.Div([
        html.H1("WoTiTi Stats", style={
            'textAlign': 'center', 'color': MODERN_COLORS['text'],
            'fontWeight': '300', 'letterSpacing': '2px', 'marginBottom': '5px'
        }),
        html.P("Work Time Tracking & Insights Dashboard", style={
            'textAlign': 'center', 'color': MODERN_COLORS['primary'],
            'fontSize': '14px', 'marginBottom': '0'
        }),
    ], style={'paddingTop': '20px', 'paddingBottom': '10px',
             'borderBottom': f'2px solid {MODERN_COLORS["primary"]}', 'marginBottom': '20px'}),
    
    # Verzeichnisauswahl
    dbc.Row([
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button('\U0001F4C1 Verzeichnis', id='browse-button', n_clicks=0,
                                   color="primary", className="mb-3", size="sm"),
                        dbc.Button('\U0001F4CA Beispieldaten', id='example-button', n_clicks=0,
                                   color="outline-primary", className="mb-3", size="sm"),
                        dbc.Button('\U0001F504 Aktualisieren', id='refresh-button', n_clicks=0,
                                   color="outline-info", className="mb-3", size="sm"),
                    ]),
                ], width="auto"),
                dbc.Col([
                    dbc.Progress(
                        id="progress",
                        value=0,
                        animated=False,
                        striped=True,
                        color="info",
                        className="mb-3",
                        style={
                            'height': '30px',
                            'width': '100%',
                            'display': 'flex',
                            'alignItems': 'center',
                            'justifyContent': 'center',
                            'fontSize': '14px',
                            'fontWeight': 'bold',
                            'backgroundColor': MODERN_COLORS['secondary'],
                        },
                        children="Verzeichnis auswählen"
                    ),
                    dbc.Badge(
                        "Datenquelle: -",
                        id="data-source-badge",
                        color="secondary",
                        className="mt-2",
                    ),
                ], md=8), 
            ], align="center"),
            dcc.Store(id='db-path', data=None),
            dcc.Store(id='param-path', data=None),
            dcc.Interval(id='appdb-autoload', interval=1000, n_intervals=0, max_intervals=1),
            html.Div(id='parameters-table')
        ], md=12),
    ]),

    dbc.Tabs([
        dbc.Tab([
            html.H2("Grundlegende Statistiken",
                    style={'textAlign': 'center', 'color': MODERN_COLORS['text'], 'marginTop': '30px'}),
            html.P("Vergleich der Arbeitszeiten zwischen Benutzern und Projekten",
                   style={'textAlign': 'center', 'color': MODERN_COLORS['text'], 'marginBottom': '20px'}),
            dbc.Row([
                create_card("Stunden pro Projekt (1)", [
                    dcc.Dropdown(
                        id='left-user-dropdown',
                        placeholder="Benutzer auswählen",
                        style=DROPDOWN_STYLE,
                        className='dropdown-custom'
                    ),
                    dbc.Spinner(dcc.Graph(id='left-pie-chart', style=GRAPH_STYLE), size="sm")
                ]),
                create_card("Stunden pro Projekt (2)", [
                    dcc.Dropdown(
                        id='right-user-dropdown',
                        placeholder="Benutzer auswählen",
                        style=DROPDOWN_STYLE,
                        className='dropdown-custom'
                    ),
                    dbc.Spinner(dcc.Graph(
                        id='right-pie-chart',
                        style=GRAPH_STYLE,
                        figure=go.Figure(layout=GRAPH_LAYOUT)
                    ), size="sm")
                ])
            ]),
            html.H2("Zeitanalyse",
                    style={'textAlign': 'center', 'color': MODERN_COLORS['text'], 'marginTop': '30px'}),
            html.P("Analyse der Arbeitszeiten über verschiedene Zeiträume",
                   style={'textAlign': 'center', 'color': MODERN_COLORS['text'], 'marginBottom': '20px'}),
            dbc.Row([
                create_card(
                    "Gesamtstunden pro Benutzer",
                    [
                        html.P("Gesamtarbeitszeit pro Benutzer über den gesamten Zeitraum",
                               style={'color': MODERN_COLORS['text']}),
                        dbc.Spinner(dcc.Graph(id='total-hours-chart', style=GRAPH_STYLE), size="sm")
                    ]
                ),
                create_card(
                    "Durchschnittliche Stunden pro Tag",
                    [
                        html.P("Durchschnittliche tägliche Arbeitszeit pro Benutzer",
                               style={'color': MODERN_COLORS['text']}),
                        dbc.Spinner(dcc.Graph(id='average-hours-per-user-chart', style=GRAPH_STYLE), size="sm")
                    ]
                )
            ]),
            dbc.Row([
                create_card(
                    "Durchschnitt pro Zeitraum",
                    [
                        html.P("Durchschnittliche Arbeitszeit pro benutzerdefiniertem Zeitraum",
                               style={'color': MODERN_COLORS['text']}),
                        dbc.InputGroup([
                            dbc.Input(id='period-days-input', type='number', value=7, min=1, max=365,
                                      style={'backgroundColor': MODERN_COLORS['secondary'], 'color': MODERN_COLORS['text'],
                                             'border': f'1px solid {MODERN_COLORS["primary"]}'}),
                            dbc.InputGroupText("Tage"),
                            dbc.Button("Berechnen", id='update-period-button', n_clicks=0, color="primary", size="sm"),
                        ], className="mb-3"),
                        dbc.Spinner(dcc.Graph(id='average-hours-per-period-chart', style=GRAPH_STYLE), size="sm")
                    ],
                    md_value=12
                )
            ]),
        ], label="Grundlagen"),
        dbc.Tab([
            html.H2("Projektanalyse",
                    style={'textAlign': 'center', 'color': MODERN_COLORS['text'], 'marginTop': '30px'}),
            html.P("Detaillierte Analyse der Projektzeiten und Wechsel",
                   style={'textAlign': 'center', 'color': MODERN_COLORS['text'], 'marginBottom': '20px'}),
            dbc.Row([
                create_card(
                    "Projektzeit-Statistiken",
                    [
                        html.P("Durchschnittliche, minimale und maximale Arbeitsdauer pro Projekt",
                               style={'color': MODERN_COLORS['text']}),
                        dbc.Spinner(dcc.Graph(id='project-stats-chart', style=GRAPH_STYLE), size="sm")
                    ],
                    md_value=12
                )
            ]),
            dbc.Row([
                create_card(
                    "Tägliche Projektstunden",
                    [
                        html.P("Tägliche Arbeitszeit aufgeschlüsselt nach Projekten",
                               style={'color': MODERN_COLORS['text']}),
                        dbc.Spinner(dcc.Graph(id='daily-hours-chart', style=GRAPH_STYLE), size="sm")
                    ]
                ),
                create_card(
                    "Projektwechsel",
                    [
                        html.P("Analyse der Projektwechsel und Pausen zwischen Projekten",
                               style={'color': MODERN_COLORS['text']}),
                        dbc.Spinner(dcc.Graph(id='project-switches-chart', style=GRAPH_STYLE), size="sm")
                    ]
                )
            ]),
            html.H2("Arbeitsmuster",
                    style={'textAlign': 'center', 'color': MODERN_COLORS['text'], 'marginTop': '30px'}),
            html.P("Analyse der individuellen Arbeitszeitmuster",
                   style={'textAlign': 'center', 'color': MODERN_COLORS['text'], 'marginBottom': '20px'}),
            dbc.Row([
                create_card(
                    "Arbeitsmuster",
                    [
                        html.P("Tageszeitliche Arbeitsmuster: Frühe Starter (vor 8 Uhr), Kernzeitarbeiter (9-17 Uhr), Spätarbeiter (nach 17 Uhr)",
                               style={'color': MODERN_COLORS['text']}),
                        dbc.Row([
                            dbc.Col([
                                dcc.Dropdown(
                                    id='pattern-user-dropdown',
                                    placeholder="Benutzer zum Vergleich auswählen",
                                    multi=True,
                                    style=DROPDOWN_STYLE,
                                    className='dropdown-custom'
                                ),
                            ], width=6),
                        ], className="mb-3"),
                        dbc.Spinner(dcc.Graph(
                            id='daily-patterns-chart',
                            style=GRAPH_STYLE,
                            figure=go.Figure(layout=GRAPH_LAYOUT)
                        ), size="sm")
                    ],
                    md_value=12
                )
            ]),
        ], label="Projekte & Muster"),
        dbc.Tab([
            html.H2("Zeitreihen & Trends",
                    style={'textAlign': 'center', 'color': MODERN_COLORS['text'], 'marginTop': '30px'}),
            html.P("Analyse der Arbeitszeiten über verschiedene Zeiträume",
                   style={'textAlign': 'center', 'color': MODERN_COLORS['text'], 'marginBottom': '20px'}),
            dbc.Row([
                create_card(
                    "Täglicher Arbeitsstunden-Trend",
                    dbc.Spinner(dcc.Graph(
                        id='daily-trend-chart',
                        style=GRAPH_STYLE,
                        figure=go.Figure(layout=GRAPH_LAYOUT)
                    ), size="sm"),
                    md_value=12
                )
            ]),
            dbc.Row([
                create_card(
                    "Wöchentliche Durchschnittsstunden",
                    dbc.Spinner(dcc.Graph(
                        id='weekly-trend-chart',
                        style=GRAPH_STYLE,
                        figure=go.Figure(layout=GRAPH_LAYOUT)
                    ), size="sm")
                ),
                create_card(
                    "Wochentags-Muster",
                    dbc.Spinner(dcc.Graph(
                        id='weekday-pattern-chart',
                        style=GRAPH_STYLE,
                        figure=go.Figure(layout=GRAPH_LAYOUT)
                    ), size="sm")
                )
            ]),
        ], label="Zeitreihen"),
        dbc.Tab([
            html.H2("Erweiterte Analysen",
                    style={'textAlign': 'center', 'color': MODERN_COLORS['text'], 'marginTop': '30px'}),
            dbc.Row([
                create_card(
                    "Benutzer-Cluster Übersicht",
                    dbc.Spinner(dcc.Graph(
                        id='cluster-overview-chart',
                        style=GRAPH_STYLE,
                        figure=go.Figure(layout=GRAPH_LAYOUT)
                    ), size="sm")
                ),
                create_card(
                    "Cluster-Profile",
                    dbc.Spinner(dcc.Graph(
                        id='cluster-profile-chart',
                        style=GRAPH_STYLE,
                        figure=go.Figure(layout=GRAPH_LAYOUT)
                    ), size="sm")
                )
            ]),
            dbc.Row([
                create_card(
                    "Dauer-Prädiktoren",
                    dbc.Spinner(dcc.Graph(
                        id='regression-importance-chart',
                        style=GRAPH_STYLE,
                        figure=go.Figure(layout=GRAPH_LAYOUT)
                    ), size="sm")
                ),
                create_card(
                    "Vorhersagegenauigkeit",
                    dbc.Spinner(dcc.Graph(
                        id='regression-accuracy-chart',
                        style=GRAPH_STYLE,
                        figure=go.Figure(layout=GRAPH_LAYOUT)
                    ), size="sm")
                )
            ]),
            dbc.Row([
                create_card(
                    "Benutzer-Unterschiede",
                    dbc.Spinner(dcc.Graph(
                        id='anova-user-chart',
                        style=GRAPH_STYLE,
                        figure=go.Figure(layout=GRAPH_LAYOUT)
                    ), size="sm")
                ),
                create_card(
                    "Projekt-Unterschiede",
                    dbc.Spinner(dcc.Graph(
                        id='anova-project-chart',
                        style=GRAPH_STYLE,
                        figure=go.Figure(layout=GRAPH_LAYOUT)
                    ), size="sm")
                )
            ]),
        ], label="Erweitert"),
    ], className="mt-4")
], fluid=True, style={'backgroundColor': MODERN_COLORS['background'], 'color': MODERN_COLORS['text'],
                       'padding': '20px 30px', 'minHeight': '100vh'})

def _load_dashboard_data(db_path, param_path, label, params_required=True):
    def update_progress(value, text, animated=True, striped=True):
        return [value, animated, striped, f"{text} ({value}%)"]

    data_source = f"Datenquelle: {label}"
    if not db_path or (params_required and not param_path):
        progress_values = update_progress(100, "Fehler: Dateien nicht gefunden", animated=False, striped=False)
        return None, None, data_source, *progress_values, [], None, [], None

    progress_values = update_progress(15, f"Dateien gefunden: {label}")
    data = get_cached_data(db_path, force=True)
    if data.is_empty():
        progress_values = update_progress(100, f"Keine Daten in {label}", animated=False, striped=False)
        return db_path, param_path, data_source, *progress_values, [], None, [], None
    progress_values = update_progress(30, "Datenbank geladen")

    progress_values = update_progress(90, "Bereite Benutzeroptionen vor...")
    users = [user for user in data.select(pl.col("user").unique()).to_series().to_list() if user != "users"] if not data.is_empty() else []
    left_user = 'user_1' if 'user_1' in users else users[0] if len(users) > 0 else None
    right_user = 'user_2' if 'user_2' in users else users[1] if len(users) > 1 else None
    options = [{'label': user, 'value': user} for user in users]

    progress_values = update_progress(100, f"Fertig: {label}", animated=False, striped=True)
    return db_path, param_path, data_source, *progress_values, options, left_user, options, right_user

@app.callback(
    [Output('db-path', 'data'), 
     Output('param-path', 'data'), 
     Output('data-source-badge', 'children'),
     Output('progress', 'value'),
     Output('progress', 'animated'), 
     Output('progress', 'striped'), 
     Output('progress', 'children'),
     Output('left-user-dropdown', 'options'), 
     Output('left-user-dropdown', 'value'),
     Output('right-user-dropdown', 'options'), 
     Output('right-user-dropdown', 'value')],
    [Input('browse-button', 'n_clicks'),
     Input('example-button', 'n_clicks'),
     Input('refresh-button', 'n_clicks'),
     Input('appdb-autoload', 'n_intervals')]
)
def update_paths(browse_clicks, example_clicks, refresh_clicks, autoload_intervals):
    """Updates database and parameter paths based on selected source."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return None, None, "Datenquelle: -", 0, False, False, "Verzeichnis auswählen", [], None, [], None

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id in ("appdb-autoload", "refresh-button"):
        db_path = get_app_database_path(PATH_TO_DATA)
        label = "app_database.db"
        force = trigger_id == "refresh-button"
        if db_path:
            preview = read_database(db_path)
            if preview.is_empty():
                example_db, example_param = find_latest_example_dataset(PATH_TO_DATA)
                if example_db and example_param:
                    label = f"Beispieldaten: {os.path.dirname(example_db)}"
                    return _load_dashboard_data(example_db, example_param, label, params_required=True)
        return _load_dashboard_data(db_path, None, label, params_required=False)

    if trigger_id == "browse-button":
        directory = browse_directory()
        if not directory:
            return None, None, "Datenquelle: -", 0, False, False, "Kein Verzeichnis ausgewählt", [], None, [], None
        db_path = get_app_database_path(directory)
        label = f"app_database.db ({directory})"
        return _load_dashboard_data(db_path, None, label, params_required=False)

    if trigger_id == "example-button":
        directory = browse_directory()
        if not directory:
            return None, None, "Datenquelle: -", 0, False, False, "Kein Verzeichnis ausgewählt", [], None, [], None
        db_path, param_path = find_latest_example_dataset(directory)
        label = os.path.dirname(db_path) if db_path else "Beispieldaten"
        return _load_dashboard_data(db_path, param_path, label, params_required=True)

    return None, None, "Datenquelle: -", 0, False, False, "Verzeichnis auswählen", [], None, [], None

@app.callback(
    Output('parameters-table', 'children'),
    [Input('param-path', 'data')]
)
def update_parameters_table(param_path):
    """Updates parameters table based on selected parameter file."""
    if param_path:
        parameters = read_parameters(param_path)
        if parameters:
            # Stil-Definitionen
            table_style = {
                'width': '100%',
                'border': '1px solid black',
                'border-collapse': 'collapse',
                'margin-bottom': '10px',
                'color': MODERN_COLORS['text'],
                'background-color': MODERN_COLORS['background'],
                'font-size': '0.9em'  # Kleinere Schriftgröße
            }
            header_style = {
                'backgroundColor': MODERN_COLORS['secondary'],
                'color': MODERN_COLORS['text'],
                'padding': '4px 6px',  # Reduziertes Padding
                'font-weight': 'bold',
                'text-align': 'center',
                'border': f'1px solid {MODERN_COLORS["accent"]}'
            }
            cell_style = {
                'border': f'1px solid {MODERN_COLORS["secondary"]}',
                'padding': '3px 6px',  # Reduziertes Padding
                'text-align': 'center'
            }
            
            # Container mit Flex-Layout
            return html.Div([
                # Kompakter Header mit Dropdown für Details
                dbc.Row([
                    dbc.Col([
                        html.H4("Generierungsparameter", style={
                            'color': MODERN_COLORS['text'],
                            'margin': '5px 0',
                            'display': 'inline-block'
                        }),
                        dbc.Button(
                            "Details ein/ausblenden",
                            id="toggle-params",
                            color="secondary",
                            size="sm",
                            className="ml-2",
                            style={'margin-left': '10px'}
                        )
                    ])
                ], className="mb-2"),
                
                # Collapse-Container für die Tabellen
                dbc.Collapse(
                    [
                        # Zwei-Spalten-Layout für die Tabellen
                        dbc.Row([
                            # Linke Spalte: General Parameters
                            dbc.Col([
                                html.Table(
                                    [
                                        html.Tr([
                                            html.Th(key.replace('_', ' ').title(), style=header_style)
                                            for key in parameters.get('user_specific_params', {}).get('user_1', {}).keys()
                                        ]),
                                        html.Tr([
                                            html.Td(str(value), style=cell_style)
                                            for value in [
                                                parameters.get('num_users'),
                                                parameters.get('storage_type'),
                                                parameters.get('start_date'),
                                                parameters.get('end_date')
                                            ]
                                        ])
                                    ],
                                    style=table_style
                                )
                            ], md=12, lg=12),
                            
                            # Rechte Spalte: User Parameters
                            dbc.Col([
                                html.Table(
                                    [
                                        # Header
                                        html.Tr([
                                            html.Th("User", style=header_style),
                                            *[html.Th(
                                                key.replace('_', ' ').title(), 
                                                style=header_style
                                            ) for key in parameters.get('user_specific_params', {}).get('user_1', {}).keys()]
                                        ]),
                                        # User Zeilen
                                        *[html.Tr([
                                            html.Th(user, style={**header_style, 'font-size': '0.9em'}),
                                            *[html.Td(
                                                str(config[key]), 
                                                style=cell_style
                                            ) for key in config.keys()]
                                        ]) for user, config in parameters.get('user_specific_params', {}).items()]
                                    ],
                                    style=table_style
                                )
                            ], md=12, lg=12)
                        ])
                    ],
                    id="collapse-params",
                    is_open=True
                )
            ])
            
        return html.Div("No parameters found.", style={'color': MODERN_COLORS['text']})
    return html.Div("Select a directory to load parameters.", style={'color': MODERN_COLORS['text']})

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
    Output('left-pie-chart', 'figure'),
    [Input('left-user-dropdown', 'value'),
     Input('db-path', 'data')]
)
def update_left_pie_chart(selected_user, db_path):
    """Updates the left pie chart based on the selected user."""
    if db_path and selected_user:
        data = get_cached_data(db_path)
        hours = get_cached_stat("hours_per_project", lambda: calculate_hours_per_project(data))
        left_pie_chart = plot_hours_per_project(hours, selected_user)
        return left_pie_chart
    else:
        return go.Figure(layout=go.Layout(plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background']))

@app.callback(
    Output('right-pie-chart', 'figure'),
    [Input('right-user-dropdown', 'value'),
     Input('db-path', 'data')]
)
def update_right_pie_chart(selected_user, db_path):
    """Updates the right pie chart based on the selected user."""
    if db_path and selected_user:
        data = get_cached_data(db_path)
        hours = get_cached_stat("hours_per_project", lambda: calculate_hours_per_project(data))
        right_pie_chart = plot_hours_per_project(hours, selected_user)
        return right_pie_chart
    else:
        return go.Figure(layout=go.Layout(plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background']))

@app.callback(
    Output('total-hours-chart', 'figure'),
    [Input('total-hours-chart', 'id'),
     Input('db-path', 'data')]
)
def update_total_hours_chart(_, db_path):
    """Updates the total hours chart."""
    if db_path:
        data = get_cached_data(db_path)
        total_hours, date_range = get_cached_stat("total_hours_per_user", lambda: calculate_total_hours_per_user(data))
        total_hours_chart = plot_total_hours_per_user(total_hours, date_range)
        return total_hours_chart
    else:
        return go.Figure(layout=go.Layout(plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background']))

@app.callback(
    Output('average-hours-per-user-chart', 'figure'),
    [Input('average-hours-per-user-chart', 'id'),
     Input('db-path', 'data')]
)
def update_average_hours_per_user_chart(_, db_path):
    """Updates the average hours per user chart."""
    if db_path:
        data = get_cached_data(db_path)
        average_hours = get_cached_stat("average_hours_per_user", lambda: calculate_average_hours_per_user(data))
        return plot_average_hours_per_user(average_hours)
    else:
        return go.Figure(layout=go.Layout(plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background']))

@app.callback(
    Output('average-hours-per-period-chart', 'figure'),
    [Input('db-path', 'data'),
     Input('update-period-button', 'n_clicks')],
    [State('period-days-input', 'value')]
)
def update_average_hours_per_period_chart(db_path, n_clicks, period_days):
    """Updates the average hours per period chart."""
    try:
        period_days = int(period_days)
        if period_days <= 0:
            return go.Figure(layout=go.Layout(title='Ungültiger Zeitraum: Bitte einen Wert größer als 0 eingeben',
                                  xaxis_title='Benutzer', yaxis_title='Durchschn. Stunden',
                                  plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
        if db_path:
            data = get_cached_data(db_path)
            key = f"average_hours_per_period_{period_days}"
            avg_period = get_cached_stat(key, lambda: calculate_average_hours_per_period(data, period_days))
            fig = plot_average_hours_per_period(avg_period, period_days)
            return fig
        else:
            return go.Figure(layout=go.Layout(plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background']))
    except ValueError:
        return go.Figure(layout=go.Layout(title='Ungültiger Zeitraum: Bitte eine gültige Zahl eingeben',
                              xaxis_title='Benutzer', yaxis_title='Durchschn. Stunden',
                              plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))

# Callback für alle Card-Toggles
@app.callback(
    Output({'type': 'collapse-card', 'index': MATCH}, 'is_open'),
    Input({'type': 'toggle-card', 'index': MATCH}, 'n_clicks'),
    State({'type': 'collapse-card', 'index': MATCH}, 'is_open'),
)
def toggle_card(n_clicks, is_open):
    """Toggle die Sichtbarkeit einer Card."""
    if n_clicks:
        return not is_open
    return is_open

@app.callback(
    [Output('project-stats-chart', 'figure'),
     Output('daily-hours-chart', 'figure'),
     Output('project-switches-chart', 'figure'),
     Output('pattern-user-dropdown', 'options')],
    [Input('db-path', 'data')]
)
def update_advanced_stats(db_path):
    """Aktualisiert die erweiterten Statistik-Visualisierungen."""
    empty_fig = go.Figure(layout=GRAPH_LAYOUT)
    empty_options = []
    
    if not db_path:
        return empty_fig, empty_fig, empty_fig, empty_options
    
    try:
        data = get_cached_data(db_path)
        
        # Projekt-Zeitstatistiken
        stats = get_cached_stat("project_time_stats", lambda: calculate_project_time_stats(data))
        stats_fig = plot_project_time_stats(stats)
        
        # Tägliche Projektstunden
        daily_hours = get_cached_stat("daily_project_hours", lambda: calculate_daily_project_hours(data))
        daily_fig = plot_daily_project_hours(daily_hours)
        
        # Projektwechsel
        switches = get_cached_stat("project_switches", lambda: calculate_project_switches(data))
        switches_fig = plot_project_switches(switches)
        
        # User-Optionen für Dropdown
        users = [{'label': user, 'value': user}
                 for user in data.select(pl.col("user").unique()).to_series().to_list()
                 if user != 'users']
        
        return stats_fig, daily_fig, switches_fig, users
        
    except Exception as e:
        print(f"Fehler beim Laden der erweiterten Statistiken: {e}")
        return empty_fig, empty_fig, empty_fig, empty_options

@app.callback(
    Output('daily-patterns-chart', 'figure'),
    [Input('db-path', 'data'),
     Input('pattern-user-dropdown', 'value')]
)
def update_daily_patterns(db_path, selected_users):
    """Aktualisiert die Visualisierung der tageszeitlichen Muster."""
    if db_path and selected_users:
        try:
            data = get_cached_data(db_path)
            if selected_users:
                data = data.filter(pl.col("user").is_in(selected_users))
            
            patterns = analyze_daily_patterns(data)
            return plot_daily_patterns(patterns)
            
        except Exception as e:
            print(f"Fehler beim Laden der Tagesmuster: {e}")
            return go.Figure(layout=GRAPH_LAYOUT)
    
    return go.Figure(layout=GRAPH_LAYOUT)

@app.callback(
    [Output('daily-trend-chart', 'figure'),
     Output('weekly-trend-chart', 'figure'),
     Output('weekday-pattern-chart', 'figure')],
    [Input('db-path', 'data')]
)
def update_time_series_analysis(db_path):
    """Aktualisiert die Zeitreihenanalyse-Visualisierungen."""
    empty_fig = go.Figure(layout=GRAPH_LAYOUT)
    
    if not db_path:
        return empty_fig, empty_fig, empty_fig
    
    try:
        data = get_cached_data(db_path)
        daily_df, weekly_avg, weekday_avg = get_cached_stat("time_series", lambda: analyze_time_series(data))
        daily_fig, weekly_fig, weekday_fig = plot_time_series_analysis(
            daily_df, weekly_avg, weekday_avg
        )
        return daily_fig, weekly_fig, weekday_fig
        
    except Exception as e:
        print(f"Fehler bei der Zeitreihenanalyse: {e}")
        return empty_fig, empty_fig, empty_fig

@app.callback(
    [Output('cluster-overview-chart', 'figure'),
     Output('cluster-profile-chart', 'figure')],
    [Input('db-path', 'data')]
)
def update_cluster_analysis(db_path):
    """Aktualisiert die Cluster-Analyse Visualisierungen."""
    empty_fig = go.Figure(layout=GRAPH_LAYOUT)
    
    if not db_path:
        return empty_fig, empty_fig
    
    try:
        data = get_cached_data(db_path)
        features_df, cluster_profiles = get_cached_stat("cluster_analysis", lambda: perform_cluster_analysis(data))
        if features_df is None or features_df.is_empty():
            return empty_fig, empty_fig
        overview_fig, profile_fig = plot_cluster_analysis(features_df, cluster_profiles)
        return overview_fig, profile_fig
        
    except Exception as e:
        print(f"Fehler bei der Cluster-Analyse: {e}")
        return empty_fig, empty_fig

@app.callback(
    [Output('regression-importance-chart', 'figure'),
     Output('regression-accuracy-chart', 'figure')],
    [Input('db-path', 'data')]
)
def update_regression_analysis(db_path):
    """Aktualisiert die Regressions-Analyse Visualisierungen."""
    empty_fig = go.Figure(layout=GRAPH_LAYOUT)
    
    if not db_path:
        return empty_fig, empty_fig
    
    try:
        data = get_cached_data(db_path)
        regression_results = get_cached_stat("regression_analysis", lambda: perform_regression_analysis(data))
        if not regression_results:
            return empty_fig, empty_fig
        importance_fig, accuracy_fig = plot_regression_analysis(regression_results)
        return importance_fig, accuracy_fig
        
    except Exception as e:
        print(f"Fehler bei der Regressions-Analyse: {e}")
        return empty_fig, empty_fig

@app.callback(
    [Output('anova-user-chart', 'figure'),
     Output('anova-project-chart', 'figure')],
    [Input('db-path', 'data')]
)
def update_anova_analysis(db_path):
    """Aktualisiert die ANOVA-Analyse Visualisierungen."""
    empty_fig = go.Figure(layout=GRAPH_LAYOUT)
    
    if not db_path:
        return empty_fig, empty_fig
    
    try:
        data = get_cached_data(db_path)
        anova_results = get_cached_stat("anova_analysis", lambda: perform_anova_analysis(data))
        if not anova_results:
            return empty_fig, empty_fig
        user_fig, project_fig = plot_anova_results(anova_results)
        return user_fig, project_fig
        
    except Exception as e:
        print(f"Fehler bei der ANOVA-Analyse: {e}")
        return empty_fig, empty_fig

def _find_available_port(start_port):
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port

if __name__ == '__main__':
    debug_mode = os.getenv("DASH_DEBUG", "0") == "1"
    base_port = int(os.getenv("DASH_PORT", "8052"))
    port = _find_available_port(base_port)
    if port != base_port:
        print(f"Port {base_port} in use, starting on {port} instead.")
    app.run(debug=debug_mode, use_reloader=False, port=port)
