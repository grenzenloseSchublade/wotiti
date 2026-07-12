from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import polars as pl

from utils import fmt_hours_hm, get_theme_colors

# Module-level theme state (initialized on first import, updated via apply_theme)
_colors, _sequence = get_theme_colors()


def build_plotly_template(colors: dict[str, str], sequence: list[str]) -> go.layout.Template:
    """Erstellt ein Plotly-Template aus dem gegebenen Farbschema."""
    return go.layout.Template(
        layout=go.Layout(
            plot_bgcolor=colors["background"],
            paper_bgcolor=colors["background"],
            font=dict(color=colors["text"], family="Inter, Arial, sans-serif", size=13),
            title=dict(font=dict(size=16, color=colors["text"]), x=0.5, xanchor="center"),
            colorway=sequence,
            xaxis=dict(
                gridcolor=colors["secondary"],
                zerolinecolor=colors["secondary"],
                title_font=dict(size=12),
                automargin=True,
            ),
            yaxis=dict(
                gridcolor=colors["secondary"],
                zerolinecolor=colors["secondary"],
                title_font=dict(size=12),
                automargin=True,
                tickformat=".2f",
                hoverformat=".2f",
            ),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
            margin=dict(l=60, r=30, t=60, b=50),
        )
    )


def apply_theme(theme_name: str | None = None) -> None:
    """Wendet ein Theme an und aktualisiert das Plotly-Template."""
    global _colors, _sequence
    _colors, _sequence = get_theme_colors(theme_name)
    pio.templates["wotiti"] = build_plotly_template(_colors, _sequence)
    pio.templates.default = "wotiti"


# Initialize default template
apply_theme()


def _is_empty(df: pl.DataFrame | None) -> bool:
    return df is None or (isinstance(df, pl.DataFrame) and df.is_empty())


def _empty_figure(title: str = "") -> go.Figure:
    """Returns a styled empty figure with a 'no data' message."""
    fig = go.Figure()
    fig.update_layout(
        title=title,
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    fig.add_annotation(
        text="Keine Daten verfügbar",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=18, color=_colors["text"]),
        opacity=0.5,
    )
    return fig


def _parse_date(d):
    """Parse a date value (str, datetime, date) into a date object."""
    from datetime import datetime as _dt

    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
            try:
                return _dt.strptime(d, fmt).date()
            except ValueError:
                continue
    elif hasattr(d, "date") and callable(d.date):
        return d.date()
    elif hasattr(d, "weekday"):
        return d
    return None


def _add_weekend_bands(fig: go.Figure, dates, *, weekend_included: bool = True) -> None:
    """Fügt dezente graue Bänder mit Sa/So-Labels für Wochenenden hinzu.

    Nur sichtbar, wenn ``weekend_included`` True ist (Toggle AN).
    Die Bänder decken den gesamten Datumsbereich inkl. Lücken ab.
    Zusammenhängende Wochenendtage (Sa+So) werden zu EINEM Band
    zusammengefasst (Sa 00:00 → Mo 00:00), damit über lange Zeiträume
    nicht Hunderte Layout-Shapes entstehen. Bei Zeiträumen über
    ~120 Tagen entfallen die Sa/So-Labels komplett.
    """
    from datetime import datetime as _dt
    from datetime import time as _time
    from datetime import timedelta

    if not weekend_included or not dates:
        return
    parsed = [p for d in dates if (p := _parse_date(d)) is not None]
    if not parsed:
        return
    d_min, d_max = min(parsed), max(parsed)
    show_labels = (d_max - d_min).days <= 120
    _WD_LABEL = {5: "Sa", 6: "So"}
    cursor = d_min
    while cursor <= d_max:
        if cursor.weekday() < 5:
            cursor += timedelta(days=1)
            continue
        # Wochenend-Lauf (Sa und/oder So) bestimmen und als EIN Band zeichnen.
        run_start = cursor
        run_end = cursor
        while run_end + timedelta(days=1) <= d_max and (run_end + timedelta(days=1)).weekday() >= 5:
            run_end += timedelta(days=1)
        # Band über volle Tage: 00:00 des ersten Tags bis 00:00 des Folgetags
        # (date ± timedelta(hours=12) wäre ein No-Op → unsichtbares Band).
        fig.add_vrect(
            x0=_dt.combine(run_start, _time.min),
            x1=_dt.combine(run_end + timedelta(days=1), _time.min),
            fillcolor="rgba(150,150,150,0.15)",
            line_width=0,
            layer="below",
        )
        if show_labels:
            day = run_start
            while day <= run_end:
                fig.add_annotation(
                    x=_dt.combine(day, _time(hour=12)),
                    y=1.0,
                    yref="paper",
                    text=_WD_LABEL[day.weekday()],
                    showarrow=False,
                    font=dict(size=10, color="rgba(150,150,150,0.85)", family="Arial"),
                    yanchor="bottom",
                    xanchor="center",
                )
                day += timedelta(days=1)
        cursor = run_end + timedelta(days=1)


def plot_hours_per_project(hours: pl.DataFrame | None, user: str) -> go.Figure:
    """Plots a pie chart of hours per project for a specific user."""
    if _is_empty(hours):
        return _empty_figure("Stunden pro Projekt")
    user_data = hours.filter(pl.col("user") == user)
    if _is_empty(user_data):
        return _empty_figure(f"Stunden pro Projekt — {user}")
    labels = user_data["project"].to_list()
    # Volle Palette zyklisch über die Projektanzahl (statt fix 3 Farben).
    colors = [_sequence[i % len(_sequence)] for i in range(len(labels))]
    vals = user_data["total_hours"].to_list()
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=[round(v, 2) for v in vals],
                marker_colors=colors,
                # H:MM wie in der App (statt Dezimalstunden), vorformatiert via customdata
                customdata=[fmt_hours_hm(v) for v in vals],
                hovertemplate="%{label}: %{customdata} (%{percent})<extra></extra>",
            )
        ],
        layout=go.Layout(
            title=f"Stunden pro Projekt \u2014 {user}",
            title_font=dict(size=18, color=_colors["text"], family="Arial, sans-serif"),
            plot_bgcolor=_colors["background"],
            paper_bgcolor=_colors["background"],
            font_color=_colors["text"],
        ),
    )
    return fig


def plot_total_hours_per_user(total_hours: pl.DataFrame | None, date_range: str) -> go.Figure:
    """Plots a bar chart of total hours per user."""
    if _is_empty(total_hours):
        fig = go.Figure(
            layout=go.Layout(
                title=f"Keine Daten \u2014 Gesamtstunden pro Benutzer ({date_range})",
                xaxis_title="Benutzer",
                yaxis_title="Gesamtstunden",
                plot_bgcolor=_colors["background"],
                paper_bgcolor=_colors["background"],
                font_color=_colors["text"],
            )
        )
        return fig
    total_hours = total_hours.with_columns(
        pl.col("total_hours").cast(pl.Float64, strict=False).alias("total_hours")
    ).drop_nulls("total_hours")
    vals = total_hours["total_hours"].to_list()
    hm = [fmt_hours_hm(v) for v in vals]  # H:MM wie in der App
    fig = go.Figure(
        data=[
            go.Bar(
                x=total_hours["user"].to_list(),
                y=vals,
                marker_color=_colors["accent"],
                text=hm,
                textposition="auto",
                customdata=hm,
                hovertemplate="%{x}: %{customdata}<extra></extra>",
            )
        ],
        layout=go.Layout(
            title=f"Gesamtstunden pro Benutzer ({date_range})",
            xaxis_title="Benutzer",
            yaxis_title="Gesamtstunden",
            title_font={"size": 18, "color": _colors["text"], "family": "Arial, sans-serif"},
            plot_bgcolor=_colors["background"],
            paper_bgcolor=_colors["background"],
            font_color=_colors["text"],
        ),
    )
    return fig


def plot_average_hours_per_user(average_hours: pl.DataFrame | None) -> go.Figure:
    """Plots a bar chart of average hours per user."""
    if _is_empty(average_hours):
        fig = go.Figure(
            layout=go.Layout(
                title="Keine Daten \u2014 Durchschnittliche Stunden pro Tag",
                xaxis_title="Benutzer",
                yaxis_title="Durchschn. Stunden",
                plot_bgcolor=_colors["background"],
                paper_bgcolor=_colors["background"],
                font_color=_colors["text"],
            )
        )
        return fig
    average_hours = average_hours.with_columns(
        pl.col("average_hours").cast(pl.Float64, strict=False).alias("average_hours")
    ).drop_nulls("average_hours")
    vals = average_hours["average_hours"].to_list()
    hm = [fmt_hours_hm(v) for v in vals]  # H:MM wie in der App
    fig = go.Figure(
        data=[
            go.Bar(
                x=average_hours["user"].to_list(),
                y=vals,
                marker_color=_sequence[1] if len(_sequence) > 1 else _sequence[0],
                text=hm,
                textposition="auto",
                customdata=hm,
                hovertemplate="%{x}: %{customdata}<extra></extra>",
            ),
        ],
        layout=go.Layout(
            title="Durchschnittliche Stunden pro Tag und Benutzer",
            xaxis_title="Benutzer",
            yaxis_title="Durchschn. Stunden",
            title_font=dict(size=18, color=_colors["text"], family="Arial, sans-serif"),
            plot_bgcolor=_colors["background"],
            paper_bgcolor=_colors["background"],
            font_color=_colors["text"],
        ),
    )
    return fig


def plot_average_hours_per_period(average_hours: pl.DataFrame | None, period_days: int) -> go.Figure:
    """Plots a bar chart of average hours per user for a given period in days."""
    if _is_empty(average_hours):
        return _empty_figure(f"Durchschn. Stunden ({period_days}-Tage-Zeiträume)")
    vals = average_hours["average_hours"].to_list()
    hm = [fmt_hours_hm(v) for v in vals]  # H:MM wie in der App
    fig = go.Figure(
        data=[
            go.Bar(
                x=average_hours["user"].to_list(),
                y=vals,
                marker_color=_sequence[0],
                text=hm,
                textposition="auto",
                customdata=hm,
                hovertemplate="%{x}: %{customdata}<extra></extra>",
            ),
        ],
        layout=go.Layout(
            title=f"Durchschnittliche Stunden ({period_days}-Tage-Zeiträume)",
            xaxis_title="Benutzer",
            yaxis_title="Durchschn. Stunden",
            title_font=dict(size=18, color=_colors["text"], family="Arial, sans-serif"),
            plot_bgcolor=_colors["background"],
            paper_bgcolor=_colors["background"],
            font_color=_colors["text"],
        ),
    )
    return fig


def plot_project_time_stats(stats: pl.DataFrame | None) -> go.Figure:
    """Visualisiert Projekt-Zeitstatistiken."""
    fig = go.Figure()

    if _is_empty(stats):
        return _empty_figure("Projektzeit-Statistiken")

    # Sortierte User-Reihenfolge → stabile Legenden/Farben über Requests hinweg
    for user in sorted(stats["user"].unique().to_list()):
        user_stats = stats.filter(pl.col("user") == user)

        fig.add_trace(
            go.Bar(
                name=f"{user} (Avg)",
                x=user_stats["project"].to_list(),
                y=user_stats["avg_hours"].to_list(),
                error_y=dict(type="data", array=user_stats["std_hours"].to_list(), visible=True),
            )
        )

    fig.update_layout(
        title="Projektzeit-Statistiken (mit Standardabweichung)",
        barmode="group",
        xaxis_title="Projekt",
        yaxis_title="Stunden",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )

    return fig


def plot_daily_project_hours(daily_hours: pl.DataFrame | None, *, weekend_included: bool = False) -> go.Figure:
    """Visualisiert tägliche Projektarbeitszeiten."""
    fig = go.Figure()

    if _is_empty(daily_hours):
        return _empty_figure("Tägliche Projektstunden")

    # Eine Linie pro (User, Projekt), nach Datum sortiert — sonst läuft die
    # Linie rückwärts durch die Zeit (Zeilen kommen in Projekt-Blöcken) und
    # zickzackt an Tagen mit mehreren Projekten.
    users = sorted(daily_hours["user"].unique().to_list())
    multi_user = len(users) > 1
    for user in users:
        user_data = daily_hours.filter(pl.col("user") == user)
        for project in sorted(user_data["project"].unique().to_list()):
            proj_data = user_data.filter(pl.col("project") == project).sort("date")
            hrs = proj_data["hours"].to_list()
            fig.add_trace(
                go.Scatter(
                    x=proj_data["date"].to_list(),
                    y=hrs,
                    mode="lines+markers",
                    # Bei nur einem User zeigt die Legende direkt die Projekte
                    name=f"{user} · {project}" if multi_user else project,
                    customdata=[fmt_hours_hm(h) for h in hrs],
                    hovertemplate="%{x|%a %d.%m.%Y} — %{customdata}<extra>%{fullData.name}</extra>",
                )
            )

    fig.update_layout(
        title="Tägliche Projektstunden",
        xaxis_title="Datum",
        xaxis_tickformat="%a %d.%m",
        xaxis_dtick=86400000,
        xaxis_tickangle=-45,
        yaxis_title="Stunden",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )

    _add_weekend_bands(fig, daily_hours["date"].to_list(), weekend_included=weekend_included)

    return fig


def plot_project_switches(switches: pl.DataFrame | None) -> go.Figure:
    """Visualisiert Projektwechsel und Pausen."""
    fig = go.Figure()

    if _is_empty(switches):
        return _empty_figure("Projektwechsel")

    for user in sorted(switches["user"].unique().to_list()):
        user_switches = switches.filter(pl.col("user") == user)

        fig.add_trace(
            go.Box(y=user_switches["pause_minutes"].to_list(), name=user, boxpoints="all", jitter=0.3, pointpos=-1.8)
        )

    fig.update_layout(
        title="Pausendauer zwischen Projektwechseln",
        yaxis_title="Pausendauer (Minuten)",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )

    return fig


def plot_daily_patterns(patterns: pl.DataFrame | None) -> go.Figure:
    """Visualisiert tageszeitliche Arbeitsmuster."""
    fig = go.Figure()

    if _is_empty(patterns):
        return _empty_figure("Arbeitsmuster")

    for user in sorted(patterns["user"].unique().to_list()):
        user_patterns = patterns.filter(pl.col("user") == user)

        fig.add_trace(
            go.Scatter(
                x=user_patterns["project"].to_list(),
                y=user_patterns["avg_start_hour"].to_list(),
                mode="markers",
                name=f"{user} (Avg Start)",
                marker=dict(size=12),
            )
        )

    fig.update_layout(
        title="Arbeitsmuster (Durchschn. Startzeiten)",
        xaxis_title="Projekt",
        yaxis_title="Startzeit (Stunde)",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )

    return fig


def plot_time_series_analysis(
    daily_df: pl.DataFrame | None,
    weekly_avg: pl.DataFrame | None,
    weekday_avg: pl.DataFrame | None,
    *,
    weekend_included: bool = False,
) -> tuple[go.Figure, go.Figure, go.Figure]:
    """Erstellt Visualisierungen für die Zeitreihenanalyse."""
    # Täglicher Trend
    daily_fig = go.Figure()
    if not _is_empty(daily_df):
        for user in sorted(daily_df["user"].unique().to_list()):
            user_data = daily_df.filter(pl.col("user") == user)
            hrs = user_data["hours"].to_list()
            daily_fig.add_trace(
                go.Scatter(
                    x=user_data["date"].to_list(),
                    y=hrs,
                    name=user,
                    mode="lines+markers",
                    customdata=[fmt_hours_hm(h) for h in hrs],
                    hovertemplate="%{x|%a %d.%m.%Y}<br>%{customdata}<extra>%{fullData.name}</extra>",
                )
            )
    daily_fig.update_layout(
        title="Täglicher Arbeitsstunden-Trend",
        xaxis_title="Datum",
        xaxis_tickformat="%a %d.%m",
        xaxis_dtick=86400000,
        xaxis_tickangle=-45,
        yaxis_title="Stunden",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )
    if not _is_empty(daily_df):
        _add_weekend_bands(daily_fig, daily_df["date"].to_list(), weekend_included=weekend_included)

    # Wöchentlicher Trend
    weekly_fig = go.Figure()
    weeks_are_labels = False  # True, wenn Wochen bereits als "YYYY-KWnn"-Labels vorliegen
    if not _is_empty(weekly_avg):
        weeks_are_labels = weekly_avg["week"].dtype == pl.Utf8
        for user in sorted(weekly_avg["user"].unique().to_list()):
            user_data = weekly_avg.filter(pl.col("user") == user)
            hrs = user_data["hours"].to_list()
            weekly_fig.add_trace(
                go.Scatter(
                    x=user_data["week"].to_list(),
                    y=hrs,
                    name=user,
                    mode="lines+markers",
                    customdata=[fmt_hours_hm(h) for h in hrs],
                    hovertemplate="%{x}: %{customdata}<extra>%{fullData.name}</extra>",
                )
            )
    weekly_fig.update_layout(
        title="Wöchentliche Durchschnittsstunden",
        xaxis_title="Kalenderwoche",
        # Bei fertigen "YYYY-KWnn"-Labels kein zusätzliches "KW "-Präfix
        xaxis_tickprefix="" if weeks_are_labels else "KW ",
        yaxis_title="Durchschn. Stunden",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )

    # Wochentags-Muster
    _WE_DAYS = {"Sa", "So"}
    _WD_ORDER = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    weekday_fig = go.Figure()
    if not _is_empty(weekday_avg):
        # Optionale Stichproben-Spalte 'n_days' (Anzahl gearbeiteter Tage) im
        # Hover anzeigen — macht n=1- vs n=12-Durchschnitte unterscheidbar.
        has_n = "n_days" in weekday_avg.columns
        for user in sorted(weekday_avg["user"].unique().to_list()):
            user_data = weekday_avg.filter(pl.col("user") == user)
            days = user_data["weekday"].to_list()
            hrs = user_data["hours"].to_list()
            hm = [fmt_hours_hm(h) for h in hrs]
            has_weekend = any(d in _WE_DAYS for d in days)
            if has_n:
                customdata = list(zip(hm, user_data["n_days"].to_list(), strict=True))
                hover = "%{x}: %{customdata[0]}<br>n=%{customdata[1]} Tage<extra>%{fullData.name}</extra>"
            else:
                customdata = hm
                hover = "%{x}: %{customdata}<extra>%{fullData.name}</extra>"
            bar_kwargs = dict(
                x=days,
                y=hrs,
                name=user,
                text=hm,
                textposition="auto",
                customdata=customdata,
                hovertemplate=hover,
            )
            if has_weekend:
                bar_kwargs["marker_color"] = ["rgba(150,150,150,0.5)" if d in _WE_DAYS else _sequence[0] for d in days]
            weekday_fig.add_trace(go.Bar(**bar_kwargs))
    weekday_fig.update_layout(
        title="Durchschnittliche Stunden nach Wochentag",
        # Feste Mo–So-Reihenfolge — sonst bestimmt die erste Trace die
        # Kategorien und die Achse startet z. B. bei "Mi".
        xaxis=dict(title="Wochentag", categoryorder="array", categoryarray=_WD_ORDER),
        yaxis_title="Durchschn. Stunden",
        barmode="group",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )

    return daily_fig, weekly_fig, weekday_fig


def plot_cluster_analysis(
    features_df: pl.DataFrame | None, cluster_profiles: list[dict]
) -> tuple[go.Figure, go.Figure]:
    """Visualisiert die Ergebnisse der Clusteranalyse."""
    overview_fig = go.Figure()

    if _is_empty(features_df):
        return _empty_figure("Benutzer-Cluster Übersicht"), _empty_figure("Cluster-Profile")

    for cluster in sorted(features_df["cluster"].unique().to_list()):
        cluster_data = features_df.filter(pl.col("cluster") == cluster)

        overview_fig.add_trace(
            go.Scatter(
                x=cluster_data["avg_start_hour"].to_list(),
                y=cluster_data["switches_per_day"].to_list(),
                mode="markers",
                name=f"Cluster {cluster}",
                text=cluster_data["user"].to_list(),
                marker=dict(size=[v * 5 for v in cluster_data["avg_duration"].to_list()], showscale=True),
            )
        )

    overview_fig.update_layout(
        title="Benutzer-Cluster Übersicht (Blasengröße = Ø Dauer)",
        xaxis_title="Durchschn. Startzeit",
        yaxis_title="Wechsel pro Tag",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )

    # Cluster-Profile
    profile_fig = go.Figure()

    for profile in cluster_profiles:
        profile_fig.add_trace(
            go.Bar(
                name=f"Cluster {profile['cluster']}",
                x=["Ø Startzeit", "Ø Wechsel", "Ø Dauer"],
                y=[profile["avg_start"], profile["avg_switches"], profile["avg_duration"]],
                text=[f"Benutzer: {', '.join(profile['users'])}"],
                hoverinfo="text",
            )
        )

    profile_fig.update_layout(
        title="Cluster-Profile",
        barmode="group",
        xaxis_title="Kennzahl",
        yaxis_title="Wert",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )

    return overview_fig, profile_fig


def plot_regression_analysis(regression_results: dict | None) -> tuple[go.Figure, go.Figure]:
    """Visualisiert die Ergebnisse der Regressionsanalyse."""
    if not regression_results or "importance" not in regression_results:
        return _empty_figure("Regressions-Analyse"), _empty_figure("Vorhersagegenauigkeit")

    # Feature Importance
    importance_fig = go.Figure()

    top_features = regression_results["importance"].head(10)
    importance_fig.add_trace(
        go.Bar(x=top_features["importance"].to_list(), y=top_features["feature"].to_list(), orientation="h")
    )

    importance_fig.update_layout(
        title=f"Top 10 Prädiktoren (R² = {regression_results['r2_score']:.3f})",
        xaxis_title="Wichtigkeit",
        yaxis_title="Merkmal",
        margin=dict(l=180),
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )

    # Actual vs Predicted
    scatter_fig = go.Figure()

    results = regression_results["actual_vs_predicted"]
    scatter_fig.add_trace(
        go.Scatter(
            x=results["actual"].to_list(),
            y=results["predicted"].to_list(),
            mode="markers",
            marker=dict(color=_sequence[1] if len(_sequence) > 1 else _sequence[0]),
        )
    )

    scatter_fig.update_layout(
        title="Tatsächliche vs. Vorhergesagte Dauer",
        xaxis_title="Tatsächliche Stunden",
        yaxis_title="Vorhergesagte Stunden",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )

    return importance_fig, scatter_fig


def _plot_anova_tukey(result: dict, title: str, xaxis_title: str) -> go.Figure:
    """Balkendiagramm der Tukey-Paardifferenzen eines ANOVA-Ergebnisses."""
    fig = go.Figure()
    table = result["tukey"]._results_table.data
    header = table[0]
    rows = table[1:]
    data = {col: [row[i] for row in rows] for i, col in enumerate(header)}
    err = data.get("std err", [0] * len(data.get("meandiff", [])))
    fig.add_trace(
        go.Bar(
            x=[f"{a} vs {b}" for a, b in zip(data["group1"], data["group2"], strict=False)],
            y=data["meandiff"],
            error_y=dict(type="data", array=err, visible=True),
        )
    )
    fig.update_layout(
        title=f"{title} (ANOVA p={result['p_value']:.3f}, explorativ)",
        xaxis_title=xaxis_title,
        xaxis_tickangle=-30,
        yaxis_title="Mittlere Differenz",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )
    return fig


def plot_anova_results(anova_results: dict | None) -> tuple[go.Figure, go.Figure]:
    """Visualisiert die ANOVA-Ergebnisse.

    Die Keys sind seit v2.3.0 unabhängig: ``user_anova`` existiert nur bei
    ≥2 Benutzern, ``project_anova`` nur bei ≥2 Projekten — im Single-User-
    Betrieb kommt typischerweise NUR ``project_anova`` an.
    """
    anova_results = anova_results or {}
    if "user_anova" in anova_results:
        user_fig = _plot_anova_tukey(anova_results["user_anova"], "Benutzer-Unterschiede", "Benutzer-Paare")
    else:
        user_fig = _empty_figure("Benutzer-ANOVA (braucht ≥2 Benutzer)")
    if "project_anova" in anova_results:
        project_fig = _plot_anova_tukey(anova_results["project_anova"], "Projekt-Unterschiede", "Projekt-Paare")
    else:
        project_fig = _empty_figure("Projekt-ANOVA (braucht ≥2 Projekte)")
    return user_fig, project_fig


# ---------------------------------------------------------------------------
# Zusätzliche Diagramme: Pausen, Heatmap, Verteilungen
# ---------------------------------------------------------------------------
def plot_break_analysis(break_stats: dict | None) -> go.Figure:
    """Gestapelte Balken Arbeits- vs. Pausenstunden pro Tag (+ Verhältnis im Titel)."""
    if not break_stats or _is_empty(break_stats.get("per_day")):
        return _empty_figure("Pausen-Analyse")
    per_day = break_stats["per_day"]
    totals = break_stats.get("totals", {})
    dates = per_day["date"].to_list()
    work_hrs = per_day["work_hours"].to_list()
    break_hrs = per_day["break_hours"].to_list()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=dates,
            y=work_hrs,
            name="Arbeit",
            marker_color=_sequence[0],
            customdata=[fmt_hours_hm(h) for h in work_hrs],
            hovertemplate="%{x}: %{customdata} Arbeit<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=dates,
            y=break_hrs,
            name="Pause",
            marker_color=_sequence[1] if len(_sequence) > 1 else _colors["accent"],
            customdata=[fmt_hours_hm(h) for h in break_hrs],
            hovertemplate="%{x}: %{customdata} Pause<extra></extra>",
        )
    )
    ratio_pct = totals.get("ratio", 0.0) * 100
    fig.update_layout(
        title=f"Arbeit vs. Pause pro Tag (Pausenanteil {ratio_pct:.0f}%)",
        barmode="stack",
        xaxis_title="Datum",
        yaxis_title="Stunden",
        yaxis=dict(rangemode="tozero"),
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )
    return fig


def plot_hour_heatmap(matrix: pl.DataFrame | None) -> go.Figure:
    """Heatmap der Arbeitsstunden je Wochentag (Y) × Tagesstunde (X)."""
    if _is_empty(matrix):
        return _empty_figure("Aktivitäts-Heatmap")
    wd_labels = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    grid = [[0.0 for _ in range(24)] for _ in range(7)]
    for row in matrix.iter_rows(named=True):
        wd = int(row["weekday"])
        hr = int(row["hour"])
        if 0 <= wd <= 6 and 0 <= hr <= 23:
            grid[wd][hr] = round(float(row["hours"]), 2)
    fig = go.Figure(
        data=go.Heatmap(
            z=grid,
            x=[f"{h:02d}" for h in range(24)],
            y=wd_labels,
            colorscale="Viridis",
            colorbar=dict(title="Stunden"),
            hovertemplate="%{y} %{x}:00 — %{z:.2f} h<extra></extra>",
        )
    )
    fig.update_layout(
        title="Aktivitäts-Heatmap (Wochentag × Stunde)",
        xaxis_title="Tagesstunde",
        yaxis_title="Wochentag",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )
    return fig


def plot_start_hour_distribution(dist: pl.DataFrame | None) -> go.Figure:
    """Balkendiagramm der Häufigkeit von Start-Uhrzeiten (0..23)."""
    if _is_empty(dist):
        return _empty_figure("Startzeit-Verteilung")
    counts = {int(r["hour"]): int(r["count"]) for r in dist.iter_rows(named=True)}
    x = list(range(24))
    y = [counts.get(h, 0) for h in x]
    fig = go.Figure(data=[go.Bar(x=[f"{h:02d}" for h in x], y=y, marker_color=_sequence[0])])
    fig.update_layout(
        title="Verteilung der Start-Uhrzeiten",
        xaxis_title="Stunde",
        yaxis_title="Anzahl Starts",
        yaxis=dict(rangemode="tozero"),
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )
    return fig


def plot_session_duration_distribution(dist: pl.DataFrame | None) -> go.Figure:
    """Histogramm der Session-Dauern (Stunden)."""
    if _is_empty(dist):
        return _empty_figure("Session-Dauer-Verteilung")
    fig = go.Figure(
        data=[
            go.Histogram(
                x=dist["duration_hours"].to_list(),
                marker_color=_sequence[1] if len(_sequence) > 1 else _sequence[0],
                hovertemplate="%{x:.1f} h: %{y} Sessions<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="Verteilung der Session-Dauern",
        xaxis_title="Dauer (Stunden)",
        yaxis_title="Anzahl Sessions",
        plot_bgcolor=_colors["background"],
        paper_bgcolor=_colors["background"],
        font_color=_colors["text"],
    )
    return fig
