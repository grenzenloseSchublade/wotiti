import sqlite3
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from config import PATH_TO_DATA
import json
import os
import glob
from datetime import datetime
from tkinter import Tk, filedialog

# Color schemes
MODERN_COLORS = {
    'background': '#282a36', 'text': '#f8f8f2', 'primary': '#6272a4',
    'secondary': '#44475a', 'accent': '#8be9fd'
}
SYNTHWAVE_COLORS = {
    'background': '#1f1f1f', 'text': '#e0e0e0', 'blue': '#00d4ff',
    'pink': '#ff00ff', 'yellow': '#ffff00'
}

def read_database(db_path):
    """Reads SQLite database, returns data as pandas DataFrame."""
    try:
        with sqlite3.connect(db_path) as conn:
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            tables = [table[0] for table in conn.execute(query).fetchall()]
            data = []
            for table_name in tables:
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                df['user'] = table_name.replace('_events', '')
                data.append(df)
            return pd.concat(data, ignore_index=True)
    except sqlite3.Error as e:
        print(f"Error reading database: {e}")
        return pd.DataFrame()

def read_parameters(file_path):
    """Reads parameters from a JSON file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error reading parameters: {e}")
        return {}

def calculate_hours_per_project(data):
    """Calculates total hours per project for each user."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'project', 'timestamp'])
    hours = []
    for (user, project), group in data.groupby(['user', 'project']):
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        # Ensure start_times and stop_times have the same length
        min_length = min(len(start_times), len(stop_times))
        total_hours = (stop_times.iloc[:min_length].values - start_times.iloc[:min_length].values).sum().astype('timedelta64[h]').astype(int)
        hours.append({'user': user, 'project': project, 'total_hours': total_hours})
    return pd.DataFrame(hours)

def plot_hours_per_project(hours, user):
    """Plots a pie chart of hours per project for a specific user."""
    user_data = hours[hours['user'] == user]
    fig = go.Figure(data=[go.Pie(labels=user_data['project'], values=user_data['total_hours'],
                                 marker_colors=[SYNTHWAVE_COLORS['blue'], SYNTHWAVE_COLORS['pink'], SYNTHWAVE_COLORS['yellow']])],
                    layout=go.Layout(title=f'Hours per Project for {user}', title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def calculate_total_hours_per_user(data):
    """Calculates total hours per user."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'timestamp'])
    start_date = data['timestamp'].min().strftime("%d-%m-%Y %H:%M:%S")
    end_date = data['timestamp'].max().strftime("%d-%m-%Y %H:%M:%S")
    date_range = f"{start_date} - {end_date}"
    total_hours = []
    for user, group in data.groupby('user'):
        if user == 'users':
            continue
        start_times = group[group['event_type'] == 'start']['timestamp'].reset_index(drop=True)
        stop_times = group[group['event_type'] == 'stop']['timestamp'].reset_index(drop=True)
        # Ensure start_times and stop_times have the same length
        min_length = min(len(start_times), len(stop_times))
        total_hours_user = sum((stop_times.iloc[i] - start_times.iloc[i]).total_seconds() / 3600 for i in range(min_length))
        total_hours.append({'user': user, 'total_hours': total_hours_user})
    return pd.DataFrame(total_hours), date_range

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

def calculate_average_hours_per_user(data):
    """Calculates average hours per user."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'timestamp'])
    average_hours = []
    for user, group in data.groupby('user'):
        if user == 'users':
            continue
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        total_hours_user = (stop_times.values - start_times.values).sum().astype('timedelta64[h]').astype(int)
        average_hours_user = total_hours_user / len(group['date'].unique())
        average_hours.append({'user': user, 'average_hours': average_hours_user})
    return pd.DataFrame(average_hours)

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

def calculate_average_hours_per_period(data, period_days):
    """Calculates average hours per user for a given period in days."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'timestamp'])
    average_hours = []
    for user, group in data.groupby('user'):
        if user == 'users':
            continue
        start_times = group[group['event_type'] == 'start']['timestamp'].reset_index(drop=True)
        stop_times = group[group['event_type'] == 'stop']['timestamp'].reset_index(drop=True)
        min_length = min(len(start_times), len(stop_times))
        total_hours = sum((stop_times.iloc[i] - start_times.iloc[i]).total_seconds() / 3600 for i in range(min_length))
        
        # Calculate the number of days the user has data for
        num_days = len(group['date'].unique())
        
        # Ensure that the number of periods is at least 1
        num_periods = max(1, num_days / period_days)
        
        average_hours_user = total_hours / num_periods
        average_hours.append({'user': user, 'average_hours': average_hours_user, 'period_days': period_days})
    return pd.DataFrame(average_hours)

def plot_average_hours_per_period(average_hours, period_days):
    """Plots a bar chart of average hours per user for a given period in days."""
    fig = go.Figure(data=[go.Bar(x=average_hours['user'], y=average_hours['average_hours'], marker_color=SYNTHWAVE_COLORS['blue'])],
                    layout=go.Layout(title=f'Average Hours per User (Calculated over {period_days} day periods)',
                                     xaxis_title='User', yaxis_title='Average Hours',
                                     title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
    return fig

def browse_directory():
    """Browses for a directory using a Tkinter dialog."""
    root = Tk()
    root.withdraw()
    directory = filedialog.askdirectory(initialdir=PATH_TO_DATA)
    root.destroy()
    return directory

def find_database_and_parameters(directory=PATH_TO_DATA, update_progress=None):
    """Finds the database and parameters files in the given directory."""
    if update_progress:
        update_progress(20, "Searching for database and parameter files...")
    db_path = glob.glob(os.path.join(directory, "generate_database.db"))
    param_path = glob.glob(os.path.join(directory, "parameter_run_*.json"))
    db_path = db_path[0] if db_path else None
    param_path = param_path[0] if param_path else None
    return db_path, param_path

# Dash App
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

app.layout = dbc.Container([
    html.H1("WoTITI Stats", style={'textAlign': 'center', 'color': MODERN_COLORS['text']}),
    dbc.Row([
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    dbc.Button('Select Directory', id='browse-button', n_clicks=0, color="primary", className="mb-3"),
                ], width="auto"),
                dbc.Col([
                    dbc.Progress(id="progress", value=0, animated=True, striped=False, color="success", className="mb-3", label="", style={'height': '30px'}),
                ], md=8),
            ], align="center"),
            dcc.Store(id='db-path', data=None),
            dcc.Store(id='param-path', data=None),
            html.Div(id='parameters-table')
        ], md=12),
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Hours per Project (Left)", style={'color': MODERN_COLORS['text']}),
                dbc.CardBody([
                    dcc.Dropdown(id='left-user-dropdown', placeholder="Select a user", style={'color': MODERN_COLORS['text'], 'backgroundColor': MODERN_COLORS['secondary']}, className='dropdown-custom'),
                    dcc.Graph(id='left-pie-chart', style={'backgroundColor': MODERN_COLORS['background']})
                ])
            ], className="mb-3", style={'backgroundColor': MODERN_COLORS['secondary'], 'color': MODERN_COLORS['text']})
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Hours per Project (Right)", style={'color': MODERN_COLORS['text']}),
                dbc.CardBody([
                    dcc.Dropdown(id='right-user-dropdown', placeholder="Select a user", style={'color': MODERN_COLORS['text'], 'backgroundColor': MODERN_COLORS['secondary']}, className='dropdown-custom'),
                    dcc.Graph(id='right-pie-chart',  style={'backgroundColor': MODERN_COLORS['background']}, figure=go.Figure(layout=go.Layout(plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'])))
                ])
            ], className="mb-3", style={'backgroundColor': MODERN_COLORS['secondary'], 'color': MODERN_COLORS['text']})
        ], md=6),
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Total Hours per User", style={'color': MODERN_COLORS['text']}),
                dbc.CardBody(dcc.Graph(id='total-hours-chart',  style={'backgroundColor': MODERN_COLORS['background']}, figure=go.Figure(layout=go.Layout(plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background']))))
            ], className="mb-3", style={'backgroundColor': MODERN_COLORS['secondary'], 'color': MODERN_COLORS['text']})
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Average Hours per User", style={'color': MODERN_COLORS['text']}),
                dbc.CardBody(dcc.Graph(id='average-hours-per-user-chart',  style={'backgroundColor': MODERN_COLORS['background']}, figure=go.Figure(layout=go.Layout(plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background']))))
            ], className="mb-3", style={'backgroundColor': MODERN_COLORS['secondary'], 'color': MODERN_COLORS['text']})
        ], md=6),
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Average Hours per Custom Period", style={'color': MODERN_COLORS['text']}),
                dbc.CardBody([
                    dbc.InputGroup([
                        dbc.Label("Period", html_for="period-days-input",  style={'color': MODERN_COLORS['text'], 'margin-right': '10px'}),
                        dbc.Input(id='period-days-input', type='number', placeholder='Enter period in days', value=7, style={'width': 'auto', 'maxWidth': '60px'}),
                        dbc.Label("[days]", html_for="period-days-input",  style={'color': MODERN_COLORS['text'], 'margin-left': '5px'}),
                        dbc.Button('Update Chart', id='update-period-button', n_clicks=0, color="secondary", style={'margin-left': '5px'}),
                    ], style={'margin': '15px'}, className='input-group-custom d-flex align-items-center'),
                    dcc.Graph(id='average-hours-per-period-chart',  style={'backgroundColor': MODERN_COLORS['background']}, figure=go.Figure(layout=go.Layout(plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'])))
                ])
            ], className="mb-3", style={'backgroundColor': MODERN_COLORS['secondary'], 'color': MODERN_COLORS['text']})
        ], md=12)
    ])
], fluid=True, style={'backgroundColor': MODERN_COLORS['background'], 'color': MODERN_COLORS['text'], 'padding': '20px'})

@app.callback(
    [Output('db-path', 'data'), Output('param-path', 'data'), Output('progress', 'value'),
     Output('progress', 'animated'), Output('progress', 'striped'), Output('progress', 'label'),
     Output('left-user-dropdown', 'options'), Output('left-user-dropdown', 'value'),
     Output('right-user-dropdown', 'options'), Output('right-user-dropdown', 'value')],
    [Input('browse-button', 'n_clicks')],
    [State('period-days-input', 'value')]
)
def update_paths(n_clicks, period_days):
    """Updates database and parameter paths based on selected directory."""
    if n_clicks > 0:
        directory = browse_directory()
        if directory:
            def update_progress(value, label, animated=True):
                """Helper function to update progress bar."""
                return [value, animated, False, label]  # Return values for the progress bar outputs

            # Initial progress update
            progress_values = update_progress(10, "Starting data loading...")
            
            db_path, param_path = find_database_and_parameters(directory, update_progress=update_progress)
            if db_path and param_path:
                progress_values = update_progress(40, "Database and parameter files found. Reading database...")
                data = read_database(db_path)
                progress_values = update_progress(70, "Database read successfully. Processing data...")
                users = [user for user in data['user'].unique() if user != 'users']
                left_user = 'user_1' if 'user_1' in users else users[0] if len(users) > 0 else None
                right_user = 'user_2' if 'user_2' in users else users[1] if len(users) > 1 else None
                options = [{'label': user, 'value': user} for user in users]
                progress_values = update_progress(100, "Data loaded and processed.", animated=False)
                return db_path, param_path, progress_values[0], progress_values[1], progress_values[2], progress_values[3], options, left_user, options, right_user
            else:
                progress_values = update_progress(100, "Error: Database or Parameter file not found", animated=False)
                return None, None, progress_values[0], progress_values[1], progress_values[2], progress_values[3], [], None, [], None
        else:
            return None, None, 0, False, False, "", [], None, [], None
    return None, None, 0, True, False, "", [], None, [], None

@app.callback(
    Output('parameters-table', 'children'),
    [Input('param-path', 'data')]
)
def update_parameters_table(param_path):
    """Updates parameters table based on selected parameter file."""
    if param_path:
        parameters = read_parameters(param_path)
        if parameters:
            table_header = [html.Tr([html.Th(key, style={'border': '1px solid black', 'padding': '4px', 'background-color': MODERN_COLORS['secondary']}) for key in parameters.keys()])]
            table_body = [html.Tr([html.Td(value, style={'border': '1px solid black', 'padding': '4px'}) for value in parameters.values()])]
            table = html.Table(table_header + table_body, style={'width': '100%', 'border': '1px solid black', 'border-collapse': 'collapse', 'margin-bottom': '10px', 'color': MODERN_COLORS['text']})
            return table
        return "No parameters found."
    return "Select a directory to load parameters."

@app.callback(
    Output('left-pie-chart', 'figure'),
    [Input('left-user-dropdown', 'value'),
     Input('db-path', 'data')]
)
def update_left_pie_chart(selected_user, db_path):
    """Updates the left pie chart based on the selected user."""
    if db_path and selected_user:
        data = read_database(db_path)
        hours = calculate_hours_per_project(data)
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
        data = read_database(db_path)
        hours = calculate_hours_per_project(data)
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
        data = read_database(db_path)
        total_hours, date_range = calculate_total_hours_per_user(data)
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
        data = read_database(db_path)
        average_hours = calculate_average_hours_per_user(data)
        if average_hours is None or average_hours.empty:
            return go.Figure(layout=go.Layout(title=f'No data available for Average Hours per User',
                          xaxis_title='User',
                          yaxis_title='Average Hours',
                          plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
        
        # Convert 'average_hours' column to numeric, handling potential errors
        average_hours.loc[:, 'average_hours'] = pd.to_numeric(average_hours['average_hours'], errors='coerce').dropna()

        fig =  go.Figure(data=[go.Bar(x=average_hours['user'], y=average_hours['average_hours'], marker_color=SYNTHWAVE_COLORS['pink'])],
                    layout=go.Layout(title=f'Average Hours per User per Day',
                                     xaxis_title='User', yaxis_title='Average Hours',
                                     title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
        return fig
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
            return go.Figure(layout=go.Layout(title=f'Invalid period: Please enter a value greater than 0',
                                  xaxis_title='User', yaxis_title='Average Hours',
                                  plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))
        if db_path:
            data = read_database(db_path)
            fig = plot_average_hours_per_period(calculate_average_hours_per_period(data, period_days), period_days)
            return fig
        else:
            return go.Figure(layout=go.Layout(plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background']))
    except ValueError:
        return go.Figure(layout=go.Layout(title=f'Invalid period: Please enter a valid number',
                              xaxis_title='User', yaxis_title='Average Hours',
                              plot_bgcolor=MODERN_COLORS['background'], paper_bgcolor=MODERN_COLORS['background'], font_color=MODERN_COLORS['text']))

if __name__ == '__main__':
    app.run_server(debug=True)
