import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
from stats_helper import read_database, save_to_csv

from config import PATH_TO_DATA

# TODO Do statistics on data: wotiti/data/20250214-010326 (1 month)
# 

# 1. **Datenaufbereitung**: Pandas + NumPy.  
# 2. **Statistische Analyse**: SciPy/StatsModels für Hypothesentests, Scikit-learn für ML-Modelle.  
# 3. **Visualisierung**:  
#    - **Einfache Plots**: Seaborn/Matplotlib.  
#    - **Interaktivität**: Plotly + Dash für Dashboards .  



# Calculations
def calculate_total_duration(data):
    """Calculate the total duration for each user and project."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'project', 'timestamp'])
    
    durations = []
    for user, group in data.groupby('user'):
        for project, project_group in group.groupby('project'):
            start_times = project_group[project_group['event_type'] == 'start']['timestamp']
            stop_times = project_group[project_group['event_type'] == 'stop']['timestamp']
            total_duration = (stop_times.values - start_times.values).sum().astype('timedelta64[s]').astype(int)
            durations.append({'user': user, 'project': project, 'total_duration': total_duration})
    
    return pd.DataFrame(durations)

# Visualizations
def plot_total_duration(durations):
    """Plot the total duration for each user and project."""
    fig = px.bar(durations, x='user', y='total_duration', color='project', title='Total Duration per User and Project')
    return fig

def plot_duration_over_time(data):
    """Plot the duration over time for each user and project."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'project', 'timestamp'])
    
    fig = go.Figure()
    for user, group in data.groupby('user'):
        for project, project_group in group.groupby('project'):
            start_times = project_group[project_group['event_type'] == 'start']['timestamp']
            stop_times = project_group[project_group['event_type'] == 'stop']['timestamp']
            durations = (stop_times.values - start_times.values).astype('timedelta64[s]').astype(int)
            fig.add_trace(go.Scatter(x=start_times, y=durations, mode='lines+markers', name=f'{user} - {project}'))
    
    fig.update_layout(title='Duration Over Time', xaxis_title='Time', yaxis_title='Duration (seconds)')
    return fig

# Dash App
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Work Time Tracker Statistics"),
    dcc.Graph(id='total-duration-graph'),
    dcc.Graph(id='duration-over-time-graph')
])

@app.callback(
    [Output('total-duration-graph', 'figure'),
     Output('duration-over-time-graph', 'figure')],
    [Input('total-duration-graph', 'id')]
)
def update_graphs(_):

    path_to_db = PATH_TO_DATA + "/20250214-010326/generate_database.db"
    data = read_database(path_to_db)
    durations = calculate_total_duration(data)
    total_duration_fig = plot_total_duration(durations)
    duration_over_time_fig = plot_duration_over_time(data)
    return total_duration_fig, duration_over_time_fig

if __name__ == '__main__':
    app.run_server(debug=True)
