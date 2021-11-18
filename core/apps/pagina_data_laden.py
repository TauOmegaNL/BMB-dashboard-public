import pandas as pd
import numpy as np
import geopandas as gpd
import base64
from datetime import timedelta, datetime

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash import no_update
import json
import os
from dash.dependencies import Input, Output, State

from core.app_multipage import app

# Import own functions
from core.utils import upload_button_style, underline_style, get_callback_trigger, tooltip_style
from core.data_utils import load_meet_je_stad, aggregate_point_data, load_location_data, \
    read_file, load_dataplatform_data, _get_code, load_gdf_from_json, combine_data_dicts

standard_datasets = ['meet je stad']

# Let the program know in what folder it is in
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

layout = dbc.Row([
    dbc.Col([
        # Choose which type of data you want to add or delete
        html.P('Selecteer dataopties:'),
        dcc.Dropdown(options=[
            {'label': 'Meet je stad', 'value': 'MJS'},
            {'label': 'Dataplatform API', 'value': 'DP'},
            {'label': 'Dataset toevoegen', 'value': 'ED_add'},
            {'label': 'Dataset aggregeren', 'value': 'DA'},
            {'label': 'Dataset verwijderen', 'value': 'ED_delete'},
        ], id='dataload-type', multi=False, style=dict(width='100%')),

        html.Div(id='dataloader')
    ], width=4),
    dbc.Col(
        # Show a dataset as a table
        dcc.Loading([
            html.P(['Selecteer data voor ', underline_style('controletabel', id='controletabel-underline'), ': ']),
            dcc.Dropdown(id='show-data-dropdown', style=dict(width='70%'),
                         children=[]),
            html.Div(id='data-shower', style={'overflow-x': 'auto', 'overflow-y': 'auto', 'height': '80vh'},
                     ),
        ], color='#ff7320'), width=8),
    dbc.Tooltip(
        dcc.Markdown("""In de controlletabel kan je controleren of het inladen van de dataset goed is gegaan.
                     Waar je op moet letten:
                     - Is de tabel ingeladen zonder **foutmeldingen**?
                     - Staan alle **kolommen** in de tabel die je verwacht?
                     - Zijn de kolommen van het **aggregeren** correct toegevoegd?
                     - Zijn de getallen met een **punt** in plaats van een **komma**?""", style={'text-align': 'left'}),
        id='controletabel-hover',
        target='controletabel-underline',
        placement='right',
        style=tooltip_style
    ),
])


@app.callback([Output('dataloader', 'children')],
              [Input('dataload-type', 'value')])
def dataloader(choice):
    """
    This callback adds all Divs from other dataset loaders into one Div. Only the divs that are not hidden will be shown
    """
    content = []

    content.extend(mjs_loader(choice != 'MJS'))
    content.extend(dataplatform_api_loader(choice != 'DP'))
    content.extend(dataset_aggregation_loader(choice != 'DA'))
    content.extend(custom_dataset_loader(choice != 'ED_add'))
    content.extend(custom_dataset_deleter(choice != 'ED_delete'))

    loader = [html.Div(content, )]
    return loader


@app.callback(Output('dataload-type', 'value'),
              Output('dataset-counter', 'data'),
              Input('real-time-data', 'data'),
              Input('data', 'data'),
              State('dataset-counter', 'data'),
              prevent_initial_callbacks=True)
def close_menu(rt_data, data, dataset_counter):
    data = combine_data_dicts(data, rt_data)
    if len(data) != dataset_counter:
        return None, len(data)
    return no_update


######################################################### MJS #########################################################
def mjs_loader(hidden):
    toelichting_mjs = """
    Meet je stad is een initiatief voor burgerwetenschap om onder andere het klimaat in de stad in kaart te brengen.
    Het collectief heeft burgers meetstations laten ophangen bij hun in de buurt om zo het aspecten van het klimaat te
    meten. Het voordeel ten opzichte van de meetstations van KNMI is dat ze meten hoe het in de leefomgeving van
    burgers er aan toe is. Een meetstation kan hangen bij de buren of de lokale bibliotheek. Een nadeel hiervan is dat
    de meetstations gevoelig zijn voor plotselinge veranderingen. Zo kan het ene meetstation in de schaduw staan op het
    balkon en de andere per ongelijk boven een barbeque hangen. Maar met genoeg dekking binnen een buurt of wijk zal
    dit alsnog een goed beeld geven.
    """
    # Meet je stad loader
    loader = [
        html.Div([
            html.H5('Meet je stad data laden'),
            html.P([
                'Meet je stad sensoren sturen elke 30 minuten een update. De meest recente data van elke sensor wordt '
                'ingeladen.',
                html.A(
                    html.P(
                        "Meer toelichting over de Meet je stad dataset.", style={'text-decoration': 'underline'}
                    ), id='toelichting-mjs-link'
                )
            ]),
            html.Div([
                dbc.Collapse(dbc.Card(dbc.CardBody(toelichting_mjs)), id="collapse-mjs-toelichting"),
                html.Br()
            ]),
            html.P('Selecteer hieronder of je de data op buurt, wijk of gemeente niveau wilt hebben:'),
            dcc.Dropdown(id='mjs-location-type', options=[
                {'label': 'Buurt', 'value': 'Buurt'},
                {'label': 'Wijk', 'value': 'Wijk'},
                {'label': 'Gemeente', 'value': 'Gemeente'},
            ]),
            html.Br(),
            html.Button('Meet je stad inladen',
                        id='mjs-load-button',
                        n_clicks=0)
        ],
            hidden=hidden)
    ]
    return loader


def load_mjs(shapes, location_code='Buurt', gemeente='Tilburg'):
    """
    This function loads the Meet Je Stad data. The real MJS loader is in data utils, but this function sets the
    inputs into the correct format and then calls the real loader. Then it processes and aggregates the output to a
    mean at every location type. (Mean temperature per Buurt/Wijk/Gemeente)
    """
    code_column = _get_code(location_code)
    code_name = code_column[:-4] + 'NAAM'

    start = datetime.now() - timedelta(hours=1)
    end = datetime.now()
    df = load_meet_je_stad(start, end, return_dates=False)
    # If there are multiple sensors in the dataset, only use the last entry.
    df = df.groupby('id', as_index=False, sort=False).last().sort_values(by='timestamp').reset_index(drop=True)
    mjs_aggregate = aggregate_point_data(df, shapes,
                                         level=location_code)  # add location code as column to the dataframe

    # Drop unnecessary rows (points outside selected gemeente) and columns
    mjs_aggregate = mjs_aggregate.loc[mjs_aggregate[code_column] != 'onbekend',
                                      [code_column, code_name, 'temperature', 'humidity', 'geometry']]
    mjs_geometry = mjs_aggregate[[code_column, 'geometry']].groupby(code_column, as_index=False).last()  # get geometry
    # From every location level, take the mean. Then merge back with the geometry column.
    mjs_aggregate = mjs_aggregate.groupby([code_column, code_name], as_index=False).mean().merge(mjs_geometry,
                                                                                                 on=code_column)
    if not isinstance(mjs_aggregate, gpd.GeoDataFrame):
        mjs_aggregate = gpd.GeoDataFrame(mjs_aggregate)
    return mjs_aggregate, start, end


@app.callback(
    Output("collapse-mjs-toelichting", "is_open"),
    [Input("toelichting-mjs-link", "n_clicks")],
    [State("collapse-mjs-toelichting", "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


################################################### Dataplatform API ###################################################
def dataplatform_api_loader(hidden):
    tooltip_geojson = [
        dcc.Markdown('**GeoJson** is een bestandsformat die specifiek werkt voor geografische data. Deze bestanden '
                     'staan in een _JSON_ format die makkelijk ingelezen kan worden. Zorg dat de URL altijd begint met '
                     '_ckan.dataplatform.nl_ en eindigt met _.json_')
    ]
    loader = [
        html.Div([
            html.H5('Dataset toevoegen vanuit dataplatform.nl'),
            html.P(['Dataplatform.nl is een platform voor open data. Hier delen gemeentes hun data over verschillende '
                    'onderwerpen. ',
                    html.A('Zie hier de datasets van Tilburg.',
                           href='https://www.dataplatform.nl/#/data?search_input=Tilburg',
                           target='_blank'),
                    ''' Het is de bedoeling dat je eerst selecteert welke dataset je wilt gebruiken.''']),

            # Every dataset has to have a name which will be the key in the data storage dictionary
            html.P('Naam dataset: '),
            dcc.Input(placeholder='Naam dataset', id='dataplatform-name', type='text', required=True),
            html.Br(), html.Br(),
            html.P([underline_style('GeoJSON URL: ', id='dataplatform-url-kop')]),
            dcc.Input(placeholder='URL', id='dataplatform-url', type='url', style=dict(width='100%'),
                      pattern='(https://)?ckan[.]dataplatform[.]nl/dataset/.*[.]json$', n_submit=0),
            html.Br(), html.Br(),
            html.Button('Dataset inladen', id='dataplatform-laden', n_clicks=0),
            dbc.Tooltip(
                tooltip_geojson,
                id='dataplatform-url-hover',
                target='dataplatform-url-kop',
                placement='right',
                style=tooltip_style
            ),
        ], hidden=hidden, )
    ]
    return loader


@app.callback(Output('dataplatform-name', 'value'),
              Output('dataplatform-url', 'value'),
              Input('dataplatform-laden', 'n_clicks'))
def reset_options(clicks):
    ctx = dash.callback_context
    trigger = get_callback_trigger(ctx)
    if trigger == 'dataplatform-laden' and clicks > 0:
        return None, None
    return no_update


################################################# Dataset aggregating #################################################
def dataset_aggregation_loader(hidden):
    loader = html.Div([
        html.H5('Dataset aggregeren'),
        html.P('Aggregeren van dataset betekent dat de gegevens in een dataset samengevoegd worden om op een hoger '
               'niveau de data te analyseren. Het is hier mogelijk om van coordinaten te aggregeren naar Tilburgse'
               ' buurt, wijk en gemeente niveau. '),
        html.P('Selecteer een dataset:'),
        dcc.Dropdown(id='data-aggregate-datasets'),
        dbc.Alert([html.P(
            'Aggregeren betekent dat de gegevens in een dataset op een hoger niveau worden samengevoegd. Het is alleen '
            'mogelijk om coördinaten te aggregeren naar buurt-, wijk- en gemeenteniveau.')],
            id='data-aggregate-latlong-warning', is_open=False, color='warning'),
        html.Div([
            html.Br(),
            html.P('Selecteer naar welk niveau de data geaggregeerd moet worden:'),
            dcc.Dropdown(options=[
                {'label': 'Buurt', 'value': 'Buurt'},
                {'label': 'Wijk', 'value': 'Wijk'},
                {'label': 'Gemeente', 'value': 'Gemeente'},
            ], id='data-aggregate-level'),
            html.Br(),

            html.Button('Aggregeer data', id='data-aggregate-button', n_clicks=0)
        ], hidden=True, id='data-aggregate-options')

    ], hidden=hidden)

    return [loader]


@app.callback(Output('data-aggregate-datasets', 'options'),
              [Input('dataload-type', 'value'),
               Input('data', 'data')])
def fill_data_aggregate_dropdown(menuvalue, data):
    """
    Fill the dropdown with dataset names\
    Menuvalue only used as a trigger for the callback
    """
    return [{'label': k, 'value': k} for k in data.keys()]


@app.callback([Output('data-aggregate-latlong-warning', 'is_open'),
               Output('data-aggregate-options', 'hidden')],
              [Input('data-aggregate-datasets', 'value'),
               State('data', 'data')])
def data_aggregate_latlong_warning(dataset_name, data):
    if data is {} or dataset_name is None:
        return False, False

    read_type = data[dataset_name]['read_type']
    bool_read_type_latlong = read_type != 'latlong'
    return bool_read_type_latlong, bool_read_type_latlong


def aggregate_data(shapes, data, level):
    dataset = data['data']
    datadict = json.loads(dataset)
    data = gpd.GeoDataFrame.from_features(datadict['features']).loc[:, data['columns']]
    gdf = aggregate_point_data(data, shapes, level=level)  # add location code as column to the dataframe
    return gdf


#################################################### Custom dataset ####################################################
def custom_dataset_loader(hidden):
    toelichting_custom_dataset = [
        dcc.Markdown('De data lader kan alleen omgaan met **Excel (.xlsx) of textbestanden (.txt en .csv)**. Daarnaast '
                     'verwacht de datalader dat de data altijd gekoppeld is aan een lengte-/breedtegraad ('
                     'latitude/longitude) of een van de gestandaardiseerde codes voor wijken en buurten.'),
        html.Br(),
        dcc.Markdown(
            'Een nette dataset heeft altijd **kolomnamen**. Zorg ook dat boven elke kolom een beschrijving van 1 '
            'of 2 woorden heeft dat verklaard wat er in die kolom staat. Zet deze bovenaan de tabel.'),
        html.Br(),
        dcc.Markdown('In dit dashboard wordt gewerkt op buurt, wijk en gemeente niveau. Als jouw data verzameld is '
                     'per buurt/wijk/gemeente dan is dat goed! Is de data verzameld op longitude/latitude, '
                     'dan zul je de **data moeten omrekenen naar een van de beschikbare opties**.')
    ]

    tooltip_locatiedata = [
        dcc.Markdown('Er zijn twee verschillende soorten data die je kan inladen: **Coordinaten en Regiocodes**. De '
                     'coordinaten (lengte-/breedtegraad) verwacht dat er twee kolommen zijn in de dataset waarvan '
                     'een de lengtegraad en de andere de breedtegraad omvat.'),
        html.Br(),
        dcc.Markdown('Er zijn drie soorten regiosoorten: Buurt, Wijk, en Gemeente. Elke regio in Nederland heeft '
                     'een unieke code. In die code staat verwezen naar wat voor soort regio dat is. Zo zal een '
                     'buurtcode altijd beginnen met BU en een gemeentecode altijd beginnen met GM.')
    ]

    tooltip_scheidingsteken = [
        dcc.Markdown('Een tekstbestand met data hoort altijd een **scheidingsteken** te hebben. Dit teken is vaak een '
                     'komma of een puntkomma die de kolommen van elkaar scheidt. Een tabel ziet er dan zo uit als '
                     'de ; het scheidingsteken is:'),
        html.P(['Kolom1;Kolom2;Kolom3', html.Br(), '1;2;3', html.Br(), '4;5;6'], style={'font-family': 'Consolas',
                                                                                        'text-align': 'left'})
    ]

    tooltip_header = [
        dcc.Markdown('Elke nette dataset heeft goede kolomnamen. Deze staan vaak bovenaan de dataset. Heeft jouw '
                     'dataset geen kolomnamen? Voeg dan een beschrijving van een of twee worden aan elke kolom toe')
    ]
    # Custom dataset loader
    loader = [
        html.Div([
            dcc.Store('temp-data', 'memory', data={}),
            html.H5('Eigen dataset toevoegen'),
            underline_style("Toelichting over de data lader.", id='toelichting-ed-link'),
            html.Div([
                dbc.Collapse(dbc.Card(dbc.CardBody(toelichting_custom_dataset)), id="collapse-ed-toelichting"),
            ]),
            # Upload drag and drop
            dcc.Upload(
                id='custom-dataset-upload',
                children=html.Div([
                    html.A('Sleep hier je dataset of selecteer een bestand')
                ]), style=upload_button_style, multiple=False,
            ),

            # Every dataset has to have a name which will be the key in the data storage dictionary
            html.P('Naam dataset: '),
            dcc.Input(placeholder='Naam dataset', id='custom-dataset-name', type='text', required=True),
            html.Br(),
            # Make a div that is standard hidden, but will be shown when a dataset is loaded
            # These are the options that can be edited right now
            html.Div([
                html.P(['Selecteer de type ', underline_style('locatiedata', 'custom-dataset-read-type-hover'), ':']),
                dcc.Dropdown(id='custom-dataset-read-type',
                             options=[
                                 {'label': 'Lengte-/Breedtegraad', 'value': 'latlong'},
                                 {'label': 'Buurt code', 'value': 'Buurt'},
                                 {'label': 'Wijk code', 'value': 'Wijk'},
                                 {'label': 'Gemeente code', 'value': 'Gemeente'}
                             ]),
                dbc.Tooltip(
                    tooltip_locatiedata,
                    id='custom-dataset-read-type-hover',
                    target='custom-dataset-read-type-hover',
                    style=tooltip_style
                ),

                # latitude longitude options options
                html.Div([
                    html.P('Vul breedte en lengtegraad kolomnamen in'),
                    html.P('Breedtegraad (latitude):'),
                    dcc.Dropdown(id='custom-dataset-latitude'),
                    html.P('Lengtegraad (longitude):'),
                    dcc.Dropdown(id='custom-dataset-longitude'),
                ], id='custom-dataset-latlong-options', hidden=True),

                # code column for buurt/wijk/gemeente options
                html.Div([
                    html.P('Selecteer de code kolom'),
                    dcc.Dropdown(id='custom-dataset-code-col')
                ], id='custom-dataset-code-options', hidden=True),

                # Sep options
                html.Div([
                    html.P(['Kies het ', underline_style('scheidingsteken', id='custom-dataset-load-sep-hover'), ':']),
                    dcc.Input(id='custom-dataset-load-sep', type='text'),
                ], id='custom-dataset-show-sep'),
                dbc.Tooltip(
                    tooltip_scheidingsteken,
                    id='custom-dataset-sep-hover',
                    target='custom-dataset-load-sep-hover',
                    style=tooltip_style
                ),

                # Header options
                html.P(
                    ['In welke rij zitten de ', underline_style('kolomnamen', id='custom-dataset-kolom-hover'), ':']),
                dcc.Input(id='custom-dataset-kolom', value=1, type='number', min=1),
                dbc.Tooltip(
                    tooltip_header,
                    id='custom-dataset-kolom-hover',
                    target='custom-dataset-kolom-hover',
                    style=tooltip_style
                ),
                dbc.Alert(children=[], color='warning', is_open=False, id='custom-dataset-kolom-alert'),
                html.Br(),
                html.Button('Dataset inladen', id='ed-load-button', n_clicks=0),
            ], id='custom-dataset-load-options', hidden=True),

        ], hidden=hidden, style=dict(width='100%'))
    ]
    return loader


@app.callback(
    Output("collapse-ed-toelichting", "is_open"),
    [Input("toelichting-ed-link", "n_clicks")],
    [State("collapse-ed-toelichting", "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


@app.callback([Output('custom-dataset-latlong-options', 'hidden'),
               Output('custom-dataset-code-options', 'hidden')],
              Input('custom-dataset-read-type', 'value'))
def unhide_read_options(read_type):
    if read_type == 'latlong':
        # unhide latlong, hide code
        return False, True
    elif read_type == 'Buurt' or read_type == 'Wijk' or read_type == 'Gemeente':
        # hide latlong, unhide code
        return True, False
    return True, True


@app.callback(Output('temp-data', 'data'),
              [Input('custom-dataset-upload', 'contents'),
               State('custom-dataset-upload', 'filename')])
def load_data(contents, filename):
    if contents is None:
        return no_update

    # Load first 5 rows
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    max_len = 50

    options_df, sep = read_file(filename, contents=decoded, nrows=max_len, make_geo=False, return_sep=True)

    # join the columns and the first line with the guessed separator. This makes it possible to guess change the
    # separator afterwards
    columns = f'{sep}'.join(list(options_df.columns))
    return {'dataframe': options_df.to_json(),
            'columns': columns,
            'sep': sep,
            'filename': filename,
            'length': len(options_df),
            'max_length': max_len}


@app.callback([Output('custom-dataset-load-options', 'hidden'),
               Output('custom-dataset-name', 'value'),

               Output('custom-dataset-latitude', 'value'),
               Output('custom-dataset-latitude', 'options'),

               Output('custom-dataset-longitude', 'value'),
               Output('custom-dataset-longitude', 'options'),

               Output('custom-dataset-code-col', 'value'),
               Output('custom-dataset-code-col', 'options'),

               Output('custom-dataset-load-sep', 'value'),
               Output('custom-dataset-kolom', 'value')],
              [Input('temp-data', 'data'),
               Input('dataload-type', 'value'),
               Input('custom-dataset-load-sep', 'value'),
               Input('custom-dataset-kolom', 'value')])
def set_options(data, datachoice, sep, header):
    """
    This function makes the options for loading a new dataset from a csv or xlsx file. It is called when the dropdown is
    set on 'Eigen dataset toevoegen'


    Input:
    data <dict>
        This is a dictionary with the loaded dataframe, guessed separator, string of columns and the filename
    datachoice <str>
        This is the value of the dropdown. 'Eigen dataset toevoegen' has value 'ED_add'
    sep <str>
        This is the manually overwritten separator. When this changes, the columns dropdown should be changed
        accordingly
    header <int>
        This is the manually overwritten headerrow. When this changes, the selected row will be taken as dropdown.

    Output:
    Hidden <bool>
        Wheter to hide the options in the dashboard
    dataset_name <str>
        Name of dataset. This is the filename without extension by default.
    latcol, longcol <str>
        Guessed latitude and longitude columns names
    column_options <list of str>
        All the columns in the dataset which could be the latitude or longitude columns
    sep <str>
        Separator for csv or txt columns
    Header row <int>
        The row in which the header is placed.
    """
    # Get reason for callback
    ctx = dash.callback_context

    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if datachoice != 'ED_add' or data == {}:
        return True, None, None, [], None, [], None, [], None, 1

    if button_id == 'temp-data':
        # When a new dataset is loaded, reset the values
        sep = None
        header = 1

    columns = data['columns']
    data_sep = data['sep']
    options_df = pd.DataFrame(json.loads(data['dataframe']))
    filename = data['filename']
    dataset_name = filename.split('.')[0]

    # If file is excel, then the columns are automatically correct. Use df columens then
    if filename.endswith('xlsx'):
        if header is not None and header > 1:
            header = min(header, len(options_df) - 1)
            columns = options_df.iloc[header, :].tolist()
        else:
            columns = options_df.columns

    else:
        # If header is not one the first row, ensemble a textversion of the given headerrow from the dataframe
        if header is not None and header > 1:
            header = min(header, len(options_df) - 1)
            columns = f'{data_sep}'.join([str(ii) for ii in options_df.iloc[header, :]])
        # If something went wrong with the sep guessing, then the guesses sep is ignored and the manually given sep is
        # used
        if sep is None or sep == '':
            columns = columns.split(data_sep)
        else:
            columns = columns.split(sep)

    # Get latitude, longitude and code columns
    latcol = None
    longcol = None
    codecol = None
    column_options = []
    for c in columns:
        # if column name is a string, then check if its latitude or longitude name
        if isinstance(c, str):
            c_lower = c.lower()
            if 'lat' in c_lower or 'breedtegraad' == c_lower:
                latcol = c
            if 'long' in c_lower or 'lengtegraad' == c_lower:
                longcol = c
        # if columns is None, convert None to string
        elif c is None:
            c = 'None'
        # if column is a NaN, then convert NaN to string
        else:
            if np.isnan(c):
                c = 'nan'

        column_options.append({'label': c, 'value': c})

    if sep is None and button_id != 'custom-dataset-load-sep':
        # if the file is a txt or csv file, use the separator from the data loader
        if filename.endswith(('txt', 'csv')):
            # only use the guessed sep if it is a text file and no manual sep is given
            sep = data_sep

    return False, dataset_name, latcol, column_options, longcol, column_options, codecol, column_options, sep, header


@app.callback([Output('custom-dataset-kolom-alert', 'is_open'),
               Output('custom-dataset-kolom-alert', 'children')],
              [Input('custom-dataset-kolom', 'value'),
               State('temp-data', 'data')])
def show_header_alert(header, data):
    if len(data) == 0:
        return False, []

    data_length = data['length']
    # Check if header is equal to the length of the dataset -1 (-1 because of counting from 0)
    # if so, check if it is eqaul or greater than the maximum allowable dataset length for options
    if header >= data_length - 1:
        if header >= data['max_length'] - 1:
            children = [html.P('Om het inladen snel te houden is het alleen mogelijk om de eerste 50 rijen '
                               'als kolomnaam te gebruiken. Is dit niet het geval? Pas de dataset aan zodat de  '
                               'kolomnamen bovenaan staan. Datasets langer dan 50 rijen zijn wel toegestaan, maar de '
                               'gehele dataset wordt pas ingeladen als op de inlaad knop wordt geklikt.')]
        else:
            children = [html.P(f'Het rijnummer die je meegeeft is groter dan de dataset. Het nummer wordt gezet op '
                               f'{data_length - 1}')]

        return True, children

    return False, []


@app.callback(Output('custom-dataset-show-sep', 'hidden'),
              [Input('custom-dataset-upload', 'content'),
               Input('custom-dataset-upload', 'filename')])
def show_sep_with_file(content, filename):
    """
    If a xlsx file is given, dont show the option of choosing the separator
    """
    if filename is None:
        return no_update
    if filename.endswith('xlsx'):
        return True
    else:
        return False


################################################ Custom dataset deleter ################################################
def custom_dataset_deleter(hidden):
    # Custom dataset deleter
    loader = [
        html.Div([
            html.H5('Verwijder dataset'),
            # Choose which dataset needs to be delted
            dcc.Dropdown(placeholder='Naam dataset', id='custom-dataset-delete-name'),
            html.Div([
                # If the user wants to delete the dataset. This button will do that
                html.Button('Dataset verwijderen', id='ed-delete-button', n_clicks=0),
                # When the user asks to delete the dataset. We ask if the user is really sure
                dbc.Alert([
                    html.P('Weet je zeker dat je de dataset wil verwijderen?'),
                    dbc.Row([
                        dbc.Col(html.Button('Ja', id='ed-delete-button-yes', n_clicks=0)),
                        dbc.Col(html.Button('Nee', id='ed-delete-button-no', n_clicks=0)),
                    ])
                ], color='danger', is_open=True, id='ed-delete-safe')
            ],
                id='custom-dataset-delete-options', hidden=True)

        ], hidden=hidden, style=dict(width='100%'))
    ]
    return loader


@app.callback(Output('custom-dataset-delete-name', 'options'),
              Input('data', 'data'),
              Input('ed-delete-button-yes', 'n_clicks'),
              State('real-time-data', 'data'))
def change_deletable_datasets(data, n_clicks, rt_data):
    """
    This callback fills the dropdown of the deletable datasets. All datasets are deletable, except the standard ones.

    Input:
    data <dict>
        The big dataset storage dictionary

    n_clicks <int> The number of clicks that has been pressed on the 'yes i want to delete a dataset'-button. This
    variable is not used, but everytime a dataset is deleted, this dropdown needs to be updated

    rt_data <dict>
        The big dataset storage dictionary for real time data

    Output
    options <list>
        Dropdown options list
    """
    data = combine_data_dicts(data, rt_data)
    return [{'label': k, 'value': k} for k in data.keys()]


@app.callback(Output('custom-dataset-read-type', 'value'),
              Input('custom-dataset-upload', 'filename'))
def reset_dataset_options(filename):
    """
    Everytime a new dataset is uploaded, reset the dropdown where you can select the location type
    """
    return None


@app.callback(Output('custom-dataset-delete-options', 'hidden'),
              [Input('ed-delete-button-yes', 'n_clicks'),
               Input('custom-dataset-delete-name', 'value')]
              )
def custom_dataset_delete_options(delete_clicks, datachoice):
    """
    Makes part of dashboard where the custom datasets can be deleted. This is called if the dropdown is set on 'Eigen
    dataset verwijderen'

    Input:
    datachoice <str>
        This is the value of the dropdown. 'Eigen dataset verwijderen' has value 'ED_delete'
    delete_clicks <int>
        The number of times the button 'delete dataset' is pressed. If it is pressed, empty all values
    data <dict>
        Dictionary with all datasets

    Output:
    Hidden <bool>
        Wheter to hide the options in the dashboard
    """
    # Get reason for callback
    ctx = dash.callback_context

    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # If the dropdown is not a value, return a hidden empty options
    if datachoice is None:
        return True

    # If a dataset has been deleted, clear all the options
    if delete_clicks > 0 and button_id == 'ed-delete-button-yes':
        return True

    return False


@app.callback(Output('ed-delete-safe', 'is_open'),
              [Input('ed-delete-button', 'n_clicks'),
               Input('ed-delete-button-no', 'n_clicks'),
               Input('ed-delete-button-yes', 'n_clicks'),
               State('ed-delete-safe', 'is_open')])
def delete_dataset_are_you_sure(delete_button, no_button, yes_button, is_open):
    """
    Ask if the user is really sure that this dataset needs to be deleted.

    Input:
    delete_button <int>
        Number of times that the 'delete button' is clicked. But is more used as a trigger
    no_button <int>
        Number of times that the 'no do not delete button' is clicked. But is more used as a trigger
    is_open <bool>
        Whether or not the alert is shown (open) or not shown.

    Output:
    is_open <bool>
        The status of showing the alert or not.
    """
    ctx = dash.callback_context
    trigger = get_callback_trigger(ctx)

    if delete_button > 0 and trigger == 'ed-delete-button':  # delete button is pressed
        return not is_open
    elif no_button > 0 and trigger == 'ed-delete-button-no':  # if no button is pressed
        return False
    elif yes_button > 0 and trigger == 'ed-delete-button-yes':  # if yes button is pressed
        return False
    elif trigger == 'custom-dataset-delete-name':  # if a different dataset is selected
        return False

    return False


###################################################### Load data ######################################################
@app.callback([Output('data', 'data'),
               Output('shape-data', 'data')],
              # First set all buttons as input. Only if one of those buttons is pressed, the function will be called
              [Input('mjs-load-button', 'n_clicks'),
               Input('dataplatform-laden', 'n_clicks'),
               Input('dataplatform-url', 'n_submit'),
               Input('data-aggregate-button', 'n_clicks'),
               Input('ed-load-button', 'n_clicks'),
               Input('ed-delete-button-yes', 'n_clicks'),

               # MJS
               Input('mjs-location-type', 'value'),

               # Dataplatform API
               State('dataplatform-name', 'value'),
               State('dataplatform-url', 'value'),
               # Aggregate data
               State('data-aggregate-datasets', 'value'),
               State('data-aggregate-level', 'value'),
               # Loading custom dataset parameters
               State('custom-dataset-upload', 'contents'),
               State('custom-dataset-upload', 'filename'),
               State('custom-dataset-name', 'value'),
               State('custom-dataset-read-type', 'value'),
               State('custom-dataset-latitude', 'value'),
               State('custom-dataset-longitude', 'value'),
               State('custom-dataset-code-col', 'value'),
               State('custom-dataset-load-sep', 'value'),
               State('custom-dataset-kolom', 'value'),
               # Deletingting custom dataset parameters
               State('custom-dataset-delete-name', 'value'),
               State('data', 'data'),
               State('shape-data', 'data')])
def load_data(mjs_n_clicks, dp_n_clicks, url_n_submits, da_n_clicks, ed_n_clicks, ed_delete,
              mjs_location_type,
              dataplatform_name, dataplatform_url,
              aggregate_name, aggregate_level,
              upload_contents, upload_filename, dataset_name, dataset_read_type, dataset_latitude,
              dataset_longitude, dataset_codecol, dataset_sep, dataset_header,
              delete_name,
              data, shape_data):
    """
    The big data loading function. This function is used to load all the data into the Store. The function is triggered
    if either one of the buttons are pressed.
    mjs_n_clicks, ed_n_clicks, ed_delete <int>
        How many times this button has been clicked. Is more used as a trigger
    upload_contents <byte string>
        This is the content of the uploaded file in encoded bitstrings.
    upload_filename <str>
        This is the filename of the uploaded file without path
    dataset_name <str>
        Dataset name for custom dataset
    dataset_latitude, dataset_longitude <str>
        Latitude and longitude columns of dataset
    dataset_sep <str>
        Dataset separator. How are the txt or csv columns separated
    dataset_header <int>
        Dataset header row. Where are the header names placed
    delete_name<str>
        Dataset name for custom dataset that needs to be deleted
    data <dict>
        Dictionairy with all the loaded datasets and corresponding metadata
    """
    # what is the reason for the callback
    ctx = dash.callback_context
    trigger = get_callback_trigger(ctx)
    # if data is a string. Assume it is in json format
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            print(e)
            data = {}
    # Most of the time, the data will be a dictionary
    elif isinstance(data, dict):
        data = data.copy()
    # If data is anything else (probably None), make an empty dictionary
    else:
        data = {}

    # If the Meet Je Stad button is clicked, load MJS
    if mjs_n_clicks > 0 and trigger == 'mjs-load-button':
        if shape_data is None:
            shape_data = {}
        if mjs_location_type not in shape_data.keys():
            shapes = load_location_data(level=mjs_location_type, gemeente='Tilburg')
            shape_data[mjs_location_type] = shapes.to_json()

    if dp_n_clicks > 0 or url_n_submits > 0 and (trigger == 'dataplatform-laden' or trigger == 'dataplatform-url'):
        if dataplatform_name is None or dataplatform_name == '':
            dataplatform_name = 'Dataset zonder naam'
            iterator = 2
            while dataplatform_name in data.keys():
                dataplatform_name = f'Dataset zonder naam {iterator}'

        dp_df = load_dataplatform_data(dataplatform_url)
        read_type = 'latlong' if (dp_df.geom_type == 'Point').all() else 'onbekend'
        dp_columns = list(dp_df.columns)
        data[dataplatform_name] = {'data': dp_df.to_json(),
                                   'columns': dp_columns,
                                   'url': dataplatform_url,
                                   'read_type': read_type,
                                   'aggregated': False}

    if da_n_clicks > 0 and trigger == 'data-aggregate-button':
        if shape_data is None:
            shape_data = {}
        if aggregate_level in shape_data:
            shapes = load_gdf_from_json(shape_data[aggregate_level])
        else:
            shapes = load_location_data(level=aggregate_level, gemeente='Tilburg')
            shape_data[aggregate_level] = shapes.to_json()
        aggregated_data = aggregate_data(shapes, data[aggregate_name], aggregate_level)
        data[aggregate_name]['data'] = aggregated_data.to_json()
        data[aggregate_name]['aggregated'] = True
        data[aggregate_name]['columns'] = list(aggregated_data.columns)

    # If the Load Eigen Dataset button is clicked, load Eigen Dataset
    if ed_n_clicks and trigger == 'ed-load-button':
        content_type, content_string = upload_contents.split(',')
        decoded = base64.b64decode(content_string)
        if dataset_name == '':
            dataset_name = 'Dataset zonder naam'
            iterator = 2
            while dataset_name in data.keys():
                dataset_name = f'Dataset zonder naam {iterator}'
        try:
            ed_df = read_file(filename=upload_filename, contents=decoded, header=dataset_header,
                              read_type=dataset_read_type, latitude_col=dataset_latitude,
                              longitude_col=dataset_longitude, codecol=dataset_codecol, sep=dataset_sep,
                              path_to_shapes=os.path.join(THIS_FOLDER, '..', 'datasets', 'shape_data'))
        except ValueError as e:
            if dataset_read_type != 'latlong':
                data[dataset_name] = {'data': '{}',
                                      'error': 'De locatie data kon niet gekoppeld worden aan de gegeven dataset. '
                                               'Is de juiste locatie type aangegeven? En de juiste bijbehorende kolom '
                                               f'in de dataset?\nTechnische beschrijving: {e}'}
            else:
                data[dataset_name] = {'data': '{}',
                                      'error': 'Er is iets fout gegaan bij het inladen van de dataset. Technische '
                                               f'beschrijving: {e}'}
            return data, shape_data
        ed_columns = list(ed_df.columns)
        # Check if some columns are timestamps. Timestamps are not json serializable, so have to be converted to strings
        ts_bool = ed_df.dtypes.apply(lambda x: x == np.dtype('datetime64[ns]'))
        ed_df.loc[:, ts_bool] = ed_df.loc[:, ts_bool].apply(lambda x: x.dt.strftime('%Y-%m-%d %H:%M:%S'), axis=1)
        data[dataset_name] = {'data': ed_df.to_json(),
                              'read_type': dataset_read_type,
                              'latcol': dataset_latitude,
                              'longcol': dataset_longitude,
                              'codecol': dataset_codecol,
                              'header': dataset_header,
                              'sep': dataset_sep,
                              'columns': ed_columns,
                              'aggregated': False}
    # If the delete button is pressed, delete the dataset
    if ed_delete and trigger == 'ed-delete-button-yes':
        data.pop(delete_name)

    return data, shape_data


#################################################### Show dataset ####################################################
@app.callback([Output('show-data-dropdown', 'options'),
               Output('show-data-dropdown', 'disabled')],
              [Input('data', 'data'),
               Input('real-time-data', 'data')])
def dropdown_options(data, rt_data):
    """
    This function gets all the dataset names in the Stored dictionary and puts it in a dropdown.

    Input:
    data, rt_data <dict>
        Dictionary with all the datasets. The keys are the names of the dataset.

    Output:
    options <list>
        List with options for the dropdown.
    """
    data = combine_data_dicts(data, rt_data)
    if data is {}:
        return [], True
    keys = list(data.keys())
    # Make all the options for the dropdown with value and label the same value
    options = [{'label': k, 'value': k} for k in keys]
    options.append({'label': 'Laat geen data zien', 'value': 'Leeg'})
    return options, False


@app.callback(Output('data-shower', 'children'),
              [Input('show-data-dropdown', 'value'),
               Input('data', 'data'),
               Input('real-time-data', 'data')])
def show_data_in_table(dataset_name, data, rt_data):
    """
    If dataset is selected by the dropdown, show the first 10 rows in table format.

    Input:
    dropdown <str>
        Dataset name that needs to be shown
    data <dict>
        Dictionary with all the datasets. The keys are the names of the dataset.

    Output:
    Table <dbc.Table>
        Table with the first 10 rows of the selected dataset
    """
    # what is the reason for the callback
    ctx = dash.callback_context

    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    data = combine_data_dicts(data, rt_data)

    if dataset_name is None or dataset_name == 'Leeg' or dataset_name not in data.keys():
        # if nothing is selected show nothing.
        return html.Div(hidden=True)

    if 'error' in list(data[dataset_name].keys()):
        return dbc.Alert([html.P(data[dataset_name]['error'])], color='danger')

    # load dataset
    datadict = json.loads(data[dataset_name]['data'])
    columns = data[dataset_name]['columns']
    gdf = gpd.GeoDataFrame.from_features(datadict['features']).loc[:, columns]

    # Show dataset
    return dbc.Table.from_dataframe(pd.DataFrame(gdf.drop('geometry', errors='ignore', axis=1)).head(10),
                                    striped=True, bordered=True, hover=True, size='sm',
                                    style={'width': '30%'})
