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

# Modern color scheme
MODERN_COLORS = {
    'background': '#282a36',  # Dark background
    'text': '#f8f8f2',       # Light text
    'primary': '#6272a4',    # Muted blue
    'secondary': '#44475a',  # Darker gray
    'accent': '#8be9fd'      # Cyan accent
}

# Synthwave neon colors
SYNTHWAVE_COLORS = {
    'background': '#1f1f1f',
    'text': '#e0e0e0',
    'blue': '#00d4ff',
    'pink': '#ff00ff',
    'yellow': '#ffff00'
}

def read_database(db_path):
    """Read the SQLite database and return the data as a pandas DataFrame."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all user tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        
        data = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            table_data = pd.DataFrame(rows, columns=columns)
            table_data['user'] = table_name.replace('_events', '')
            data.append(table_data)
        
        conn.close()
        return pd.concat(data, ignore_index=True)
    except sqlite3.Error as e:
        print(f"Error reading database: {e}")
        return pd.DataFrame()

def read_parameters(file_path):
    """Read parameters from a JSON file."""
    try:
        with open(file_path, 'r') as file:
            parameters = json.load(file)
        return parameters
    except Exception as e:
        print(f"Error reading parameters: {e}")
        return {}

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

def plot_hours_per_project(hours, user):
    """Plot a pie chart of hours per project for a specific user."""
    user_data = hours[hours['user'] == user]
    fig = go.Figure(data=[go.Pie(labels=user_data['project'], values=user_data['total_hours'], marker_colors=[SYNTHWAVE_COLORS['blue'], SYNTHWAVE_COLORS['pink'], SYNTHWAVE_COLORS['yellow']])],
                    layout=go.Layout(title=f'Hours per Project for {user}',
                                     title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'],
                                     paper_bgcolor=MODERN_COLORS['background'],
                                     font_color=MODERN_COLORS['text']))
    return fig

def calculate_total_hours_per_user(data):
    """Calculate the total hours per user."""
    data['timestamp'] = pd.to_datetime(
        data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'timestamp'])

    # Get the start and end date of the data.
    start_date = data['timestamp'].min().strftime("%d-%m-%Y %H:%M:%S")
    end_date = data['timestamp'].max().strftime("%d-%m-%Y %H:%M:%S")
    date_range = f"{start_date} - {end_date}"
    
    total_hours = []
    for user, group in data.groupby('user'):
        if user == 'users':
            continue
        start_times = group[group['event_type'] == 'start']['timestamp'].reset_index(drop=True)
        stop_times = group[group['event_type'] == 'stop']['timestamp'].reset_index(drop=True)
        
         # Ensure that start_times and stop_times have the same length
        min_length = min(len(start_times), len(stop_times))
        start_times = start_times[:min_length]
        stop_times = stop_times[:min_length]

        # Calculate total hours by pairing start and stop times
        total_hours_user = 0
        for i in range(min(len(start_times), len(stop_times))):
            time_diff = stop_times[i] - start_times[i]
            total_hours_user += time_diff.total_seconds() / 3600

        total_hours.append({'user': user, 'total_hours': total_hours_user})
    
    return pd.DataFrame(total_hours), date_range

def plot_total_hours_per_user(total_hours, date_range):
    """Plot a bar chart of total hours per user."""
    
    if total_hours is None or total_hours.empty:
        return go.Figure(layout=go.Layout(title=f'No data available for Total Hours per User ({date_range})',
                      xaxis_title='User',
                      yaxis_title='Total Hours',
                      plot_bgcolor=MODERN_COLORS['background'],
                      paper_bgcolor=MODERN_COLORS['background'],
                      font_color=MODERN_COLORS['text']))

    # Convert 'total_hours' column to numeric, handling potential errors
    total_hours.loc[:, 'total_hours'] = pd.to_numeric(total_hours['total_hours'], errors='coerce')

    # Remove rows with NaN values in 'total_hours'
    total_hours = total_hours.dropna(subset=['total_hours'])

    fig = go.Figure(data=[go.Bar(x=total_hours['user'], y=total_hours['total_hours'], marker_color=MODERN_COLORS['accent'])],
                    layout=go.Layout(title=f'Total Hours per User ({date_range})',
                                     xaxis_title='User',
                                     yaxis_title='Total Hours',
                                     title_font={"size": 18, "color": MODERN_COLORS['text'], "family": 'Arial, sans-serif'},
                                     plot_bgcolor=MODERN_COLORS['background'],
                                     paper_bgcolor=MODERN_COLORS['background'],
                                     font_color=MODERN_COLORS['text']))
    return fig

def calculate_average_hours_per_user(data):
    """Calculate the average hours per user."""
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
    """Plot a bar chart of average hours per user."""
    
    if average_hours is None or average_hours.empty:
        return go.Figure(layout=go.Layout(title=f'No data available for Average Hours per User',
                          xaxis_title='User',
                          yaxis_title='Average Hours',
                          plot_bgcolor=MODERN_COLORS['background'],
                          paper_bgcolor=MODERN_COLORS['background'],
                          font_color=MODERN_COLORS['text']))
    
    # Convert 'average_hours' column to numeric, handling potential errors
    average_hours.loc[:, 'average_hours'] = pd.to_numeric(average_hours['average_hours'], errors='coerce')

    # Remove rows with NaN values in 'average_hours'
    average_hours = average_hours.dropna(subset=['average_hours'])
    
    fig =  go.Figure(data=[go.Bar(x=average_hours['user'], y=average_hours['average_hours'], marker_color=SYNTHWAVE_COLORS['pink'])],
                layout=go.Layout(title=f'Average Hours per User',
                                 xaxis_title='User',
                                 yaxis_title='Average Hours',
                                 title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                 plot_bgcolor=MODERN_COLORS['background'],
                                 paper_bgcolor=MODERN_COLORS['background'],
                                 font_color=MODERN_COLORS['text']))
    return fig

# TODO Hier nochmal prüfen, was genau berechnet werden soll
def calculate_average_hours_per_period(data, period_days):
    """Calculate the average hours per user for a given period in days.
    
    This function calculates the average working hours for each user over a specified period.
    """
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'timestamp'])
    
    average_hours = []
    
    # Calculate the number of periods based on the entire dataset
    total_days = (data['timestamp'].max() - data['timestamp'].min()).days
    num_periods = max(1, total_days // period_days)  # Ensure at least one period

    for user, group in data.groupby('user'):
        if user == 'users':
            continue
        
        # Get start and stop times
        start_times = group[group['event_type'] == 'start']['timestamp'].reset_index(drop=True)
        stop_times = group[group['event_type'] == 'stop']['timestamp'].reset_index(drop=True)
        
        # Calculate total hours
        total_hours = 0
        for start_time, stop_time in zip(start_times, stop_times):
            total_hours += (stop_time - start_time).total_seconds() / 3600
        
        # Calculate average hours per period
        average_hours_user = total_hours / num_periods
        average_hours.append({
            'user': user,
            'average_hours': average_hours_user,
            'period_days': period_days
        })
    
    return pd.DataFrame(average_hours)

def plot_average_hours_per_period(average_hours, period_days):
    """Plot a bar chart of average hours per user for a given period in days."""
    fig = go.Figure(data=[go.Bar(x=average_hours['user'], y=average_hours['average_hours'], marker_color=SYNTHWAVE_COLORS['blue'])],
                    layout=go.Layout(title=f'Average Hours per User (Calculated over {period_days} day periods)',
                                     xaxis_title='User',
                                     yaxis_title='Average Hours',
                                     title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'],
                                     paper_bgcolor=MODERN_COLORS['background'],
                                     font_color=MODERN_COLORS['text']))
    return fig

def browse_directory():
    """Browse for a directory using a Tkinter dialog."""
    root = Tk()
    root.withdraw()  # Hide the root window
    directory = filedialog.askdirectory()
    root.destroy()  # Destroy the root window after use
    return directory

def find_database_and_parameters(directory=PATH_TO_DATA):
    """Find the database and parameters files in the given directory."""
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
            dbc.Button('Select Directory', id='browse-button', n_clicks=0, color="primary", className="mb-3"),
            dcc.Store(id='db-path', data=None),
            dcc.Store(id='param-path', data=None),
            dbc.Progress(id="progress", value=0, animated=False, striped=False, color="success", className="mb-3", label=""),
            html.Div(id='parameters-table')
        ], md=12),
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Hours per Project (Left)", style={'color': MODERN_COLORS['text']}),
                dbc.CardBody([
                    dcc.Dropdown(
                        id='left-user-dropdown',
                        placeholder="Select a user",
                        style={'color': MODERN_COLORS['text'], 'backgroundColor': MODERN_COLORS['secondary']},
                        className='dropdown-custom'  # Add custom class
                    ),
                    dcc.Graph(id='left-pie-chart', style={'backgroundColor': MODERN_COLORS['background']})
                ])
            ], className="mb-3", style={'backgroundColor': MODERN_COLORS['secondary'], 'color': MODERN_COLORS['text']})
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Hours per Project (Right)", style={'color': MODERN_COLORS['text']}),
                dbc.CardBody([
                    dcc.Dropdown(
                        id='right-user-dropdown',
                        placeholder="Select a user",
                        style={'color': MODERN_COLORS['text'], 'backgroundColor': MODERN_COLORS['secondary']},
                        className='dropdown-custom'  # Add custom class
                    ),
                    dcc.Graph(id='right-pie-chart',  style={'backgroundColor': MODERN_COLORS['background']})
                ])
            ], className="mb-3", style={'backgroundColor': MODERN_COLORS['secondary'], 'color': MODERN_COLORS['text']})
        ], md=6),
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Total Hours per User", style={'color': MODERN_COLORS['text']}),
                dbc.CardBody(dcc.Graph(id='total-hours-chart',  style={'backgroundColor': MODERN_COLORS['background']}))
            ], className="mb-3", style={'backgroundColor': MODERN_COLORS['secondary'], 'color': MODERN_COLORS['text']})
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Average Hours per User", style={'color': MODERN_COLORS['text']}),
                dbc.CardBody(dcc.Graph(id='average-hours-per-user-chart',  style={'backgroundColor': MODERN_COLORS['background']}))
            ], className="mb-3", style={'backgroundColor': MODERN_COLORS['secondary'], 'color': MODERN_COLORS['text']})
        ], md=6),
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Average Hours per Custom Period", style={'color': MODERN_COLORS['text']}),
                dbc.CardBody([
                    dbc.Label("Enter period in days:", html_for="period-days-input",  style={'color': MODERN_COLORS['text']}),
                    dbc.InputGroup([
                        dbc.Input(id='period-days-input', type='number', placeholder='Enter period in days', value=7, style={'width': 'auto', 'maxWidth': '80px'}),
                        dbc.Button('Update Chart', id='update-period-button', n_clicks=0, color="secondary", style={'margin-left': '5px'}),
                    ], style={'margin': '15px'}, className='input-group-custom'),
                    #]),
                    dcc.Graph(id='average-hours-per-period-chart',  style={'backgroundColor': MODERN_COLORS['background']})
                ])
            ], className="mb-3", style={'backgroundColor': MODERN_COLORS['secondary'], 'color': MODERN_COLORS['text']})
        ], md=12)
    ])
], fluid=True, style={'backgroundColor': MODERN_COLORS['background'], 'color': MODERN_COLORS['text'], 'padding': '20px'})

@app.callback(
    [Output('db-path', 'data'),
     Output('param-path', 'data'),
     Output('progress', 'value'),
     Output('progress', 'animated'),
     Output('progress', 'striped'),
     Output('progress', 'label')],
    [Input('browse-button', 'n_clicks')]
)
def update_paths(n_clicks):
    """Update the database and parameter paths based on the selected directory."""
    if n_clicks > 0:
        directory = browse_directory()
        if directory:
            db_path, param_path = find_database_and_parameters(directory)
            if db_path and param_path:
                return db_path, param_path, 100, False, False, "100% - Data Loaded"  # Set progress to 100% and stop animation
            else:
                return None, None, 100, False, False, "Error: Database or Parameter file not found"
        else:
            return None, None, 0, False, False, "" # No directory selected
    return None, None, 0, False, False, "" # Initial state

@app.callback(
    Output('parameters-table', 'children'),
    [Input('param-path', 'data')]
)
def update_parameters_table(param_path):
    """Update the parameters table based on the selected parameter file."""
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
    [Output('left-user-dropdown', 'options'),
     Output('left-user-dropdown', 'value'),
     Output('right-user-dropdown', 'options'),
     Output('right-user-dropdown', 'value')],
    [Input('db-path', 'data'),
     Input('browse-button', 'n_clicks')]  # Add browse-button to trigger on new data
)
def update_dropdowns(db_path, n_clicks):
    """Update the dropdown options with user data."""
    if db_path:
        data = read_database(db_path)
        users = data['user'].unique()
        options = [{'label': user, 'value': user} for user in users]
        default_value = users[0] if len(users) > 0 else None
        return options, default_value, options, default_value
    else:
        return [], None, [], None

@app.callback(
    Output('left-pie-chart', 'figure'),
    [Input('left-user-dropdown', 'value'),
     Input('db-path', 'data')]
)
def update_left_pie_chart(selected_user, db_path):
    """Update the left pie chart based on the selected user."""
    if db_path and selected_user:
        data = read_database(db_path)
        hours = calculate_hours_per_project(data)
        left_pie_chart = plot_hours_per_project(hours, selected_user)
        return left_pie_chart
    else:
        return {}

@app.callback(
    Output('right-pie-chart', 'figure'),
    [Input('right-user-dropdown', 'value'),
     Input('db-path', 'data')]
)
def update_right_pie_chart(selected_user, db_path):
    """Update the right pie chart based on the selected user."""
    if db_path and selected_user:
        data = read_database(db_path)
        hours = calculate_hours_per_project(data)
        right_pie_chart = plot_hours_per_project(hours, selected_user)
        return right_pie_chart
    else:
        return {}

@app.callback(
    Output('total-hours-chart', 'figure'),
    [Input('total-hours-chart', 'id'),
     Input('db-path', 'data')]
)
def update_total_hours_chart(_, db_path):
    """Update the total hours chart."""
    if db_path:
        data = read_database(db_path)
        total_hours, date_range = calculate_total_hours_per_user(data)
        total_hours_chart = plot_total_hours_per_user(total_hours, date_range)
        return total_hours_chart
    else:
        return {}

@app.callback(
    Output('average-hours-per-user-chart', 'figure'),
    [Input('average-hours-per-user-chart', 'id'),
     Input('db-path', 'data')]
)
def update_average_hours_per_user_chart(_, db_path):
    """Update the average hours per user chart."""
    if db_path:
        data = read_database(db_path)
        average_hours = calculate_average_hours_per_user(data)
        if average_hours is None or average_hours.empty:
            return go.Figure(layout=go.Layout(title=f'No data available for Average Hours per User',
                          xaxis_title='User',
                          yaxis_title='Average Hours',
                          plot_bgcolor=MODERN_COLORS['background'],
                          paper_bgcolor=MODERN_COLORS['background'],
                          font_color=MODERN_COLORS['text']))
        
        # Convert 'average_hours' column to numeric, handling potential errors
        average_hours.loc[:, 'average_hours'] = pd.to_numeric(average_hours['average_hours'], errors='coerce')

        # Remove rows with NaN values in 'average_hours'
        average_hours = average_hours.dropna(subset=['average_hours'])
        
        fig =  go.Figure(data=[go.Bar(x=average_hours['user'], y=average_hours['average_hours'], marker_color=SYNTHWAVE_COLORS['pink'])],
                    layout=go.Layout(title=f'Average Hours per User',
                                     xaxis_title='User',
                                     yaxis_title='Average Hours',
                                     title_font=dict(size=18, color=MODERN_COLORS['text'], family='Arial, sans-serif'),
                                     plot_bgcolor=MODERN_COLORS['background'],
                                     paper_bgcolor=MODERN_COLORS['background'],
                                     font_color=MODERN_COLORS['text']))
        return fig
    else:
        return {}

@app.callback(
    Output('average-hours-per-period-chart', 'figure'),
    [Input('update-period-button', 'n_clicks')],
    [State('period-days-input', 'value'),
     State('db-path', 'data')]
)
def update_average_hours_per_period_chart(n_clicks, period_days, db_path):
    """
    Callback to update the average hours per period chart based on the input period in days.
    """
    if db_path:
        data = read_database(db_path)
        average_hours = calculate_average_hours_per_period(data, int(period_days))
        average_hours_per_period_chart = plot_average_hours_per_period(average_hours, int(period_days))
        return average_hours_per_period_chart
    else:
        return {}

if __name__ == '__main__':
    app.run_server(debug=True)
