import plotly.graph_objects as go
import plotly.io as pio
import polars as pl
from utils import MODERN_COLORS, SYNTHWAVE_COLORS

# Modern color sequence for consistent multi-trace charts
COLOR_SEQUENCE = [
    '#8be9fd',  # cyan
    '#ff79c6',  # pink
    '#50fa7b',  # green
    '#ffb86c',  # orange
    '#bd93f9',  # purple
    '#f1fa8c',  # yellow
    '#ff5555',  # red
    '#6272a4',  # muted blue
]

# Custom Plotly template for all charts
_WOTITI_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font=dict(color=MODERN_COLORS['text'], family='Inter, Arial, sans-serif', size=13),
        title=dict(font=dict(size=16, color=MODERN_COLORS['text']), x=0.5, xanchor='center'),
        colorway=COLOR_SEQUENCE,
        xaxis=dict(gridcolor='#44475a', zerolinecolor='#44475a', title_font=dict(size=12),
                   automargin=True),
        yaxis=dict(gridcolor='#44475a', zerolinecolor='#44475a', title_font=dict(size=12),
                   automargin=True),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11)),
        margin=dict(l=60, r=30, t=60, b=50),
    )
)
pio.templates['wotiti'] = _WOTITI_TEMPLATE
pio.templates.default = 'wotiti'

def _is_empty(df):
    return df is None or (isinstance(df, pl.DataFrame) and df.is_empty())

def _empty_figure(title=""):
    """Returns a styled empty figure with a 'no data' message."""
    fig = go.Figure()
    fig.update_layout(
        title=title,
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text'],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    fig.add_annotation(
        text="Keine Daten verfügbar",
        xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=18, color=MODERN_COLORS['text']),
        opacity=0.5
    )
    return fig

def plot_hours_per_project(hours, user):
    """Plots a pie chart of hours per project for a specific user."""
    if _is_empty(hours):
        return _empty_figure("Stunden pro Projekt")
    user_data = hours.filter(pl.col("user") == user)
    fig = go.Figure(data=[go.Pie(labels=user_data["project"].to_list(), values=user_data["total_hours"].to_list(),
                                 marker_colors=[SYNTHWAVE_COLORS['blue'], SYNTHWAVE_COLORS['pink'], SYNTHWAVE_COLORS['yellow']])],
                    layout=go.Layout(title=f'Stunden pro Projekt \u2014 {user}', title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def plot_total_hours_per_user(total_hours, date_range):
    """Plots a bar chart of total hours per user."""
    if _is_empty(total_hours):
        fig = go.Figure(layout=go.Layout(title=f'Keine Daten \u2014 Gesamtstunden pro Benutzer ({date_range})',
                      xaxis_title='Benutzer', yaxis_title='Gesamtstunden',
                      plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
        return fig
    total_hours = total_hours.with_columns(
        pl.col("total_hours").cast(pl.Float64, strict=False).alias("total_hours")
    ).drop_nulls("total_hours")
    fig = go.Figure(data=[go.Bar(x=total_hours["user"].to_list(), y=total_hours["total_hours"].to_list(), marker_color=MODERN_COLORS['accent'])],
                    layout=go.Layout(title=f'Gesamtstunden pro Benutzer ({date_range})',
                                     xaxis_title='Benutzer', yaxis_title='Gesamtstunden',
                                     title_font={"size": 18, "color": MODERN_COLORS['text'], "family": 'Arial, sans-serif'},
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def plot_average_hours_per_user(average_hours):
    """Plots a bar chart of average hours per user."""
    if _is_empty(average_hours):
        fig = go.Figure(layout=go.Layout(title='Keine Daten \u2014 Durchschnittliche Stunden pro Tag',
                          xaxis_title='Benutzer', yaxis_title='Durchschn. Stunden',
                          plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
        return fig
    average_hours = average_hours.with_columns(
        pl.col("average_hours").cast(pl.Float64, strict=False).alias("average_hours")
    ).drop_nulls("average_hours")
    fig =  go.Figure(data=[go.Bar(x=average_hours["user"].to_list(), y=average_hours["average_hours"].to_list(), marker_color=SYNTHWAVE_COLORS['pink'])],
                layout=go.Layout(title='Durchschnittliche Stunden pro Tag und Benutzer',
                                 xaxis_title='Benutzer', yaxis_title='Durchschn. Stunden',
                                 title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                 plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def plot_average_hours_per_period(average_hours, period_days):
    """Plots a bar chart of average hours per user for a given period in days."""
    if _is_empty(average_hours):
        return _empty_figure(f"Durchschn. Stunden ({period_days}-Tage-Zeiträume)")
    fig = go.Figure(data=[go.Bar(x=average_hours["user"].to_list(), y=average_hours["average_hours"].to_list(), marker_color=SYNTHWAVE_COLORS['blue'])],
                    layout=go.Layout(title=f'Durchschnittliche Stunden ({period_days}-Tage-Zeiträume)',
                                     xaxis_title='Benutzer', yaxis_title='Durchschn. Stunden',
                                     title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def plot_project_time_stats(stats):
    """Visualisiert Projekt-Zeitstatistiken."""
    fig = go.Figure()
    
    if _is_empty(stats):
        return _empty_figure("Projektzeit-Statistiken")

    for user in stats["user"].unique().to_list():
        user_stats = stats.filter(pl.col("user") == user)
        
        fig.add_trace(go.Bar(
            name=f"{user} (Avg)",
            x=user_stats["project"].to_list(),
            y=user_stats["avg_hours"].to_list(),
            error_y=dict(
                type='data',
                array=user_stats["std_hours"].to_list(),
                visible=True
            )
        ))
        
    fig.update_layout(
        title='Projektzeit-Statistiken (mit Standardabweichung)',
        barmode='group',
        xaxis_title='Projekt',
        yaxis_title='Stunden',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return fig

def plot_daily_project_hours(daily_hours):
    """Visualisiert tägliche Projektarbeitszeiten."""
    fig = go.Figure()
    
    if _is_empty(daily_hours):
        return _empty_figure("Tägliche Projektstunden")

    for user in daily_hours["user"].unique().to_list():
        user_data = daily_hours.filter(pl.col("user") == user)
        
        fig.add_trace(go.Scatter(
            x=user_data["date"].to_list(),
            y=user_data["hours"].to_list(),
            mode='lines+markers',
            name=user,
            text=user_data["project"].to_list(),
            hovertemplate='%{text}<br>%{y:.1f} Stunden'
        ))
    
    fig.update_layout(
        title='Tägliche Projektstunden',
        xaxis_title='Datum',
        yaxis_title='Stunden',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return fig

def plot_project_switches(switches):
    """Visualisiert Projektwechsel und Pausen."""
    fig = go.Figure()
    
    if _is_empty(switches):
        return _empty_figure("Projektwechsel")

    for user in switches["user"].unique().to_list():
        user_switches = switches.filter(pl.col("user") == user)
        
        fig.add_trace(go.Box(
            y=user_switches["pause_minutes"].to_list(),
            name=user,
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.8
        ))
    
    fig.update_layout(
        title='Projektwechsel-Muster (Pausendauer)',
        yaxis_title='Pausendauer (Minuten)',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return fig

def plot_daily_patterns(patterns):
    """Visualisiert tageszeitliche Arbeitsmuster."""
    fig = go.Figure()
    
    if _is_empty(patterns):
        return _empty_figure("Arbeitsmuster")

    for user in patterns["user"].unique().to_list():
        user_patterns = patterns.filter(pl.col("user") == user)
        
        fig.add_trace(go.Scatter(
            x=user_patterns["project"].to_list(),
            y=user_patterns["avg_start_hour"].to_list(),
            mode='markers',
            name=f"{user} (Avg Start)",
            marker=dict(size=12)
        ))
    
    fig.update_layout(
        title='Arbeitsmuster (Durchschn. Startzeiten)',
        xaxis_title='Projekt',
        yaxis_title='Uhrzeit',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return fig

def plot_time_series_analysis(daily_df, weekly_avg, weekday_avg):
    """Erstellt Visualisierungen für die Zeitreihenanalyse."""
    # Täglicher Trend
    daily_fig = go.Figure()
    if not _is_empty(daily_df):
        for user in daily_df["user"].unique().to_list():
            user_data = daily_df.filter(pl.col("user") == user)
            daily_fig.add_trace(go.Scatter(
                x=user_data["date"].to_list(),
                y=user_data["hours"].to_list(),
                name=user,
                mode='lines+markers'
            ))
    daily_fig.update_layout(
        title='Täglicher Arbeitsstunden-Trend',
        xaxis_title='Datum',
        yaxis_title='Stunden',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    # Wöchentlicher Trend
    weekly_fig = go.Figure()
    if not _is_empty(weekly_avg):
        for user in weekly_avg["user"].unique().to_list():
            user_data = weekly_avg.filter(pl.col("user") == user)
            weekly_fig.add_trace(go.Scatter(
                x=user_data["week"].to_list(),
                y=user_data["hours"].to_list(),
                name=user,
                mode='lines+markers'
            ))
    weekly_fig.update_layout(
        title='Wöchentliche Durchschnittsstunden',
        xaxis_title='Kalenderwoche',
        yaxis_title='Durchschn. Stunden',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    # Wochentags-Muster
    weekday_fig = go.Figure()
    if not _is_empty(weekday_avg):
        for user in weekday_avg["user"].unique().to_list():
            user_data = weekday_avg.filter(pl.col("user") == user)
            weekday_fig.add_trace(go.Bar(
                x=user_data["weekday"].to_list(),
                y=user_data["hours"].to_list(),
                name=user
            ))
    weekday_fig.update_layout(
        title='Durchschnittliche Stunden nach Wochentag',
        xaxis_title='Wochentag',
        yaxis_title='Durchschn. Stunden',
        barmode='group',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return daily_fig, weekly_fig, weekday_fig

def plot_cluster_analysis(features_df, cluster_profiles):
    """Visualisiert die Ergebnisse der Clusteranalyse."""
    overview_fig = go.Figure()
    
    if _is_empty(features_df):
        return _empty_figure("Benutzer-Cluster Übersicht"), _empty_figure("Cluster-Profile")

    for cluster in features_df["cluster"].unique().to_list():
        cluster_data = features_df.filter(pl.col("cluster") == cluster)
        
        overview_fig.add_trace(go.Scatter(
            x=cluster_data["avg_start_hour"].to_list(),
            y=cluster_data["switches_per_day"].to_list(),
            mode='markers',
            name=f'Cluster {cluster}',
            text=cluster_data["user"].to_list(),
            marker=dict(
                size=[v * 5 for v in cluster_data["avg_duration"].to_list()],
                showscale=True
            )
        ))
    
    overview_fig.update_layout(
        title='Benutzer-Cluster Übersicht',
        xaxis_title='Durchschn. Startzeit',
        yaxis_title='Wechsel pro Tag',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    # Cluster-Profile
    profile_fig = go.Figure()
    
    for profile in cluster_profiles:
        profile_fig.add_trace(go.Bar(
            name=f'Cluster {profile["cluster"]}',
            x=['Avg Start', 'Avg Switches', 'Avg Duration'],
            y=[profile['avg_start'], profile['avg_switches'], profile['avg_duration']],
            text=[f'Users: {", ".join(profile["users"])}'],
            hoverinfo='text'
        ))
    
    profile_fig.update_layout(
        title='Cluster-Profile',
        barmode='group',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return overview_fig, profile_fig

def plot_regression_analysis(regression_results):
    """Visualisiert die Ergebnisse der Regressionsanalyse."""
    if not regression_results or 'importance' not in regression_results:
        return _empty_figure("Regressions-Analyse"), _empty_figure("Vorhersagegenauigkeit")

    # Feature Importance
    importance_fig = go.Figure()
    
    top_features = regression_results['importance'].head(10)
    importance_fig.add_trace(go.Bar(
        x=top_features["importance"].to_list(),
        y=top_features["feature"].to_list(),
        orientation='h'
    ))
    
    importance_fig.update_layout(
        title=f'Top 10 Prädiktoren (R² = {regression_results["r2_score"]:.3f})',
        xaxis_title='Wichtigkeit',
        yaxis_title='Merkmal',
        margin=dict(l=180),
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    # Actual vs Predicted
    scatter_fig = go.Figure()
    
    results = regression_results['actual_vs_predicted']
    scatter_fig.add_trace(go.Scatter(
        x=results["actual"].to_list(),
        y=results["predicted"].to_list(),
        mode='markers',
        marker=dict(color=SYNTHWAVE_COLORS['pink'])
    ))
    
    scatter_fig.update_layout(
        title='Tatsächliche vs. Vorhergesagte Dauer',
        xaxis_title='Tatsächliche Stunden',
        yaxis_title='Vorhergesagte Stunden',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return importance_fig, scatter_fig

def plot_anova_results(anova_results):
    """Visualisiert die Ergebnisse der ANOVA-Analyse."""
    if not anova_results or 'user_anova' not in anova_results:
        return _empty_figure("Benutzer-ANOVA"), _empty_figure("Projekt-ANOVA")

    # User ANOVA
    user_fig = go.Figure()
    
    user_table = anova_results['user_anova']['tukey']._results_table.data
    user_header = user_table[0]
    user_rows = user_table[1:]
    user_data = {col: [row[i] for row in user_rows] for i, col in enumerate(user_header)}
    
    user_err = user_data.get("std err", [0] * len(user_data.get("meandiff", [])))
    user_fig.add_trace(go.Bar(
        x=[f"{a} vs {b}" for a, b in zip(user_data['group1'], user_data['group2'])],
        y=user_data['meandiff'],
        error_y=dict(
            type='data',
            array=user_err,
            visible=True
        )
    ))
    
    user_fig.update_layout(
        title=f'Benutzer-Unterschiede (ANOVA p={anova_results["user_anova"]["p_value"]:.3f})',
        xaxis_title='Benutzer-Paare',
        xaxis_tickangle=-30,
        yaxis_title='Mittlere Differenz',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    # Project ANOVA
    project_fig = go.Figure()
    
    project_table = anova_results['project_anova']['tukey']._results_table.data
    project_header = project_table[0]
    project_rows = project_table[1:]
    project_data = {col: [row[i] for row in project_rows] for i, col in enumerate(project_header)}
    
    project_err = project_data.get("std err", [0] * len(project_data.get("meandiff", [])))
    project_fig.add_trace(go.Bar(
        x=[f"{a} vs {b}" for a, b in zip(project_data['group1'], project_data['group2'])],
        y=project_data['meandiff'],
        error_y=dict(
            type='data',
            array=project_err,
            visible=True
        )
    ))
    
    project_fig.update_layout(
        title=f'Projekt-Unterschiede (ANOVA p={anova_results["project_anova"]["p_value"]:.3f})',
        xaxis_title='Projekt-Paare',
        xaxis_tickangle=-30,
        yaxis_title='Mittlere Differenz',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return user_fig, project_fig
