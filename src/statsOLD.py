import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
from stats_helper import read_database, save_to_csv

from config import PATH_TO_DATA
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import LabelEncoder
import numpy as np
import json

# TODO Do statistics on data: wotiti/data/20250214-010326 (1 month)
# 
## Vorgehen
# 1. **Datenaufbereitung**: Pandas + NumPy.  
# 2. **Statistische Analyse**: SciPy/StatsModels für Hypothesentests, Scikit-learn für ML-Modelle.  
# 3. **Visualisierung**:  
#    - **Einfache Plots**: Seaborn/Matplotlib.  
#    - **Interaktivität**: Plotly + Dash für Dashboards .  

## Was möchte ich kalkulieren?
# Jeweils Pro Woche, pro monat, pro jahr

# Triviale Berechnungen
# - Total Duration per User
# - Total Duration per Project
# - Duration Over Time per User and Project
# Triviale Zusammenhänge
# - logistische Regression: User -> Project
# - logistische Regression: Project -> User
# - lineare Regression: Duration -> User
# - lineare Regression: Duration -> Project
# - lineare Regression: Duration -> User + Project
# - lineare Regression: Duration -> User * Project
# - etc. 
# Komplexe Berechnungen und Zusammenhänge
# - Wann wurde jeweils von user gearbeitet?
# - Wann wurde jeweils an project gearbeitet?
# - Wann wurde jeweils von user an project gearbeitet?
# - Wie lange wurde jeweils von user gearbeitet?
# - Wie oft wurde jeweils von user an project gearbeitet?

# Calculations

def read_parameters(file_path):
    """Read parameters from a JSON file."""
    with open(file_path, 'r') as file:
        parameters = json.load(file)
    return parameters

def calculate_hours_per_project(data):
    """Calculate the total hours per project for each user."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'project', 'timestamp'])
    
    hours = []
    for user, group in data.groupby('user'):
        for project, project_group in group.groupby('project'):
            start_times = project_group[project_group['event_type'] == 'start']['timestamp']
            stop_times = project_group[project_group['event_type'] == 'stop']['timestamp']
            total_hours = (stop_times.values - start_times.values).sum().astype('timedelta64[h]').astype(int)
            hours.append({'user': user, 'project': project, 'total_hours': total_hours})
    
    return pd.DataFrame(hours)

def plot_hours_per_project(hours):
    """Plot a pie chart of hours per project for each user."""
    figs = {}
    for user, group in hours.groupby('user'):
        fig = px.pie(group, names='project', values='total_hours', title=f'Hours per Project for {user}')
        figs[user] = fig
    return figs

def calculate_duration_per_period(data, period='W'):
    """Calculate the total duration per user and project for a given period (week, month, year)."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'project', 'timestamp'])
    data['period'] = data['timestamp'].dt.to_period(period)
    
    durations = []
    for (user, project, period), group in data.groupby(['user', 'project', 'period']):
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        total_duration = (stop_times.values - start_times.values).sum().astype('timedelta64[s]').astype(int)
        durations.append({'user': user, 'project': project, 'period': period, 'total_duration': total_duration})
    
    return pd.DataFrame(durations)

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

def logistic_regression_user_to_project(data):
    """Perform logistic regression to predict project based on user."""
    le_user = LabelEncoder()
    le_project = LabelEncoder()
    
    data['user_encoded'] = le_user.fit_transform(data['user'])
    data['project_encoded'] = le_project.fit_transform(data['project'])
    
    X = data[['user_encoded']]
    y = data['project_encoded']
    
    model = LogisticRegression()
    model.fit(X, y)
    
    return model, le_user, le_project

def logistic_regression_project_to_user(data):
    """Perform logistic regression to predict user based on project."""
    le_user = LabelEncoder()
    le_project = LabelEncoder()
    
    data['user_encoded'] = le_user.fit_transform(data['user'])
    data['project_encoded'] = le_project.fit_transform(data['project'])
    
    X = data[['project_encoded']]
    y = data['user_encoded']
    
    model = LogisticRegression()
    model.fit(X, y)
    
    return model, le_user, le_project

def linear_regression_duration_to_user(data):
    """Perform linear regression to predict duration based on user."""
    le_user = LabelEncoder()
    
    data['user_encoded'] = le_user.fit_transform(data['user'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'project', 'timestamp'])
    
    durations = []
    for user, group in data.groupby('user'):
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        total_duration = (stop_times.values - start_times.values).sum().astype('timedelta64[s]').astype(int)
        durations.append({'user': user, 'total_duration': total_duration})
    
    durations_df = pd.DataFrame(durations)
    durations_df['user_encoded'] = le_user.transform(durations_df['user'])
    
    X = durations_df[['user_encoded']]
    y = durations_df['total_duration']
    
    model = LinearRegression()
    model.fit(X, y)
    
    return model, le_user

def linear_regression_duration_to_project(data):
    """Perform linear regression to predict duration based on project."""
    le_project = LabelEncoder()
    
    data['project_encoded'] = le_project.fit_transform(data['project'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'project', 'timestamp'])
    
    durations = []
    for project, group in data.groupby('project'):
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        total_duration = (stop_times.values - start_times.values).sum().astype('timedelta64[s]').astype(int)
        durations.append({'project': project, 'total_duration': total_duration})
    
    durations_df = pd.DataFrame(durations)
    durations_df['project_encoded'] = le_project.transform(durations_df['project'])
    
    X = durations_df[['project_encoded']]
    y = durations_df['total_duration']
    
    model = LinearRegression()
    model.fit(X, y)
    
    return model, le_project

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

def plot_logistic_regression_user_to_project(data, model, le_user, le_project):
    """Plot the results of logistic regression to predict project based on user."""
    predictions = model.predict(data[['user_encoded']])
    data['predicted_project'] = le_project.inverse_transform(predictions)
    
    fig = px.scatter(data, x='user', y='predicted_project', color='project', title='Logistic Regression: User to Project')
    return fig

def plot_logistic_regression_project_to_user(data, model, le_user, le_project):
    """Plot the results of logistic regression to predict user based on project."""
    predictions = model.predict(data[['project_encoded']])
    data['predicted_user'] = le_user.inverse_transform(predictions)
    
    fig = px.scatter(data, x='project', y='predicted_user', color='user', title='Logistic Regression: Project to User')
    return fig

def plot_linear_regression_duration_to_user(data, model, le_user):
    """Plot the results of linear regression to predict duration based on user."""
    durations = []
    for user, group in data.groupby('user'):
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        total_duration = (stop_times.values - start_times.values).sum().astype('timedelta64[s]').astype(int)
        durations.append({'user': user, 'total_duration': total_duration})
    
    durations_df = pd.DataFrame(durations)
    durations_df['user_encoded'] = le_user.transform(durations_df['user'])
    
    X = durations_df[['user_encoded']]
    predictions = model.predict(X)
    durations_df['predicted_duration'] = predictions
    
    fig = px.scatter(durations_df, x='user', y='predicted_duration', color='user', title='Linear Regression: Duration to User')
    return fig

def plot_linear_regression_duration_to_project(data, model, le_project):
    """Plot the results of linear regression to predict duration based on project."""
    durations = []
    for project, group in data.groupby('project'):
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        total_duration = (stop_times.values - start_times.values).sum().astype('timedelta64[s]').astype(int)
        durations.append({'project': project, 'total_duration': total_duration})
    
    durations_df = pd.DataFrame(durations)
    durations_df['project_encoded'] = le_project.transform(durations_df['project'])
    
    X = durations_df[['project_encoded']]
    predictions = model.predict(X)
    durations_df['predicted_duration'] = predictions
    
    fig = px.scatter(durations_df, x='project', y='predicted_duration', color='project', title='Linear Regression: Duration to Project')
    return fig

# Dash App
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Work Time Tracker Statistics"),
    dcc.Graph(id='total-duration-graph'),
    dcc.Graph(id='duration-over-time-graph'),
    dcc.Graph(id='logistic-regression-user-to-project-graph'),
    dcc.Graph(id='logistic-regression-project-to-user-graph'),
    dcc.Graph(id='linear-regression-duration-to-user-graph'),
    dcc.Graph(id='linear-regression-duration-to-project-graph'),
    html.Div(id='pie-charts')
])

@app.callback(
    [Output('total-duration-graph', 'figure'),
     Output('duration-over-time-graph', 'figure'),
     Output('logistic-regression-user-to-project-graph', 'figure'),
     Output('logistic-regression-project-to-user-graph', 'figure'),
     Output('linear-regression-duration-to-user-graph', 'figure'),
     Output('linear-regression-duration-to-project-graph', 'figure'),
     Output('pie-charts', 'children')],
    [Input('total-duration-graph', 'id')]
)
def update_graphs(_):
    path_to_db = PATH_TO_DATA + "/20250214-010326/generate_database.db"
    data = read_database(path_to_db)
    
    durations = calculate_total_duration(data)
    total_duration_fig = plot_total_duration(durations)
    duration_over_time_fig = plot_duration_over_time(data)
    
    model_user_to_project, le_user, le_project = logistic_regression_user_to_project(data)
    logistic_regression_user_to_project_fig = plot_logistic_regression_user_to_project(data, model_user_to_project, le_user, le_project)
    
    model_project_to_user, le_user, le_project = logistic_regression_project_to_user(data)
    logistic_regression_project_to_user_fig = plot_logistic_regression_project_to_user(data, model_project_to_user, le_user, le_project)
    
    model_duration_to_user, le_user = linear_regression_duration_to_user(data)
    linear_regression_duration_to_user_fig = plot_linear_regression_duration_to_user(data, model_duration_to_user, le_user)
    
    model_duration_to_project, le_project = linear_regression_duration_to_project(data)
    linear_regression_duration_to_project_fig = plot_linear_regression_duration_to_project(data, model_duration_to_project, le_project)
    
    hours = calculate_hours_per_project(data)
    pie_charts = plot_hours_per_project(hours)
    pie_chart_divs = [dcc.Graph(figure=fig) for fig in pie_charts.values()]
    
    return (total_duration_fig, duration_over_time_fig, logistic_regression_user_to_project_fig,
            logistic_regression_project_to_user_fig, linear_regression_duration_to_user_fig,
            linear_regression_duration_to_project_fig, pie_chart_divs)

if __name__ == '__main__':
    app.run_server(debug=True)
