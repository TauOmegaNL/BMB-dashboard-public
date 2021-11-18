# Import libraries
import dash_core_components as dcc
import dash_html_components as html
import sys
import os

sys.path.insert(0, os.getcwd())

# Connect to main app.py file
from core import app
# Connect to your app pages
from core import dl, vk, ik
from core.data_utils import load_location_data, load_gdf_from_json
from core.utils import get_callback_trigger
from core.apps.pagina_data_laden import load_mjs

import dash
from dash import no_update
from dash.dependencies import Input, Output, State

import base64

# Set Standard variables
button_style = {'width': '10%',
                'heigth': '5%',
                'margin-top': '0.1%',
                'margin-left': '0.1%',
                'padding': '0px'}

list_style = {'list-style-type': 'none',
              'display': 'inline',
              'margin-top': '2px',
              'margin-bottom': '2px'}


THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(THIS_FOLDER, '..', 'afbeeldingen', "181205-bibliotheek-plectrum-only.png")
encoded_logo = base64.b64encode(open(logo_path, 'rb').read()).decode('ascii')

app.layout = html.Div([
    html.Title('Monitor van de Stad'),
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='shape-data', storage_type='session'),
    dcc.Store(id='layer-data', storage_type='session'),
    dcc.Store(id='dataset-counter', storage_type='session', data=0),
    dcc.Loading(dcc.Store(id='data', storage_type='session', data={}), fullscreen=True, color='#ff7320',
                style={'opacity': '0.2'}),
    dcc.Store(id='real-time-data', storage_type='session', data={}),
    dcc.Interval(id='real-time-trigger',
                 interval=1000 * 60 * 15,
                 n_intervals=0,
                 disabled=True),
    html.Ul([
        html.Li(
            html.A(html.Div(
                html.Img(src='data:image/png;base64,{}'.format(encoded_logo),
                         style={'width': '2%',
                                'margin-right': '1%',
                                'margin-top': '0.3%',
                                'float': 'left'}),
                id='logo'), href='/'), style=list_style),
        html.Li(dcc.Link(html.Button('Datasets', id='Datasets_knop',
                                     style=button_style),
                         href='/apps/BMB_datasets'),
                style=list_style),
        html.Li(dcc.Link(html.Button('Data-interactie', id='Interactie_kaart_knop',
                                     style=button_style),
                         href='/apps/BMB_interactie_kaart'),
                style=list_style),
        html.Li(dcc.Link(html.Button('Datavisualisatie', id='Visualisatie_kaart_knop',
                                     style=button_style),
                         href='/apps/BMB_visualisatie_kaart'),
                style=list_style)
    ], id='top_bar', className='row', style={'vertical-align': 'top', 'display': 'inline-block', 'width': '100%'}),
    html.Br(),
    html.Div(id='page-content'),
    html.Footer(['© Gemaakt door Tau Omega in samenwerking met Bibliotheek Midden-Brabant. ',
                html.A('Github.', href='https://github.com/')], style={'display': 'flex'},
                id='footer')

], id='main-div')


@app.callback([Output('page-content', 'children'),
               Output('top_bar', 'hidden'),
               Output('footer', 'hidden')],
              [Input('url', 'pathname')])
def display_page(pathname):
    hide_datasets = pathname != '/apps/BMB_datasets' and pathname != '/'
    layout = [html.Div(dl.layout, hidden=hide_datasets)]
    if pathname == '/apps/BMB_interactie_kaart':
        layout.append(ik.layout)
        return layout, False, False
    if pathname == '/apps/BMB_visualisatie_kaart':
        layout.append(vk.layout)
        return layout, True, True

    return layout, False, False


@app.callback(Output('main-div', 'style'),
              Input('url', 'pathname'))
def reset_style(pathname):
    if pathname == '/apps/BMB_visualisatie_kaart':
        return {'margin-top': '-24px',
                'width': '100'}
    else:
        return {
            'margin-left': '2%',
            'margin-right': '2%'
        }


###################################################### Real Time ######################################################
@app.callback([Output('real-time-data', 'data'),
               Output('real-time-trigger', 'disabled')],
              [Input('real-time-trigger', 'n_intervals'),
               Input('mjs-load-button', 'n_clicks'),
               Input('mjs-location-type', 'value'),

               Input('ed-delete-button-yes', 'n_clicks'),
               State('custom-dataset-delete-name', 'value'),

               State('shape-data', 'data'),
               State('real-time-data', 'data')])
def load_real_time_data(n_intervals, mjs_n_clicks, mjs_location_type,
                        delete_clicks, delete_dataset_name,
                        shape_data, data):
    ctx = dash.callback_context
    trigger = get_callback_trigger(ctx)

    if delete_clicks and trigger == 'ed-delete-button-yes':
        data.pop(delete_dataset_name)
        return data, True

    if mjs_n_clicks > 0 and trigger == 'mjs-load-button':
        if shape_data is None:
            shape_data = {}
        if mjs_location_type in shape_data:
            shapes = load_gdf_from_json(shape_data[mjs_location_type])
        else:
            shapes = load_location_data(level=mjs_location_type, gemeente='Tilburg')
        mjs_df, start, end = load_mjs(shapes, mjs_location_type)
        mjs_columns = list(mjs_df.columns)
        data['meet je stad'] = {'data': mjs_df.to_json(),
                                'date_1': start.strftime('%Y-%m-%d %H:%M:%S'),
                                'date_2': end.strftime('%Y-%m-%d %H:%M:%S'),
                                'columns': mjs_columns,
                                'region_type': mjs_location_type}
        return data, False

    # If interval triggered or mjs button is clicked, load MJS
    if n_intervals > 0 and trigger == 'real-time-trigger':
        if len(data) == 0:
            return no_update
        mjs_location_type = data['meet je stad']['region_type']
        shapes = load_gdf_from_json(shape_data[mjs_location_type])

        print(f'MJS loaded\nInterval: {n_intervals}')
        mjs_df, start, end = load_mjs(shapes, mjs_location_type)
        mjs_columns = list(mjs_df.columns)
        data['meet je stad'] = {'data': mjs_df.to_json(),
                                'date_1': start.strftime('%Y-%m-%d %H:%M:%S'),
                                'date_2': end.strftime('%Y-%m-%d %H:%M:%S'),
                                'columns': mjs_columns,
                                'region_type': mjs_location_type}
        print(f"Time: {end.strftime('%H:%M:%S')}\n")

        return data, False

    return no_update


if __name__ == '__main__':
    app.run_server(debug=False)
