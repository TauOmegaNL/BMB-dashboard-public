import pathlib
import plotly.express as px
import dash_html_components as html
import os

opj = os.path.join

PATH = pathlib.Path(__file__).parent
IMAGE_PATH = PATH.joinpath("afbeeldingen").resolve()
DATA_PATH = PATH.joinpath("datasets").resolve()

plot_colors = px.colors.qualitative.Plotly

graph_div_style = {
    'border-color': '#0c423e',
    'border-width': '4px',
    'border-style': 'solid',
    'border-radius': '5px'
}

upload_button_style = {
    'width': '100%',
    'height': '60px',
    'lineHeight': '60px',
    'borderWidth': '1px',
    'borderStyle': 'dashed',
    'borderRadius': '5px',
    'textAlign': 'center',
    'margin': '10px'
}

tooltip_style = {
    'font-size': '14px'
}


def underline_style(text: str, id: str):
    return html.Span(text, id=id, style={"textDecoration": "underline",
                                         'cursor': 'pointer'})

def get_callback_trigger(ctx):
    if not ctx.triggered:
        button_id = 'No trigger'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    return button_id
