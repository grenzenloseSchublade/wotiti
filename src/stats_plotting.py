import plotly.graph_objects as go
import polars as pl
from utils import MODERN_COLORS, SYNTHWAVE_COLORS

def _is_empty(df):
    return df is None or (isinstance(df, pl.DataFrame) and df.is_empty())

def plot_hours_per_project(hours, user):
    """Plots a pie chart of hours per project for a specific user."""
    if _is_empty(hours):
        return go.Figure()
    user_data = hours.filter(pl.col("user") == user)
    fig = go.Figure(data=[go.Pie(labels=user_data["project"].to_list(), values=user_data["total_hours"].to_list(),
                                 marker_colors=[SYNTHWAVE_COLORS['blue'], SYNTHWAVE_COLORS['pink'], SYNTHWAVE_COLORS['yellow']])],
                    layout=go.Layout(title=f'Hours per Project for {user}', title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def plot_total_hours_per_user(total_hours, date_range):
    """Plots a bar chart of total hours per user."""
    if _is_empty(total_hours):
        fig = go.Figure(layout=go.Layout(title=f'No data available for Total Hours per User ({date_range})',
                      xaxis_title='User', yaxis_title='Total Hours',
                      plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
        return fig
    total_hours = total_hours.with_columns(
        pl.col("total_hours").cast(pl.Float64, strict=False).alias("total_hours")
    ).drop_nulls("total_hours")
    fig = go.Figure(data=[go.Bar(x=total_hours["user"].to_list(), y=total_hours["total_hours"].to_list(), marker_color=MODERN_COLORS['accent'])],
                    layout=go.Layout(title=f'Total Hours per User ({date_range})',
                                     xaxis_title='User', yaxis_title='Total Hours',
                                     title_font={"size": 18, "color": MODERN_COLORS['text'], "family": 'Arial, sans-serif'},
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def plot_average_hours_per_user(average_hours):
    """Plots a bar chart of average hours per user."""
    if _is_empty(average_hours):
        fig = go.Figure(layout=go.Layout(title=f'No data available for Average Hours per User',
                          xaxis_title='User', yaxis_title='Average Hours',
                          plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
        return fig
    average_hours = average_hours.with_columns(
        pl.col("average_hours").cast(pl.Float64, strict=False).alias("average_hours")
    ).drop_nulls("average_hours")
    fig =  go.Figure(data=[go.Bar(x=average_hours["user"].to_list(), y=average_hours["average_hours"].to_list(), marker_color=SYNTHWAVE_COLORS['pink'])],
                layout=go.Layout(title=f'Average Hours per User per Day',
                                 xaxis_title='User', yaxis_title='Average Hours',
                                 title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                 plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def plot_average_hours_per_period(average_hours, period_days):
    """Plots a bar chart of average hours per user for a given period in days."""
    if _is_empty(average_hours):
        return go.Figure()
    fig = go.Figure(data=[go.Bar(x=average_hours["user"].to_list(), y=average_hours["average_hours"].to_list(), marker_color=SYNTHWAVE_COLORS['blue'])],
                    layout=go.Layout(title=f'Average Hours per User (Calculated over {period_days} day periods)',
                                     xaxis_title='User', yaxis_title='Average Hours',
                                     title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def plot_project_time_stats(stats):
    """Visualisiert Projekt-Zeitstatistiken."""
    fig = go.Figure()
    
    if _is_empty(stats):
        return fig

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
        title='Project Time Statistics (with Standard Deviation)',
        barmode='group',
        xaxis_title='Project',
        yaxis_title='Hours',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return fig

def plot_daily_project_hours(daily_hours):
    """Visualisiert tägliche Projektarbeitszeiten."""
    fig = go.Figure()
    
    if _is_empty(daily_hours):
        return fig

    for user in daily_hours["user"].unique().to_list():
        user_data = daily_hours.filter(pl.col("user") == user)
        
        fig.add_trace(go.Scatter(
            x=user_data["date"].to_list(),
            y=user_data["hours"].to_list(),
            mode='lines+markers',
            name=user,
            text=user_data["project"].to_list(),
            hovertemplate='%{text}<br>%{y:.1f} hours'
        ))
    
    fig.update_layout(
        title='Daily Project Hours',
        xaxis_title='Date',
        yaxis_title='Hours',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return fig

def plot_project_switches(switches):
    """Visualisiert Projektwechsel und Pausen."""
    fig = go.Figure()
    
    if _is_empty(switches):
        return fig

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
        title='Project Switch Patterns (Pause Duration)',
        yaxis_title='Pause Duration (minutes)',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return fig

def plot_daily_patterns(patterns):
    """Visualisiert tageszeitliche Arbeitsmuster."""
    fig = go.Figure()
    
    if _is_empty(patterns):
        return fig

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
        title='Daily Work Patterns (Average Start Times)',
        xaxis_title='Project',
        yaxis_title='Hour of Day',
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
        title='Daily Working Hours Trend',
        xaxis_title='Date',
        yaxis_title='Hours',
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
        title='Weekly Average Working Hours',
        xaxis_title='Calendar Week',
        yaxis_title='Average Hours',
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
        title='Average Working Hours by Weekday',
        xaxis_title='Weekday',
        yaxis_title='Average Hours',
        barmode='group',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return daily_fig, weekly_fig, weekday_fig

def plot_cluster_analysis(features_df, cluster_profiles):
    """Visualisiert die Ergebnisse der Clusteranalyse."""
    # Cluster-Übersicht
    overview_fig = go.Figure()
    
    if _is_empty(features_df):
        return overview_fig, go.Figure()

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
        title='User Clusters Overview',
        xaxis_title='Average Start Hour',
        yaxis_title='Switches per Day',
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
        title='Cluster Profiles',
        barmode='group',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return overview_fig, profile_fig

def plot_regression_analysis(regression_results):
    """Visualisiert die Ergebnisse der Regressionsanalyse."""
    # Feature Importance
    importance_fig = go.Figure()
    
    top_features = regression_results['importance'].head(10)
    importance_fig.add_trace(go.Bar(
        x=top_features["importance"].to_list(),
        y=top_features["feature"].to_list(),
        orientation='h'
    ))
    
    importance_fig.update_layout(
        title=f'Top 10 Predictors (R² = {regression_results["r2_score"]:.3f})',
        xaxis_title='Importance',
        yaxis_title='Feature',
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
        title='Actual vs Predicted Duration',
        xaxis_title='Actual Hours',
        yaxis_title='Predicted Hours',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return importance_fig, scatter_fig

def plot_anova_results(anova_results):
    """Visualisiert die Ergebnisse der ANOVA-Analyse."""
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
        title=f'User Differences (ANOVA p={anova_results["user_anova"]["p_value"]:.3f})',
        xaxis_title='User Pairs',
        yaxis_title='Mean Difference',
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
        title=f'Project Differences (ANOVA p={anova_results["project_anova"]["p_value"]:.3f})',
        xaxis_title='Project Pairs',
        yaxis_title='Mean Difference',
        plot_bgcolor=MODERN_COLORS['background'],
        paper_bgcolor=MODERN_COLORS['background'],
        font_color=MODERN_COLORS['text']
    )
    
    return user_fig, project_fig
