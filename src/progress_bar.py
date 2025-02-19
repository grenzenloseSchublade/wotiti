import time
import dash_html_components as html
import dash_core_components as dcc
from dash.exceptions import PreventUpdate
from dash_extensions.enrich import Output, Dash, Trigger, FileSystemCache

steps, sleep_time = 100, 0.1
# Create example app.
app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([
    html.Button("Click me", id="btn"), html.Div(id="progress"), html.Div(id="result"),
    dcc.Interval(id="interval", interval=500)
])
# Create a server side resource.
fsc = FileSystemCache("cache_dir")
fsc.set("progress", None)


@app.callback(Output("result", "children"), Trigger("btn", "n_clicks"))
def run_calculation():
    for i in range(steps):
        fsc.set("progress", str((i + 1) / steps))  # update progress
        time.sleep(sleep_time)  # do actual calculation (emulated by sleep operation)
    return "done"


@app.callback(Output("progress", "children"), Trigger("interval", "n_intervals"))
def update_progress():
    value = fsc.get("progress")  # get progress
    if value is None:
        raise PreventUpdate
    return "Progress is {:.0f}%".format(float(fsc.get("progress")) * 100)


if __name__ == '__main__':
    app.run_server()