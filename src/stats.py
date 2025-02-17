import sqlite3
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
from config import PATH_TO_DATA
import json

# DATABASE_PATH = "wotiti/" + PATH_TO_DATA + "/20250214-010326/generate_database.db"
DATABASE_PATH = "wotiti/" + PATH_TO_DATA + "/20250217-114917/generate_database.db"
PARAMETERS_PATH = "wotiti/" + PATH_TO_DATA + "/20250217-114917/parameter_run_20250217-114917.json"


# Define Synthwave neon colors
SYNTHWAVE_COLORS = {
    'background': '#ffffff', # White
    'text': '#000000', # Black
    'blue': '#00d4ff', # Blue
    'pink': '#ff00ff', # Pink
    'yellow': '#ffff00' # Yellow
}

def read_database(db_path=DATABASE_PATH):
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

def read_parameters(file_path=PARAMETERS_PATH):
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
    fig = px.pie(user_data, names='project', values='total_hours', title=f'Hours per Project for {user}', 
                 color_discrete_sequence=[SYNTHWAVE_COLORS['blue'], SYNTHWAVE_COLORS['pink'], SYNTHWAVE_COLORS['yellow']])
    fig.update_layout(
        title_font=dict(size=18, color=SYNTHWAVE_COLORS['text'], family='Arial, sans-serif')
    )
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
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        time_difference = (stop_times.values - start_times.values)
        total_hours_user = time_difference.sum().astype('timedelta64[h]').astype(int)
        total_hours.append({'user': user, 'total_hours': total_hours_user})

    return pd.DataFrame(total_hours), date_range


def plot_total_hours_per_user(total_hours, date_range):
    """Plot a bar chart of total hours per user."""

    fig = px.bar(total_hours, x='user', y='total_hours',
                 title=f'Total Hours per User ({date_range})',
                 labels={'user': 'User', 'total_hours': 'Total Hours'},
                 color_discrete_sequence=[SYNTHWAVE_COLORS['blue']])
    fig.update_layout(
        title_font={"size": 18, "color": SYNTHWAVE_COLORS['text'],
                    "family": 'Arial, sans-serif'}
    )
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
    fig = px.bar(average_hours, x='user', y='average_hours', title='Average Hours per User', 
                 labels={'user': 'User', 'average_hours': 'Average Hours'}, 
                 color_discrete_sequence=[SYNTHWAVE_COLORS['pink']])
    fig.update_layout(
        title_font=dict(size=18, color=SYNTHWAVE_COLORS['text'], family='Arial, sans-serif')
    )
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
    """Plot a bar chart of average hours per user for a given period in days.
    
    This function generates a bar chart that visualizes the average working hours for each user
    over a specified period.
    """
    fig = px.bar(average_hours, x='user', y='average_hours', 
                 title=f'Average Hours per User (Calculated over {period_days} day periods)', 
                 labels={'user': 'User', 'average_hours': 'Average Hours'},
                 color_discrete_sequence=[SYNTHWAVE_COLORS['blue'], SYNTHWAVE_COLORS['pink'], SYNTHWAVE_COLORS['yellow']])
    fig.update_layout(
        title_font=dict(size=18, color=SYNTHWAVE_COLORS['text'], family='Arial, sans-serif')
    )
    return fig

# Dash App
app = Dash(__name__)

app.layout = html.Div([
    html.H1("WoTITI Stats", style={'color': SYNTHWAVE_COLORS['text'], 'text-align': 'pretty'}),
    html.Div(id='parameters-table'),
    html.H2("Hours per Project", style={'color': SYNTHWAVE_COLORS['text'], 'text-align': 'pretty'}),
    html.Div([
        html.Div([
            dcc.Dropdown(id='left-user-dropdown', placeholder="Select a user", style={'background-color': SYNTHWAVE_COLORS['background'], 'color': SYNTHWAVE_COLORS['text']}),
            dcc.Graph(id='left-pie-chart')
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),
        html.Div([
            dcc.Dropdown(id='right-user-dropdown', placeholder="Select a user", style={'background-color': SYNTHWAVE_COLORS['background'], 'color': SYNTHWAVE_COLORS['text']}),
            dcc.Graph(id='right-pie-chart')
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'})
    ], style={'display': 'flex', 'flex-wrap': 'wrap', 'justify-content': 'space-between'}),
    html.H2("Total Hours per User", style={'color': SYNTHWAVE_COLORS['text'], 'text-align': 'pretty'}),
    dcc.Graph(id='total-hours-chart'),
    html.H2("Average Hours per User pre Day", style={'color': SYNTHWAVE_COLORS['text'], 'text-align': 'pretty'}),
    dcc.Graph(id='average-hours-per-user-chart'),
    html.H2("Average Hours per Custom Period", style={'color': SYNTHWAVE_COLORS['text'], 'text-align': 'pretty'}),
    html.Div(
        children=[
            html.Label("Enter period in days:", style={'color': SYNTHWAVE_COLORS['text']}),
            dcc.Input(id='period-days-input', type='number', placeholder='Enter period in days', value=7, style={'margin-right': '10px'}),
            html.Button('Update Chart', id='update-period-button', n_clicks=0)
        ],
        style={'display': 'flex', 'alignItems': 'left', 'justifyContent': 'pretty'}
    ),
    dcc.Graph(id='average-hours-per-period-chart')
], style={'background-color': SYNTHWAVE_COLORS['background'], 'font-family': 'Arial, sans-serif'})

# @app.callback(
#     Output('parameters-table', 'children'),
#     [Input('parameters-table', 'id')]
# )
# def update_parameters_table(_):
#     """Update the parameters table."""
#     parameters = read_parameters()
#     if parameters:
#         table_header = [html.Tr([
#             html.Th(
#                 key,
#                 style={
#                     'border': '1px solid black',
#                     'padding': '4px',
#                     'background-color': '#f2f2f2'
#                 }
#             ) for key in parameters.keys()
#         ])]
#         table_body = [html.Tr([
#             html.Td(
#                 value,
#                 style={'border': '1px solid black', 'padding': '4px'}
#             ) for value in parameters.values()
#         ])]
#         table = html.Table(
#             table_header + table_body,
#             style={
#                 'width': '100%',
#                 'border': '1px solid black',
#                 'border-collapse': 'collapse',
#                 'margin-bottom': '10px'
#             }
#         )
#         return table
#     return "No parameters found."


@app.callback(
    [
        Output('left-user-dropdown', 'options'),
        Output('left-user-dropdown', 'value'),
        Output('right-user-dropdown', 'options'),
        Output('right-user-dropdown', 'value')
    ],
    [Input('left-user-dropdown', 'id')]
)
def update_dropdowns(_):
    """Update the dropdown options with user data."""
    data = read_database()
    users = data['user'].unique()
    options = [{'label': user, 'value': user} for user in users]
    default_value = users[0] if len(users) > 0 else None
    return options, default_value, options, default_value


@app.callback(
    Output('left-pie-chart', 'figure'),
    [Input('left-user-dropdown', 'value')]
)
def update_left_pie_chart(selected_user):
    """Update the left pie chart based on the selected user."""
    data = read_database()
    hours = calculate_hours_per_project(data)
    left_pie_chart = plot_hours_per_project(hours, selected_user)
    return left_pie_chart


@app.callback(
    Output('right-pie-chart', 'figure'),
    [Input('right-user-dropdown', 'value')]
)
def update_right_pie_chart(selected_user):
    """Update the right pie chart based on the selected user."""
    data = read_database()
    hours = calculate_hours_per_project(data)
    right_pie_chart = plot_hours_per_project(hours, selected_user)
    return right_pie_chart


@app.callback(
    Output('total-hours-chart', 'figure'),
    [Input('total-hours-chart', 'id')]
)
def update_total_hours_chart(_):
    """Update the total hours chart."""
    data = read_database()
    total_hours, date_range = calculate_total_hours_per_user(data)
    total_hours_chart = plot_total_hours_per_user(total_hours, date_range)
    return total_hours_chart


@app.callback(
    Output('average-hours-per-user-chart', 'figure'),
    [Input('average-hours-per-user-chart', 'id')]
)
def update_average_hours_per_user_chart(_):
    """Update the average hours per user chart."""
    data = read_database()
    average_hours = calculate_average_hours_per_user(data)
    average_hours_per_user_chart = plot_average_hours_per_user(average_hours)
    return average_hours_per_user_chart

@app.callback(
    Output('average-hours-per-period-chart', 'figure'),
    [Input('update-period-button', 'n_clicks')],
    [State('period-days-input', 'value')]
)
def update_average_hours_per_period_chart(n_clicks, period_days):
    """
    Callback to update the average hours per period chart based on the input period in days.
    
    This callback is triggered when the update button is clicked.
    It calculates the average hours per user for the specified period and updates the
    'average-hours-per-period-chart' component with the new chart.
    """
    data = read_database()
    average_hours = calculate_average_hours_per_period(data, int(period_days))
    average_hours_per_period_chart = plot_average_hours_per_period(average_hours, int(period_days))
    return average_hours_per_period_chart

if __name__ == '__main__':
    app.run_server(debug=True)
