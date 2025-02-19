import plotly.graph_objects as go
from utils import MODERN_COLORS, SYNTHWAVE_COLORS
import pandas as pd 

def plot_hours_per_project(hours, user):
    """Plots a pie chart of hours per project for a specific user."""
    user_data = hours[hours['user'] == user]
    fig = go.Figure(data=[go.Pie(labels=user_data['project'], values=user_data['total_hours'],
                                 marker_colors=[SYNTHWAVE_COLORS['blue'], SYNTHWAVE_COLORS['pink'], SYNTHWAVE_COLORS['yellow']])],
                    layout=go.Layout(title=f'Hours per Project for {user}', title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def plot_total_hours_per_user(total_hours, date_range):
    """Plots a bar chart of total hours per user."""
    if total_hours is None or total_hours.empty:
        fig = go.Figure(layout=go.Layout(title=f'No data available for Total Hours per User ({date_range})',
                      xaxis_title='User', yaxis_title='Total Hours',
                      plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
        return fig
    total_hours.loc[:, 'total_hours'] = pd.to_numeric(total_hours['total_hours'], errors='coerce').dropna()
    fig = go.Figure(data=[go.Bar(x=total_hours['user'], y=total_hours['total_hours'], marker_color=MODERN_COLORS['accent'])],
                    layout=go.Layout(title=f'Total Hours per User ({date_range})',
                                     xaxis_title='User', yaxis_title='Total Hours',
                                     title_font={"size": 18, "color": MODERN_COLORS['text'], "family": 'Arial, sans-serif'},
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def plot_average_hours_per_user(average_hours):
    """Plots a bar chart of average hours per user."""
    if average_hours is None or average_hours.empty:
        fig = go.Figure(layout=go.Layout(title=f'No data available for Average Hours per User',
                          xaxis_title='User', yaxis_title='Average Hours',
                          plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
        return fig
    average_hours.loc[:, 'average_hours'] = pd.to_numeric(average_hours['average_hours'], errors='coerce').dropna()
    fig =  go.Figure(data=[go.Bar(x=average_hours['user'], y=average_hours['average_hours'], marker_color=SYNTHWAVE_COLORS['pink'])],
                layout=go.Layout(title=f'Average Hours per User per Day',
                                 xaxis_title='User', yaxis_title='Average Hours',
                                 title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                 plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def plot_average_hours_per_period(average_hours, period_days):
    """Plots a bar chart of average hours per user for a given period in days."""
    fig = go.Figure(data=[go.Bar(x=average_hours['user'], y=average_hours['average_hours'], marker_color=SYNTHWAVE_COLORS['blue'])],
                    layout=go.Layout(title=f'Average Hours per User (Calculated over {period_days} day periods)',
                                     xaxis_title='User', yaxis_title='Average Hours',
                                     title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig
