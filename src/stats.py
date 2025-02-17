import sqlite3
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
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
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
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
        total_hours_user = (stop_times.values - start_times.values).sum().astype('timedelta64[h]').astype(int)
        total_hours.append({'user': user, 'total_hours': total_hours_user})
    
    return pd.DataFrame(total_hours), date_range

def plot_total_hours_per_user(total_hours, date_range):
    """Plot a bar chart of total hours per user."""
    
    fig = px.bar(total_hours, x='user', y='total_hours', title=f'Total Hours per User ({date_range})', 
                 labels={'user': 'User', 'total_hours': 'Total Hours'}, 
                 color_discrete_sequence=[SYNTHWAVE_COLORS['blue']])
    fig.update_layout(
        title_font=dict(size=18, color=SYNTHWAVE_COLORS['text'], family='Arial, sans-serif')
    )
    return fig

# TODO Berechnung hinzufügen von minimum und maximum Stunden pro Tag, Woche und Monat
# -> so darstellen, dass min, max und average auf einer Grafik dargestellt werden 
# TODO Berechnung hinzufügen von Anzahl der Tage, Wochen und Monate
# TODO Berechnung hinzufügen von Anzahl der Projekte pro Tag, Woche und Monat

# TODO das hier ist irgendwie alles falsch...
def calculate_average_hours(data, period='D'):
    """Calculate the average hours per user for a given period (day, week, month).
    Ensure that each day has the same number of start and stop events.
    If a start event begins on one day and the stop event goes into the next day,
    count it towards the initial day and do not integrate it into the following day.
    """
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'timestamp'])

    # Berechnung der Perioden basierend auf dem ersten Datum
    start_date = data['timestamp'].min()

    #period = 'M'

    if period == 'D':
        full_period_length = 1
        data['period'] = (data['timestamp'] - start_date).dt.days
    elif period == 'W':
        full_period_length = 7
        data['period'] = (data['timestamp'] - start_date).dt.days // 7
    elif period == 'M':
        full_period_length = 30
        data['period'] = (data['timestamp'] - start_date).dt.days // 30
    else:
        raise ValueError("Ungültiger Periodenwert. Bitte 'D', 'W' oder 'M' verwenden.")
    
    hours = []
    for (user, user_period), group in data.groupby(['user', 'period']):
        # Berechne die Länge der aktuellen Periode in Tagen pro User
        period_length = (group['timestamp'].max() - group['timestamp'].min()).days + 1
        
        # Wenn die Periode nicht vollständig ist, überspringe sie
        if period_length < full_period_length:
            continue
        
        start_times = group[group['event_type'] == 'start']['timestamp'].reset_index(drop=True)
        stop_times = group[group['event_type'] == 'stop']['timestamp'].reset_index(drop=True)

        # Ensure the same number of start and stop events per period
        min_length = min(len(start_times), len(stop_times))
        start_times = start_times[:min_length]
        stop_times = stop_times[:min_length]
        
        if user == "user_4":
            print("#####")
            print(start_times)
            print(stop_times)

        # Calculate total hours
        total_hours = (
            (stop_times.values - start_times.values)
            .sum()
            .astype('timedelta64[h]')
            .astype(int)
        )
        hours.append({'user': user, 'period': user_period, 'total_hours': total_hours})
    
    df = pd.DataFrame(hours)
    average_hours = df.groupby('user')['total_hours'].mean().reset_index()
    return average_hours

def plot_average_hours(data):
    """Plot a bar chart of average hours per day, week, and month for a user."""
    periods = ['D', 'W', 'M']
    average_hours = []
    
    for period in periods:
        avg_hours = calculate_average_hours(data, period)
        avg_hours['period'] = period
        average_hours.append(avg_hours)

    # Get the start and end date of the data.
    start_date = data['timestamp'].min().strftime("%d-%m-%Y %H:%M:%S")
    end_date = data['timestamp'].max().strftime("%d-%m-%Y %H:%M:%S")
    date_range = f"{start_date} - {end_date}" 
    
    average_hours_df = pd.concat(average_hours)
    fig = px.bar(average_hours_df, x='user', y='total_hours', color='period', barmode='group',
                 title=f'Average Hours from {date_range}', labels={'user': 'User', 'total_hours': 'Average Hours', 'period': 'Period'},
                 color_discrete_sequence=[SYNTHWAVE_COLORS['blue'], SYNTHWAVE_COLORS['pink'], SYNTHWAVE_COLORS['yellow']])
    
    fig.update_layout(
        title_font=dict(size=18, color=SYNTHWAVE_COLORS['text'], family='Arial, sans-serif'),
        margin=dict(t=30, b=30)  # Add top and bottom margin of 20px
    )
    
    # Add text labels on the bars
    fig.update_traces(texttemplate='%{y}', textposition='outside')
    
    return fig

# TODO hier ist das riesen problem, dass irgendwie die averaging funktion komplett verkackt wird...
# 
def calculate_average_hours_per_user(data):
    """Calculate the average hours per user."""
    data['timestamp'] = pd.to_datetime(data['timestamp'], format="%d-%m-%Y %H:%M:%S")
    data = data.sort_values(by=['user', 'timestamp'])
    
    average_hours = []
    for user, group in data.groupby('user'):
        if user == 'users':
            continue

        print(len(group['date'].unique()))
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
    html.H2("Average Hours per Period", style={'color': SYNTHWAVE_COLORS['text'], 'text-align': 'pretty'}),
    dcc.Graph(id='average-hours-chart')
], style={'background-color': SYNTHWAVE_COLORS['background'], 'font-family': 'Arial, sans-serif'})

@app.callback(
    Output('parameters-table', 'children'),
    [Input('parameters-table', 'id')]
)
def update_parameters_table(_):
    parameters = read_parameters()
    if parameters:
        table_header = [html.Tr([html.Th(key, style={'border': '1px solid black', 'padding': '4px', 'background-color': '#f2f2f2'}) for key in parameters.keys()])]
        table_body = [html.Tr([html.Td(value, style={'border': '1px solid black', 'padding': '4px'}) for value in parameters.values()])]
        table = html.Table(table_header + table_body, style={'width': '100%', 'border': '1px solid black', 'border-collapse': 'collapse', 'margin-bottom': '10px'})
        return table
    return "No parameters found."

@app.callback(
    [Output('left-user-dropdown', 'options'),
     Output('left-user-dropdown', 'value'),
     Output('right-user-dropdown', 'options'),
     Output('right-user-dropdown', 'value')],
    [Input('left-user-dropdown', 'id')]
)
def update_dropdowns(_):
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
    data = read_database()
    hours = calculate_hours_per_project(data)
    left_pie_chart = plot_hours_per_project(hours, selected_user)
    return left_pie_chart

@app.callback(
    Output('right-pie-chart', 'figure'),
    [Input('right-user-dropdown', 'value')]
)
def update_right_pie_chart(selected_user):
    data = read_database()
    hours = calculate_hours_per_project(data)
    right_pie_chart = plot_hours_per_project(hours, selected_user)
    return right_pie_chart

@app.callback(
    Output('average-hours-chart', 'figure'),
    [Input('average-hours-chart', 'id')]
)
def update_average_hours_chart(_):
    data = read_database()
    average_hours_chart = plot_average_hours(data)
    return average_hours_chart

@app.callback(
    Output('total-hours-chart', 'figure'),
    [Input('total-hours-chart', 'id')]
)
def update_total_hours_chart(_):
    data = read_database()
    total_hours, date_range = calculate_total_hours_per_user(data)
    total_hours_chart = plot_total_hours_per_user(total_hours, date_range)
    return total_hours_chart

@app.callback(
    Output('average-hours-per-user-chart', 'figure'),
    [Input('average-hours-per-user-chart', 'id')]
)
def update_average_hours_per_user_chart(_):
    data = read_database()
    average_hours = calculate_average_hours_per_user(data)
    average_hours_per_user_chart = plot_average_hours_per_user(average_hours)
    return average_hours_per_user_chart

if __name__ == '__main__':
    app.run_server(debug=True)
