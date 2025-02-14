import sqlite3
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
from config import PATH_TO_DATA
import json

DATABASE_PATH = PATH_TO_DATA + "/20250214-010326/generate_database.db"
PARAMETERS_PATH = PATH_TO_DATA + "/20250214-010326/parameter_run_20250214-010326.json"

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
    ], style={'display': 'flex', 'flex-wrap': 'wrap', 'justify-content': 'space-between'})
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

if __name__ == '__main__':
    app.run_server(debug=True)
