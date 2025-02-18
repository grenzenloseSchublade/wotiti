import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
import pandas as pd
from config import PATH_TO_DATA
from calculations import calculate_hours_per_project, calculate_total_hours_per_user, calculate_average_hours_per_user, calculate_average_hours_per_period
from plotting import plot_hours_per_project, plot_total_hours_per_user, plot_average_hours_per_user, plot_average_hours_per_period
from utils import read_database, browse_directory, find_database_and_parameters, read_parameters
from utils import MODERN_COLORS, SYNTHWAVE_COLORS

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
