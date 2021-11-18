import geopandas as gpd
import numpy as np
import json

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash import no_update, callback_context
from dash.dependencies import Input, Output, State, ALL

from core.app_multipage import app

# Import own functions
from core.data_utils import load_gdf_from_json, load_location_data, combine_data_dicts
from core.visualisatie_utils import plolty_figure_wrapper, plolty_gemeente_map_wrapper, basic_colors
from core.utils import get_callback_trigger, tooltip_style

available_colormaps = ['Blues', 'Reds', 'Greens', 'Purples', 'Bluered']
colormaps_options = [{"label": x, "value": x} for x in available_colormaps]

# The width of the text and choices of the question forms
text_width = 6
choice_width = 6

# These are simpeler names of the variable of figures to show in error messages
error_names = {"extra_vis_1" : "Grafiek 1",
                "extra_vis_2" : "Grafiek 2",
                "map_vis" : "Kaart visualisatie"}


def type_error_numeric(figure_name, inputtype, charttype, name, columnname, types):
    return f"{figure_name}: De {inputtype}-data van de {charttype} '{name}' moet numeriek zijn. De volgende data types komen voor in" \
           f" kolom '{columnname}': {types}"


# App layout
layout = html.Div([
    dbc.Modal([html.Button("Sluit", id='sluit-warnings-error-popup', className="ml-auto", n_clicks=0)],
              id='warning-error-popup', is_open=False, centered=True),
    dbc.Row([
        dcc.Store(id='save-layer-warnings-error-store', storage_type='session', data={'warning': [], 'error': []}),
        dcc.Store(id='update-graph-warnings-error-store', storage_type='session', data={'warning': [], 'error': []}),
        dcc.Store(id='update-map-warnings-error-store', storage_type='session', data={'warning': [], 'error': []}),
        # On the left we have two visualisations with a dropdown te select which visualization you would like to edit.
        dbc.Col([
            html.Details([
                html.Summary("Grafiek 1"),
                html.Div(id='extra-vis-1-total-div', children=[
                    html.Div(id="extra-vis-1-options", hidden=True),
                    html.Div(id="extra-vis-1-figure-div", children=[
                        dcc.Graph(id="extra-vis-1-figure",
                                  className='figureborder-mappage',
                                  style={'height': '38vh', 'margin-bottom': '0.4%'}, config = {"editable" : True}),
                    ], hidden=False),
                ], hidden=False),
            ], open=True),
            html.Details([
                html.Summary("Grafiek 2"),
                html.Div(id='extra-vis-2-total-div', children=[
                    html.Div(id="extra-vis-2-options", hidden=True),
                    html.Div(id='extra-vis-2-figure-div', children=[
                        dcc.Graph(id="extra-vis-2-figure",
                                  className='figureborder-mappage',
                                  style={'height': '38vh'}, config = {"editable" : True})
                    ], hidden=False),
                ], hidden=False),
            ], open=True),
            html.P("Verander of voeg visualisaties toe:"),
            dcc.Dropdown(id='selection-vis-to-change-dropdown',
                         options=[
                             {"label": 'Grafiek 1', "value": 'extra_vis_1'},
                             {"label": 'Grafiek 2', "value": 'extra_vis_2'},
                             {"label": 'Kaartvisualisatie', "value": 'map_vis'}],
                         multi=False)

        ], width=4),

        # On the right we have a figure for the map visualization
        dbc.Col([
            html.Div(
                id='map-vis-total-div', children=[
                    html.Div(id="map-vis-options", hidden=True),
                    html.Div(id="map-vis-figure-div", children=[
                        dcc.Graph(
                            id="map-vis", className='figureborder-mappage', style={'height': '83vh'}, config = {"editable" : True})
                    ], hidden=False),
                    dbc.Alert(children=[], id="map-warning-message",
                              is_open=False, color='danger')
                ], hidden=False),
            html.Button(id='open-warnings-error-popup', n_clicks=0,
                        children=['Bekijk foutmeldingen en waarschuwingen (0)'],
                        style={'margin-top': '1%',
                               'margin-bottom': '0%',
                               'margin-left': '60%',
                               'width': '40%'}),
        ], width=8)]),
])

######################################################### Fill dropdown options #########################################################
def _get_aggregate_visualization_options(index, value=""):
    # This function creates the options what to do with aggregated data. If there are multipile points per area the
    # data needs to be transformed to be visualized.
    formgroup = dbc.FormGroup([
                    dbc.Label(["Selecteer hoe waardes per gebied (BU/WK/GM) ",
                            html.Span("gecombineerd", id="gecombineerd-tooltip", style={'textDecoration': "underline"}),
                            " worden:"], width=text_width),
                    dbc.Tooltip(dcc.Markdown("""In een gebied kunnen meerdere waardes voorkomen. In de visualisatie kan maar één waarde getoond worden. Hier kun je kiezen hoe je meerdere waardes naar één waarde wil combineren.
                                                Gemiddelde:
                                                \[10, 15, 20\] -> 15
                                                Maximale:
                                                \[10, 15, 20\] -> 20
                                                Minimale:
                                                \[10, 15, 20\] -> 10
                                                Som:
                                                \[10, 15, 20\] -> 45
                                                Aantal:
                                                \[10, 15, 20\] -> 3
                                                """),
                                target='gecombineerd-tooltip',
                                placement='top',
                                style=tooltip_style),
                    dbc.Col(
                        dcc.Dropdown(id={'type': 'aggregate-method', 'index': index},
                                    options=[{"label": 'Gemiddelde van het gebied', 'value': 'mean'},
                                            {"label": 'De maximale waarde in het gebied',
                                            'value': 'max'},
                                            {"label": 'De minimale waarde in het gebied',
                                            'value': 'min'},
                                            {"label": 'De som van alle waarde in het gebied',
                                            'value': 'sum'},
                                            {"label": 'De hoeveelheid datapunten in het gebied',
                                            'value': 'frequency'},
                                            ],
                                    value=value),
                    ),
                ],
                row=True,
            )

    return formgroup


def _get_level_options(index, value=""):
    # This function creates the options to choose the level of the visualization.
    formgroup = create_formgroup("Kies niveau visualisatie:",
            dcc.Dropdown(id={'type': 'map-level', 'index': index},
                options=[{"label": 'Buurt', 'value': 'Buurt'},
                        {"label": 'Wijk', 'value': 'Wijk'},
                        {"label": 'Gemeente', 'value': 'Gemeente'}],
                value=value))

    return formgroup


def _group_values(gdf, groupby_value, group_method, group_to=None):
    "This functions groups a given geo dataframe with a certain method and then return the dataframe"

    if group_method == 'mean':
        gdf[group_to] = gdf[group_to].astype(float)
        grouped_df = gdf.groupby(groupby_value).mean().reset_index()

    elif group_method == 'max':
        gdf[group_to] = gdf[group_to].astype(float)
        grouped_df = gdf.groupby(groupby_value).max().reset_index()

    elif group_method == 'min':
        gdf[group_to] = gdf[group_to].astype(float)
        grouped_df = gdf.groupby(groupby_value).min().reset_index()

    elif group_method == 'sum':
        gdf[group_to] = gdf[group_to].astype(float)
        grouped_df = gdf.groupby(groupby_value).sum().reset_index()

    elif group_method == 'frequency':
        grouped_df = gdf.groupby(groupby_value).count().reset_index()

    else:
        grouped_df = gdf.groupby(groupby_value).mean().reset_index()

    return grouped_df

######################################################### General layout functions #########################################################
def create_formgroup(label_text, component, text_width = 6, choice_width = 6):
    formgroup = dbc.FormGroup(
        [
            dbc.Label(label_text,
                      width=text_width),
            dbc.Col(
                component,
                width=choice_width,
            ),
        ],
        row=True,
    )

    return formgroup


def _get_column_options(all_data, chosen_dataset, remove_geometry=True):
    """
    A function to filter the all_data dicitonary to get the correct dataset. After this we save the columns
    of the the dataset as a variable and remove 'geometry'. We then create an options dictionary for a
    dash dropdown
    """
    columns = all_data[chosen_dataset]['columns']
    if 'geometry' in columns and remove_geometry:
        columns.remove('geometry')
    options = [{'label': c, 'value': c} for c in columns]

    return options


def _button_layout(show_delete_button, index):
    """
    This function generates the layout of two buttons next to each other. Two options are given. First the option to
    show the delete button. This boolean definies if the delete button is shown or not. Second what the index of the
    button should be. This connects the buttons to a certain visualisation (scatter, barchart, etc.)
    """
    button_quit = dbc.Col(
        dbc.Button(
            'Opslaan en afsluiten',
            id={'type': 'button-quit', 'index': index},
            block=True,
            className='button',
            n_clicks=0)
    )

    button_delete = dbc.Col(
        dbc.Button(
            'Verwijder visualisatie',
            id={'type': 'button-delete', 'index': index},
            block=True,
            style={'font-family': "Arial", 'font-size': '14px', 'font-weight': 'bold'},
            color='danger',
            n_clicks=0)
    )

    if show_delete_button:
        buttons = [button_quit, button_delete]
    else:
        buttons = [button_quit]

    return buttons


def _get_columns_and_button_layout(all_data, chosen_dataset, show_delete_button, index, remove_geometry=True):
    # Get the options for the dropdowns.
    options = _get_column_options(all_data, chosen_dataset, remove_geometry)
    # Create the last part of the layout which show the save and delete button. Only show the quit button if show_delete_button is True.
    buttons = _button_layout(show_delete_button, index)

    return options, buttons


######################################################### General options loader #########################################################
def general_options_loader(hidden, part2_hidden, image_options=False):
    # The options needed to create a visualization layer. These options are the ones you have to choose
    # before you specific what kind of visualization you want. You need to choose a visualization type,
    # the and the dataset you want to create a visualization of.

    if image_options:
        loader = []

    else:

        vis_options = [{'label': 'scatter', 'value': 'scatter'},
                       {'label': 'barchart', 'value': 'barchart'},
                       {'label': 'grouped barchart', 'value': 'grouped_barchart'},
                       {'label': 'piechart', 'value': 'piechart'},
                       {'label': 'histogram', 'value': 'histogram'},
                       {'label': 'multi histogram', 'value': 'multi_histogram'}]

        question_1 = create_formgroup("Selecteer de visualisatie die je wilt bewerken of voeg een visualisatie toe:",
                                      dcc.Dropdown(id='general-add-or-edit-dropdown', options=[], multi=False))
        question_2 = create_formgroup("Kies de titel van de visualisatie:",
                                      dbc.Input(id='figure-title-input', type='text',
                                                placeholder='vul hier de titel in'))
        question_3 = create_formgroup("Selecteer dataset:",
                                      dcc.Dropdown(id='general-select-data-dropdown', options=[], multi=False))
        question_4 = create_formgroup("Selecteer type visualisatie:",
                                      dcc.Dropdown(id='general-select-vis-dropdown', options=vis_options, multi=False))

        loader = [
            # Div 1 This asks if you want to edit an existing layer, or add a new one
            html.Div(id='general-options-div-1', children=[
                html.H6("Opties"),
                question_1,
            ], style={}, hidden=hidden),

            # Div 2 This will ask which dataset and which visualization you would want to see
            html.Div(id='general-options-div-2', children=[
                question_2,
                question_3,
                question_4,

                # The div that gets filled with the options
                html.Div(id='visualization-options-div', children=[], hidden=True),
            ], style={}, hidden=part2_hidden),

            # The go back button is always visible at the bottom
            html.Br(),
            dbc.Button(
                'Ga terug',
                id={'type': 'button-go-back', 'index': 'general-options'},
                block=True,
                className='button',
                n_clicks=0,
                style={'background-color': 'rgba(108,117,125,255)'}),
        ]

    return loader

def general_map_options_loader(hidden, part2_hidden):
    # The options needed to create a visualization layer. These options are the ones you have to choose
    # before you specific what kind of visualization you want. You need to choose a visualization type,
    # the and the dataset you want to create a visualization of.
    vis_options = [{'label': 'Numerieke waardes per gebied', 'value': 'choroplethmapbox'},
                   {'label': 'Categorische waardes per gebied',
                    'value': 'categorical_choroplethmapbox'},
                   {'label': 'Numerieke waarde per bubbel per gebied', 'value': 'bubble_mapbox'}]

    question_1 = create_formgroup("Selecteer de visualisatie die je wilt bewerken of voeg een visualisatie toe:", dcc.Dropdown(id='general-add-or-edit-dropdown', options=[], multi=False))
    question_2 = create_formgroup("Kies titel van de visualisatie:", dbc.Input(type="text", id="figure-title-input", placeholder="vul hier de naam van het figuur in"))
    question_3 = create_formgroup("Selecteer dataset:", dcc.Dropdown(id='general-select-data-dropdown', options=[], multi=False))
    question_4 = dbc.FormGroup(
                [
                    dbc.Label(html.P(["Selecteer type ",
                                      html.Span("visualisatie ", id="visualisatie-tooltip",
                                                style={"textDecoration": "underline"}),
                                      ":"]), width=text_width),
                    dbc.Tooltip([dcc.Markdown(
                        "Je moet hier kiezen wat voor visualisatie je wilt tonen op de kaart. Er zijn de volgende opties:"),
                        dcc.Markdown(
                            "**Numerieke (bubbbel) waarde per gebied**: Voor deze visualisatie visualiseer je een \
                                of meerdere getallen op de kaart per gebied. Als je een bubbel visualisatie maakt dan \
                                komt er per gebied een bubbel waarvan de grote en kleur bepaald wordt door de gekozen data"),
                        dcc.Markdown(
                            "**Categorische waardes per gebied**: Voor deze visualisatie visualiseer je een enkele \
                                categorie per gebied op de kaart")],
                        target='visualisatie-tooltip',
                        placement='right',
                        style=tooltip_style),
                    dbc.Col(
                        dcc.Dropdown(id='general-select-vis-dropdown',
                                     options=vis_options,
                                     multi=False),
                        width=choice_width,
                    ),
                ],
                row=True,
            )


    loader = [
        # Div 1 This asks if you want to edit an existing layer, or add a new one
        html.Div(id='general-options-div-1', children=[
            html.H6("Opties"),
            question_1,
        ], style={}, hidden=hidden),

        # Div 2 This will ask which dataset and which visualization you would want to see
        html.Div(id='general-options-div-2', children=[
            question_2,
            question_3,
            question_4,
            # The div that gets filled with the options
            html.Div(id='visualization-options-div', children=[], hidden=True)
        ], style={}, hidden=part2_hidden),

        html.Br(),
        # The go back button that is always visible
        dbc.Button(
            'Ga terug',
            id={'type': 'button-go-back', 'index': 'general-options'},
            block=True,
            className='button',
            n_clicks=0,
            style={'background-color': 'rgba(108,117,125,255)'}),
    ]

    return loader

######################################################### Graph visualisation loaders #########################################################
def scatter_options_loader(hidden, all_data, chosen_dataset, layer_name="", x_data="", x_axis="", y_data="", y_axis="",
                           title_disabled=False, show_delete_button=False):
    options, buttons = _get_columns_and_button_layout(all_data, chosen_dataset, show_delete_button, 'scatter')
    question_1 = create_formgroup("Kies de naam die wordt getoond in de legenda:",
                                  dbc.Input(
                                      id={'type': 'layer-name', 'index': 'scatter'},
                                      type='text',
                                      placeholder='vul hier de naam in',
                                      value=layer_name,
                                      disabled=title_disabled
                                  ))

    question_2 = create_formgroup("Selecteer de x waarde van de scatter plot:",
                                  dcc.Dropdown(id={'type': 'x-data', 'index': 'scatter'}, options=options, multi=False,
                                               value=x_data))
    question_3 = create_formgroup("Kies de naam van de x-as:",
                                  dbc.Input(id={'type': 'x-axis', 'index': 'scatter'}, type='text',
                                            placeholder='naam x-as', value=x_axis))
    question_4 = create_formgroup("Selecteer de y waarde van de scatter plot:",
                                  dcc.Dropdown(id={'type': 'y-data', 'index': 'scatter'}, options=options, multi=False,
                                               value=y_data))
    question_5 = create_formgroup("Kies de naam van de y-as:",
                                  dbc.Input(id={'type': 'y-axis', 'index': 'scatter'}, type='text',
                                            placeholder='naam y-as', value=y_axis))

    loader = [
        html.Div([
            html.H6("Scatter opties"),
            question_1,
            question_2,
            question_3,
            html.Br(),
            question_4,
            question_5,
            dbc.Row(buttons)
        ], style={}, hidden=hidden)
    ]

    return loader


def barchart_options_loader(hidden, all_data, chosen_dataset, layer_name="", x_data="", x_axis="", y_data="", y_axis="",
                            title_disabled=False, show_delete_button=False):
    options, buttons = _get_columns_and_button_layout(all_data, chosen_dataset, show_delete_button, 'barchart')
    question_1 = create_formgroup("Kies de naam die wordt getoond in de legenda:",
                                  dbc.Input(
                                      id={'type': 'layer-name', 'index': 'barchart'},
                                      type='text',
                                      placeholder='vul hier de naam in',
                                      value=layer_name,
                                      disabled=title_disabled
                                  ))

    question_2 = create_formgroup("Selecteer de x waarde van de barchart plot:",
                                  dcc.Dropdown(id={'type': 'x-data', 'index': 'barchart'}, options=options, multi=False,
                                               value=x_data))
    question_3 = create_formgroup("Kies de naam van de x-as:",
                                  dbc.Input(id={'type': 'x-axis', 'index': 'barchart'}, type='text',
                                            placeholder='naam x-as', value=x_axis))
    question_4 = create_formgroup("Selecteer de y waarde van de barchart plot:",
                                  dcc.Dropdown(id={'type': 'y-data', 'index': 'barchart'}, options=options, multi=False,
                                               value=y_data))
    question_5 = create_formgroup("Kies de naam van de y-as:",
                                  dbc.Input(id={'type': 'y-axis', 'index': 'barchart'}, type='text',
                                            placeholder='naam y-as', value=y_axis))

    loader = [
        html.Div([
            html.H6("Barchart opties"),
            question_1,
            question_2,
            question_3,
            html.Br(),
            question_4,
            question_5,
            dbc.Row(buttons)
        ], style={}, hidden=hidden)

    ]

    return loader


def grouped_barchart_options_loader(hidden, all_data, chosen_dataset, layer_name="", x_data="", x_axis="", y_data="",
                                    y_axis="", mode="", title_disabled=False, show_delete_button=False):
    options, buttons = _get_columns_and_button_layout(all_data, chosen_dataset, show_delete_button, 'grouped-barchart')
    question_1 = create_formgroup("Kies de naam die wordt getoond in de legenda:",
                                  dbc.Input(
                                      id={'type': 'layer-name', 'index': 'grouped-barchart'},
                                      type='text',
                                      placeholder='vul hier de naam in',
                                      value=layer_name,
                                      disabled=title_disabled
                                  ))
    question_2 = create_formgroup("Selecteer de x waarde van de grouped-barchart plot:",
                                  dcc.Dropdown(id={'type': 'x-data', 'index': 'grouped-barchart'}, options=options,
                                               multi=False, value=x_data))
    question_3 = create_formgroup("Kies de naam van de x-as:",
                                  dbc.Input(id={'type': 'x-axis', 'index': 'grouped-barchart'}, type='text',
                                            placeholder='naam x-as', value=x_axis))
    question_4 = create_formgroup("Selecteer de y waarden van de grouped-barchart plot:",
                                  dcc.Dropdown(id={'type': 'y-data', 'index': 'grouped-barchart'}, options=options,
                                               multi=True, value=y_data))
    question_5 = create_formgroup("Kies de naam van de y-as:",
                                  dbc.Input(id={'type': 'y-axis', 'index': 'grouped-barchart'}, type='text',
                                            placeholder='naam y-as', value=y_axis))
    question_6 = create_formgroup("Selecteer hoe je de data wilt vergelijken:",
                                  dcc.Dropdown(id={'type': 'mode', 'index': 'grouped-barchart'},
                                               options=[{'label': 'groepen', 'value': 'group'},
                                                        {'label': 'stappels', 'value': 'stack'}], value=mode))

    loader = [
        html.Div([
            html.H6("Grouped barchart opties"),
            question_1,
            question_2,
            question_3,
            html.Br(),
            question_4,
            question_5,
            question_6,

            dbc.Row(buttons)
        ], style={}, hidden=hidden)

    ]
    return loader


def piechart_options_loader(hidden, all_data, chosen_dataset, layer_name="", x_data="", y_data="", title_disabled=False,
                            show_delete_button=False):
    options, buttons = _get_columns_and_button_layout(all_data, chosen_dataset, show_delete_button, 'piechart')
    question_1 = create_formgroup("Kies de naam die wordt getoond in de legenda:",
                                    dbc.Input(
                                        id={'type': 'layer-name', 'index': 'piechart'},
                                        type='text',
                                        placeholder='vul hier de naam in',
                                        value=layer_name,
                                        disabled=title_disabled
                                        ))
    question_2 = create_formgroup("Selecteer de categorieën van de piechart:", dcc.Dropdown(id={'type': 'x-data', 'index': 'piechart'}, options=options, multi=False, value=x_data))
    question_3 = create_formgroup("Selecteer de bijbehorende waardes van de piechart plot:", dcc.Dropdown(id={'type': 'y-data', 'index': 'piechart'}, options=options, multi=False, value=y_data))

    loader = [
        html.Div([
            html.H6("Piechart opties"),
            question_1,
            question_2,
            question_3,
            dbc.Row(buttons)
        ], style={}, hidden=hidden)
    ]

    return loader


def histogram_options_loader(hidden, all_data, chosen_dataset, layer_name="", x_data="", x_axis="",
                             title_disabled=False, show_delete_button=False):
    options, buttons = _get_columns_and_button_layout(all_data, chosen_dataset, show_delete_button, 'histogram')
    question_1 = create_formgroup("Kies de naam die wordt getoond in de legenda:",
                                  dbc.Input(
                                      id={'type': 'layer-name', 'index': 'histogram'},
                                      type='text',
                                      placeholder='vul hier de naam in',
                                      value=layer_name,
                                      disabled=title_disabled
                                  ))
    question_2 = create_formgroup("Selecteer de kolom die je wilt visualiseren:",
                                  dcc.Dropdown(id={'type': 'x-data', 'index': 'histogram'}, options=options,
                                               multi=False, value=x_data))
    question_3 = create_formgroup("Kies de naam van de x-as:",
                                  dbc.Input(id={'type': 'x-axis', 'index': 'histogram'}, type='text',
                                            placeholder='naam x-as', value=x_axis))
    loader = [
        html.Div([
            html.H6("Histogram opties"),
            question_1,
            question_2,
            question_3,
            dbc.Row(buttons)
        ], style={}, hidden=hidden),
    ]

    return loader


def multi_histogram_options_loader(hidden, all_data, chosen_dataset, layer_name="", x_data="", mode="",
                                   title_disabled=False, show_delete_button=False):
    options, buttons = _get_columns_and_button_layout(all_data, chosen_dataset, show_delete_button, 'multi-histogram')
    question_1 = create_formgroup("Kies de naam die wordt getoond in de legenda:",
                                  dbc.Input(
                                      id={'type': 'layer-name', 'index': 'multi-histogram'},
                                      type='text',
                                      placeholder='vul hier de naam in',
                                      value=layer_name,
                                      disabled=title_disabled
                                  ))
    question_2 = create_formgroup("Selecteer de kolommen die je wilt visualiseren:",
                                  dcc.Dropdown(id={'type': 'x-data', 'index': 'multi-histogram'}, options=options,
                                               multi=True, value=x_data))
    question_3 = create_formgroup("Selecteer hoe je de data wilt vergelijken:",
                                  dcc.Dropdown(id={'type': 'mode', 'index': 'multi-histogram'},
                                               options=[{'label': 'over elkaar', 'value': 'overlay'},
                                                        {'label': 'stappels', 'value': 'stack'}], value=mode))
    loader = [
        html.Div([
            html.H6("Multi-histogram opties"),
            question_1,
            question_2,
            question_3,
            dbc.Row(buttons)
        ], style={}, hidden=hidden),
    ]
    return loader


######################################################### Map visualisation loaders #########################################################
def choroplethmapbox_options_loader(hidden, all_data, chosen_dataset, vis_type='numerical', layer_name="", map_level="",
                                    map_data="", map_labels="", aggregate_method="", colormap='viridis',
                                    title_disabled=False, show_delete_button=False):
    options, buttons = _get_columns_and_button_layout(all_data, chosen_dataset, show_delete_button, 'choroplethmapbox')

    # This layout function can be used for categorical and numerical options. They have the exact same options
    # but they do have a different description. Categorical choroplethmapbox also don't need the option to aggregate
    if vis_type == 'numerical':
        header = "Numerieke waardes per gebied opties"
        # create the layout to ask what to do with aggregated data (take the mean, max, min, etc.)
        aggregate_options = _get_aggregate_visualization_options('choroplethmapbox', aggregate_method)
        color_map_options = create_formgroup("Selecteer de kleur overgang van de visualisatie:",
                                             dcc.Dropdown(id={'type': 'colormap', 'index': 'choroplethmapbox'},
                                                          options=colormaps_options, value=colormap))
    elif vis_type == 'categorical':
        header = 'Categorische waardes per gebied opties'
        aggregate_options = None
        color_map_options = None
    else:
        header = ''
        aggregate_options = None
        color_map_options = None

    level_options = _get_level_options('choroplethmapbox', map_level)

    question_1 = create_formgroup("Kies naam die wordt getoond in de legenda:",
                                  dbc.Input(id={'type': 'layer-name', 'index': 'choroplethmapbox'},
                                            type='text',
                                            placeholder='vul hier de naam van de visualisatie in',
                                            value=layer_name,
                                            disabled=title_disabled
                                            ))
    question_2 = create_formgroup("Selecteer de kolom met de regio code (GM/WK/BU)",
                                  dcc.Dropdown(id={'type': 'map-labels', 'index': 'choroplethmapbox'}, options=options,
                                               value=map_labels))
    question_3 = create_formgroup("Selecteer de kolom die gevisualiseerd wordt op de kaart:",
                                  dcc.Dropdown(id={'type': 'map-data', 'index': 'choroplethmapbox'}, options=options,
                                               value=map_data))

    loader = [
        html.Div([
            html.H6(header),
            question_1,
            level_options,
            question_2,
            question_3,
            aggregate_options,
            color_map_options,
        ], style={}, hidden=hidden),

        dbc.Row(buttons)
    ]

    return loader

def _process_choroplethmapbox(figure_wrapper, gdf, layer):
    # In this function we make the neccesary steps to process the dashboard data to create a chropletmapbox layer
    labels = layer['map_labels']
    regio_name = layer['map_labels'][:-5] + "_NAAM"
    if regio_name in gdf:
        text = regio_name
        groupby_values = [labels, text]
        hover_template = "%{text}<br>%{customdata}: %{z}"
    else:
        text = None
        groupby_values = labels
        hover_template = "%{location}<br>%{customdata}: %{z}"

    grouped_df = _group_values(
        gdf, groupby_values, layer['aggregate_method'], layer['map_data'])

    if layer['aggregate_method'] == 'frequency':
        color_name = 'Aantal'
    else:
        color_name = layer['map_data']

    figure_wrapper.add_level_choroplethmapbox_layer(
        data=grouped_df[layer['map_data']],
        data_key=grouped_df[labels],
        name=layer['layer_name'],
        show_legend=True,
        color_name=color_name,
        color_scale=layer['colormap'],
        hover_template=hover_template,
        text=grouped_df[text] if text is not None else None,
        custom_data=[layer['map_data']] * len(grouped_df)
    )

    return figure_wrapper

def _process_categorical_choroplethmapbox(figure_wrapper, gdf, layer):
    # In this function we make the neccesary steps to process the dashboard data to create a categorical
    # chropletmapbox layer
    figure_wrapper.add_categorical_level_choroplethmapbox(
        gdf=gdf,
        key_column=layer['map_labels'],
        categorie_column=layer['map_data'],
        legend_group=layer['layer_name'],
        show_legend=True,
    )

    return figure_wrapper

def bubble_choroplethmapbox_options_loader(hidden, all_data, chosen_dataset, layer_name="", map_level="", map_data="",
                                           map_labels="", aggregate_method="",
                                           colormap='viridis',
                                           title_disabled=False, show_delete_button=False):
    options, buttons = _get_columns_and_button_layout(all_data, chosen_dataset, show_delete_button,
                                                      'bubble-choroplethmapbox')

    # create the layout to ask what to do with aggregated data (take the mean, max, min, etc.)
    aggregate_options = _get_aggregate_visualization_options('bubble-choroplethmapbox', aggregate_method)

    level_options = _get_level_options('bubble-choroplethmapbox', map_level)
    question_1 = create_formgroup("Kies naam die wordt getoond in de legenda:",
                                  dbc.Input(id={'type': 'layer-name', 'index': 'bubble-choroplethmapbox'},
                                            type='text',
                                            placeholder='vul hier de naam van de visualisatie in',
                                            value=layer_name,
                                            disabled=title_disabled
                                            ))
    question_2 = create_formgroup("Selecteer de kolom met de regio code (GM/WK/BU)",
                                  dcc.Dropdown(id={'type': 'map-labels', 'index': 'bubble-choroplethmapbox'},
                                               options=options, value=map_labels))
    question_3 = create_formgroup(
        "Selecteer de kolom die gevisualiseerd wordt op de kaart (dit bepaald de grote en de kleur van de bubbel):",
        dcc.Dropdown(id={'type': 'map-data', 'index': 'bubble-choroplethmapbox'}, options=options, value=map_data))
    color_map_options = create_formgroup("Selecteer de kleur overgang van de visualisatie:",
                                         dcc.Dropdown(id={'type': 'colormap', 'index': 'bubble-choroplethmapbox'},
                                                      options=colormaps_options, value=colormap))
    loader = [
        html.Div([
            html.H6("Numerieke waarde per bubbel per gebied opties"),
            question_1,
            level_options,
            question_2,
            question_3,
            aggregate_options,
            color_map_options,

        ], style={}, hidden=hidden),

        dbc.Row(buttons)
    ]

    return loader

def _process_bubble_mapbox(figure_wrapper, gdf, layer):
    # In this function we make the neccesary steps to process the dashboard data to create a bubble mapbox layer
    labels = layer['map_labels']
    regio_name = layer['map_labels'][:-5] + "_NAAM"
    if regio_name in gdf:
        text = regio_name
        groupby_values = [labels, text]
        hover_template = "%{text}<br>%{customdata}: %{marker.color}"
    else:
        text = None
        groupby_values = labels
        hover_template = "%{location}<br>%{customdata}: %{marker.color}"

    grouped_df = _group_values(
        gdf, groupby_values, layer['aggregate_method'], layer['map_data']).sort_values(by=layer['map_data'],
                                                                                       ascending=False)

    if layer['aggregate_method'] == 'frequency':
        color_name = 'Aantal'
    else:
        color_name = layer['map_data']

    figure_wrapper.add_bubble_layer(
        data_key=grouped_df[layer['map_labels']],
        color=grouped_df[layer['map_data']] if layer['map_data'] is not "" else None,
        size=grouped_df[layer['map_data']] if layer['map_data'] is not "" else None,
        show_legend=True,
        name=layer['layer_name'],
        hover_template=hover_template,
        show_scale=True,
        color_name=layer['map_data'],
        text=grouped_df[text] if text is not None else None,
        color_scale=layer['colormap'],
        custom_data=[layer['map_data']] * len(grouped_df)
    )

    return figure_wrapper

######################################################### Save visualisation layers #########################################################
@app.callback(
    # Output
    [Output('layer-data', 'data'),
     Output('save-layer-warnings-error-store', 'data')],

    # The buttons that trigger the callback
    [Input({'type': 'button-quit', 'index': ALL}, 'n_clicks'),
     Input({'type': 'button-delete', 'index': ALL}, 'n_clicks'),

     # The layer data to import and then add the new layers
     State('layer-data', 'data'),

     # The basic settings
     State('selection-vis-to-change-dropdown', 'value'),
     State('general-select-vis-dropdown', 'value'),
     State('general-select-data-dropdown', 'value'),
     State('figure-title-input', 'value'),

     # The specific settings for figure visualizations
     State({'type': 'layer-name', 'index': ALL}, 'value'),
     State({'type': 'x-data', 'index': ALL}, 'value'),
     State({'type': 'x-axis', 'index': ALL}, 'value'),
     State({'type': 'y-data', 'index': ALL}, 'value'),
     State({'type': 'y-axis', 'index': ALL}, 'value'),
     State({'type': 'mode', 'index': ALL}, 'value')],

    # The specific settings for map visualizations
    State({'type': 'map-level', 'index': ALL}, 'value'),
    State({'type': 'map-data', 'index': ALL}, 'value'),
    State({'type': 'map-labels', 'index': ALL}, 'value'),
    State({'type': 'aggregate-method', 'index': ALL}, 'value'),
    State({'type': 'colormap', 'index': ALL}, 'value'),

    # get value of general add or edit layer menu
    State('general-add-or-edit-dropdown', 'value'),

    # Prevent initial callbacks so that it doesn't trigger as soon as the two buttons start existing
    prevent_initial_call=True)
def save_layer(n_clicks_quit, n_clicks_delete,
               layer_data,
               selected_fig, selected_vis, selected_data, figure_name,
               layer_name, x_data, x_axis, y_data, y_axis, mode,
               map_level, map_data, map_labels, aggregate_method, colormap,
               add_or_edit):
    """
    This functions saves all the data of a layer when the save button is clicked. It will save all data even if some
    don't exist for that visualisation. For example it will save a mode for a scatter, while scatter has no mode
    option. It's important to note that this function uses pattern matching callbacks (
    https://dash.plotly.com/pattern-matching-callbacks). This means our inputs are lists instead of single values,
    this is why sometimes extra indexing is used.
    """
    raise_data = {'warning': [],
                  'error': []}

    ctx = callback_context
    trigger = get_callback_trigger(ctx)

    # Because of dynamic callbacks our options are given in a list. When we add the first layer
    # the list is only 1 element long. So we just need to select the first element (index 0). When
    # we add a layer to another figure it get's added to the back of the list. So then we need to use index 1
    # So when we have excatly 1 option, we use index 0 and if we have more options we use index -1
    if len(layer_name) == 1:
        index = 0
    else:
        index = -1

    # For both buttons we first need to know if they exist (if they don't exist they will be an empty list) secondly
    # we need to know if they have been clicked atleast once
    if n_clicks_quit:  # if n clicks is empty
        save_clicked = n_clicks_quit[index] > 0
    else:
        save_clicked = False

    if n_clicks_delete:  # if n clicks is empty
        delete_clicked = n_clicks_delete[index] > 0
    else:
        delete_clicked = False

    # If the save button is clicked, save all the information of the layer
    if 'button-quit' in trigger and save_clicked:
        # if its the first layer create a new dictionary
        if layer_data is None:
            layer_data = {}

        # If the specific figure has no layers yet add an empty dictionary to store the layers
        if selected_fig not in layer_data:
            layer_data[selected_fig] = {}

        if layer_name[index] != "":
            layer_name_string = layer_name[index]
        else:
            layer_name_string = "Laag zonder naam"
            raise_data['warning'].append(f'{error_names[selected_fig]}: De zojuist toegevoegde laag heeft geen naam gekregen. Deze visualisatie '
                                         f'krijgt de naam ({layer_name_string})')

        if selected_fig in ['extra_vis_1', 'extra_vis_2']:
            if selected_vis in ['scatter', 'barchart', 'grouped_barchart', 'histogram', 'grouped_histogram']:
                if x_data[index] == '':
                    raise_data['error'].append(f'{error_names[selected_fig]}: Er is geen kolom opgegeven voor de x data.')
                if x_axis[index] == '':
                    raise_data['warning'].append(f'{error_names[selected_fig]}: Er is geen titel gegeven voor de x-as')
                if selected_vis not in ['histogram', 'grouped_histogram']:
                    if y_data[index] == '':
                        raise_data['error'].append(f'{error_names[selected_fig]}: Er is geen kolom opgegeven voor de y data.')
                    if y_axis[index] == '':
                        raise_data['warning'].append(f'{error_names[selected_fig]}: Er is geen titel gegeven voor de y-as')
            if selected_vis == 'piechart':
                if x_data[index] == '':
                    raise_data['error'].append(f'{error_names[selected_fig]}: Er is geen kolom opgegeven voor de labels.')
                if y_data[index] == '':
                    raise_data['error'].append(f'{error_names[selected_fig]}: Er is geen kolom opgegeven voor de bijbehorende waardes.')

        else:
            if map_labels[index] is None:
                raise_data['error'].append(f'{error_names[selected_fig]}: Er is geen regio code (GM/WK/BU) meegegeven.')

        if selected_fig in list(layer_data.keys()):
            if layer_name_string in list(layer_data[selected_fig].keys()) and add_or_edit != layer_name_string:
                raise_data['error'].append(f'{error_names[selected_fig]}: Laag naam ({layer_name_string}) bestaat al voor dit figuur. Kies een '
                                           f'andere naam voor deze visualisatie.')

        # Some options might not exist. So we check if we can use indexing. If we cant, we return None
        layer = {'figure_name': figure_name,
                 'layer_name': layer_name_string,
                 'visualisation_type': selected_vis,
                 'selected_dataset': selected_data,
                 'x_data': x_data[index] if x_data != [] else None,
                 'x_axis': x_axis[index] if x_axis != [] else None,
                 'y_data': y_data[index] if y_data != [] else None,
                 'y_axis': y_axis[index] if y_axis != [] else None,
                 'mode': mode[index] if mode != [] else None,
                 'map_level': map_level[index] if map_level != [] else None,
                 'map_data': map_data[index] if map_data != [] else None,
                 'map_labels': map_labels[index] if map_labels != [] else None,
                 'aggregate_method': aggregate_method[index] if aggregate_method != [] else None,
                 'colormap': colormap[index] if colormap != [] else None,
                 }
        # Save the information. First select the correct figure and then name of the layer.
        layer_data[selected_fig][layer_name_string] = layer
        print("Save_layer", raise_data)

        if len(raise_data['error']) > 0:
            return no_update, raise_data

        # Return the layer_data to the data store and set the dropdown on None
        return layer_data, raise_data

    # If the delete button is clicked delete the key and its information from the layer data
    elif 'button-delete' in trigger and delete_clicked:
        layer_data[selected_fig].pop(layer_name[index])

        return layer_data, raise_data

    else:
        return no_update

######################################################### Update figures & Map #########################################################
@app.callback([Output('extra-vis-1-figure', 'figure'),
               Output('extra-vis-2-figure', 'figure'),
               Output('update-graph-warnings-error-store', 'data')],

              [Input('layer-data', 'data'),
               Input('real-time-data', 'data'),
               State('data', 'data'),
               ], prevent_initial_call=False)
def update_figures(layer_data, rt_data, all_data):
    """
    This function updates all the non-map figures. It does this by loping over all the figures and checking all the
    layer data. It will then transform this layer data in actual visualizations and return it for the correct figures.
    """
    ctx = callback_context
    trigger = get_callback_trigger(ctx)
    if trigger == 'No trigger' and layer_data is None:
        return no_update

    all_data = combine_data_dicts(all_data, rt_data)

    raise_data = {'error': [],
                  'warning': []}
    figure_names = ['extra_vis_1', 'extra_vis_2']
    figure_outputs = []
    # First check if there are any layers to visualize
    if layer_data is None:
        return no_update

    # Loop over all the figures (we update all the figures in this callback)
    for figure_name in figure_names:
        # check if the figure has any layers
        if figure_name not in layer_data:
            figure_outputs.append(no_update)
            continue

        figure_wrapper = plolty_figure_wrapper(
            id=figure_name, title='')

        # if the figure has layers, then we loop over the layers to add them to the visualization
        for key, value in layer_data[figure_name].items():
            # Load dataset
            dataset_name = value['selected_dataset']
            gdf = load_gdf_from_json(all_data[dataset_name]['data'])

            if value['visualisation_type'] is None:
                return no_update

            elif value['visualisation_type'] == 'scatter':
                x_data = gdf[value['x_data']]
                y_data = gdf[value['y_data']]
                try:
                    x_data = x_data.astype(float)
                except ValueError:
                    # If casting to float raises an value error, then we let x_data be a string (most likely)
                    pass
                x_data_sort = np.argsort(x_data.values)

                x_data = x_data.iloc[x_data_sort]
                try:
                    y_data = y_data.astype(float)
                except ValueError:
                    # If casting to float raises an value error, then we let y_data be a string (most likely)
                    pass

                y_data = y_data.iloc[x_data_sort]

                figure_wrapper.create_scatter(
                    x=x_data,
                    y=y_data,
                    name=value['layer_name']
                )

            elif value['visualisation_type'] == 'barchart':
                x = gdf[value['x_data']]
                x_sort = np.argsort(x.values)
                x = x.iloc[x_sort]
                if len(x) != len(np.unique(x)):
                    raise_data['warning'].append(f'{error_names[figure_name]}: Let op: Er zijn x waardes die meerdere y waardes hebben. De '
                                                 'barchart wordt opgedeeld door de y waardes op elkaar te leggen. Dit'
                                                 ' kan verwarring veroorzaken bij de interpretatie.')
                try:
                    y = gdf[value['y_data']].astype(float)
                    y = y.iloc[x_sort]
                    figure_wrapper.create_barchart(
                        x=x,
                        y=y,
                        name=value['layer_name'])
                except ValueError:
                    typelist = get_unique_types(gdf[value['y_data']].tolist())
                    raise_data['error'].append(type_error_numeric(error_names[figure_name], 'y', 'barchart', value['layer_name'],
                                                                  value['y_data'], typelist))

            elif value['visualisation_type'] == 'grouped_barchart':
                # Grouped barchart expects the data in a certain format. So first we fit it in that format. The
                # format is {y_data_name : {'x_data' : [1, 2, 3], 'y_data' : [1, 2, 3]}}
                try:
                    data = {}
                    for y_naam in value['y_data']:
                        x = gdf[value['x_data']]
                        x_sort = np.argsort(x)
                        data[y_naam] = {
                            'x': x.iloc[x_sort], 'y': gdf[y_naam].iloc[x_sort].astype(float)}
                    figure_wrapper.create_grouped_barchart(
                        data_dict=data,
                        mode=value['mode']
                    )
                except ValueError:
                    typelist = get_unique_types(gdf[value['y_data']].tolist())
                    raise_data['error'].append(
                        type_error_numeric(error_names[figure_name], 'y', 'gegroepeerde barchart', value['layer_name'],
                                           value['y_data'], typelist))

            elif value['visualisation_type'] == 'piechart':
                try:
                    x = gdf[value['x_data']]
                    y = gdf[value['y_data']].astype(float)
                    y_sort = np.argsort(y)

                    figure_wrapper.create_pie_chart(
                        labels=x.iloc[y_sort],
                        values=y.iloc[y_sort])
                except ValueError:
                    typelist = get_unique_types(gdf[value['y_data']].tolist())
                    raise_data['error'].append(type_error_numeric(error_names[figure_name], 'waarde', 'piechart', value['layer_name'],
                                                                  value['y_data'], typelist))

            elif value['visualisation_type'] == 'histogram':
                try:
                    x = gdf[value['x_data']].astype(float)
                except ValueError:
                    x = gdf[value['x_data']]
                figure_wrapper.create_histogram(
                    x=x.sort_values(),
                    name=value['layer_name'])

            elif value['visualisation_type'] == 'multi_histogram':
                # Multi histogram expects the data in a certain format. So first we fit it in that format
                data = {}
                for x_naam in value['x_data']:
                    try:
                        x = gdf[x_naam].astype(float)
                    except ValueError:
                        x = gdf[x_naam]
                    data[x_naam] = {'x': x.sort_values()}
                figure_wrapper.create_multi_histogram(
                    data_dict=data,
                    mode=value['mode'])

            # Last we update the figures title and axes. The title and axes of the last layer will be used for now.

            figure_wrapper.figure.update_xaxes(
                title_text=value['x_axis'])
            figure_wrapper.figure.update_yaxes(
                title_text=value['y_axis'])
            figure_wrapper.figure.update_layout(
                title=value['figure_name']
            )

            # If the figure is a histogram or multi_histogram change the y axis to frequentie
            if value['visualisation_type'] == 'multi_histogram' or value['visualisation_type'] == 'histogram':
                figure_wrapper.figure.update_yaxes(title_text="frequentie")

        figure_wrapper.figure.update_layout(
            margin=dict(l=20, r=20, t=30, b=20))

        figure_outputs.append(figure_wrapper.figure)
    print("Update figuur:", raise_data)

    if len(raise_data['error']) > 0:
        return no_update, no_update, raise_data

    if trigger == 'real-time-data':
        print('Update interactie grafiek')

    return figure_outputs[0], figure_outputs[1], raise_data

def _add_map_layers(figure_wrapper, layer_data, all_data, raise_data):
    # This function adds all given map layers to a map_figure_wrapper

    # We loop over all the given layers and add them one by one to the visualization
    for key, value in layer_data['map_vis'].items():
        # Load dataset
        dataset_name = value['selected_dataset']
        datadict = json.loads(all_data[dataset_name]['data'])
        columns = all_data[dataset_name]['columns']
        gdf = gpd.GeoDataFrame.from_features(
            datadict['features']).loc[:, columns]

        # Drop unknown values in the gdf. We do this otherwise the axis are not representative of Tilburg
        gdf = gdf[gdf[value['map_labels']] != 'onbekend']

        # Get level and code signature of that level
        level = value['map_level']
        assert level == figure_wrapper.level, f'Regio van dataset {dataset_name} ({level}) komt niet overeen met de ' \
                                              f'regio van de kaart ({figure_wrapper.level})'
        code_start = {'Buurt': 'BU', 'Wijk': 'WK', 'Gemeente': 'GM'}[level]

        # Get column with region codes
        region_codes = gdf[value['map_labels']]
        code_column_error = f"{error_names['map_vis']}: De kolom {value['map_labels']} in {dataset_name} bevat geen (correcte) {level} codes"

        # If the types in this column are not strings, then this column does definitly not consists the region codes
        if "<class 'str'>" in list(region_codes.apply(lambda x: str(type(x))).unique()):
            # Raise an error if either all the codes do not start with the code signature or
            # all the codes are not 10 characters long
            if (region_codes.str[:2] != code_start).all() or ((region_codes.str.len() != 10).all() and
                                                              (region_codes.str.len() != 8).all() and
                                                              (region_codes.str.len() != 6).all()):
                raise_data['error'].append(code_column_error)
                continue
        else:
            raise_data['error'].append(code_column_error)
            continue

        if value['visualisation_type'] is None:
            continue

        # Return the correct visualization based on the layer options
        elif value['visualisation_type'] == 'choroplethmapbox':
            try:
                if value['aggregate_method'] != 'frequency':
                    gdf[value['map_data']] = gdf[value['map_data']].astype(float)
                figure_wrapper = _process_choroplethmapbox(figure_wrapper, gdf, value)
            except ValueError:
                # If the given data column is not castable to float, raise an error
                typelist = get_unique_types(gdf[value['map_data']].tolist())
                raise_data['error'].append(type_error_numeric(error_names['map_vis'], 'visualisatie', 'Numerieke kaart', value['layer_name'],
                                                              value['map_data'], typelist))

        elif value['visualisation_type'] == 'categorical_choroplethmapbox':
            if gdf[value['map_labels']].value_counts().iloc[0] > 1:
                raise_data['warning'].append(f'{error_names["map_vis"]}: Categorische kaart {value["layer_name"]} heeft per {value["map_labels"]}'
                                             f' meer dan 1 categorie. Het is niet mogelijk om per gebied meerdere '
                                             f'categorieën te visualiseren. Daarom is de categorie in de kaart de '
                                             f'meest voorkomende categorie.')
            try:
                figure_wrapper = _process_categorical_choroplethmapbox(figure_wrapper, gdf, value)
            except AssertionError as e:
                n_categories = str(e).split('categories ')[1].split(' than colors ')[0]

                raise_data['error'].append(f'{error_names["map_vis"]}: De categorische kaart kan maximaal {len(basic_colors)} categorieën '
                                           f'visualiseren. Deze visualisatie heeft {n_categories} '
                                           f'unieke categorieën.')

        elif value['visualisation_type'] == 'bubble_mapbox':
            figure_wrapper = _process_bubble_mapbox(figure_wrapper, gdf, value)

    if len(raise_data['error']) > 0:
        return figure_wrapper, raise_data

    return figure_wrapper, raise_data

@app.callback([Output('map-vis', 'figure'),
               Output('map-warning-message', 'children'),
               Output('map-warning-message', 'is_open'),
               Output('update-map-warnings-error-store', 'data')],
              [Input('layer-data', 'data'),
               Input('real-time-data', 'data'),
               State('data', 'data'),
               State('shape-data', 'data')])  # , prevent_initial_call=False)
def update_map(layer_data, rt_data, all_data, shape_data):
    """
    This function updates the map figure. It does this whenever another layer is added to layer-data.
    """
    ctx = callback_context
    trigger = get_callback_trigger(ctx)
    all_data = combine_data_dicts(all_data, rt_data)

    # First check if there are any layers to visualize. If there are None, we create a fake dictionary. This makes it
    # possible to still Show the background even when there is no data yet.
    raise_data = {'error': [],
                  'warning': []}

    if layer_data is None:
        layer_data = {'map_vis': {}}
    elif 'map_vis' not in layer_data.keys():
        layer_data['map_vis'] = {}

    # Check if there are any layers for the map
    if 'map_vis' in layer_data.keys():
        map_layers = layer_data['map_vis']
    else:
        map_layers = {}

    # Before we loop over the layers we need to find the level. For this we simply take the level of the first added
    # layer
    if len(list(map_layers)) == 0:
        chosen_level = 'Buurt'
    else:
        chosen_level = map_layers[list(map_layers.keys())[0]]['map_level']

    if shape_data is None:
        shape_data = {}
    # If no level is chosen yet force it to Buurt so there is always a visualization.
    if chosen_level not in ['Buurt', 'Wijk', 'Gemeente']:
        chosen_level = 'Buurt'

    # Check what the chosen level is and find the correct shape data in the shape store. If it doesn't exist yet we
    # load it in.
    if chosen_level in shape_data:
        tilburg_shapes = load_gdf_from_json(shape_data[chosen_level])
    else:
        tilburg_shapes = load_location_data(level=chosen_level, gemeente='Tilburg',
                                            path_to_datasets="datasets/shape_data")

    # Create a map figure wrapper and a the background of gemeente Tilburg
    figure_wrapper = plolty_gemeente_map_wrapper(
        title='', gdf_gemeente=tilburg_shapes, level=chosen_level)
    figure_wrapper.add_gemeente_background(opacity=0.35)
    figure_wrapper.add_ringbaan_and_spoor()

    if trigger == 'No trigger' and map_layers == {}:
        figure_wrapper.figure.update_layout(mapbox=dict(
            style="open-street-map", zoom=11.5, center={"lat": 51.57, "lon": 5.07}
        ),
            legend_orientation='v',
            legend={'x': 0, 'y': 0},
            margin=dict(l=0, r=2, t=0, b=0)
        )
        return figure_wrapper.figure, no_update, False, no_update

    try:
        figure_wrapper, raise_data = _add_map_layers(figure_wrapper, layer_data, all_data, raise_data)
    except AssertionError as e:
        raise_data['error'].append(error_names["map_vis"] + str(e))

    # The title of the map figure is defined by the first layer added. But only add if there is atleast one layer
    if len(layer_data['map_vis'].items()) > 0:
        first_layer = list(layer_data['map_vis'].keys())[0]
        figure_wrapper.figure.update_layout(title={'text': layer_data['map_vis'][first_layer]['figure_name'],
                                                   'x': 0.5,
                                                   'y': 0.99,
                                                   'xanchor': 'center',
                                                   'font': {'size': 28}})

    figure_wrapper.figure.update_layout(mapbox=dict(
        style="open-street-map", zoom=11.5, center={"lat": 51.57, "lon": 5.07}
    ),
        legend_orientation='v',
        legend={'x': 0, 'y': 0},
        margin=dict(l=0, r=2, t=0, b=0)
    )

    if len(raise_data['error']) > 0:
        return no_update, no_update, False, raise_data

    print('update interactie figure')
    return [figure_wrapper.figure, no_update, False, raise_data]

######################################################### Update options #########################################################
@app.callback(
    # Output extra vis 1
    [Output('extra-vis-1-options', 'children'),
     Output('extra-vis-1-options', 'hidden'),
     Output('extra-vis-1-figure-div', 'hidden'),

     # Output extra vis 2
     Output('extra-vis-2-options', 'children'),
     Output('extra-vis-2-options', 'hidden'),
     Output('extra-vis-2-figure-div', 'hidden'),

     # Output map visualizations
     Output('map-vis-options', 'children'),
     Output('map-vis-options', 'hidden'),
     Output('map-vis-figure-div', 'hidden'),

     # vReset choose visualization dropdown
     Output('selection-vis-to-change-dropdown', 'value')

     ],

    # Inputs for when to trigger changes
    [Input('selection-vis-to-change-dropdown', 'value'),
     Input({'type': 'button-delete', 'index': ALL}, 'n_clicks'),
     Input({'type': 'button-quit', 'index': ALL}, 'n_clicks'),
     Input({'type': 'button-go-back', 'index': ALL}, 'n_clicks')]
)
def add_all_divs_to_chosen_figure(chosen_figure, button_delete_clicks, button_quit_clicks, button_back_clicks):
    """
    This callbacks looks at what figure you want to change and then replaces the figure with the option menu. It does
    this by replace an empty div with the options menu and then switching the hidden values of this div and the figure.
    """
    # Indexing to select the correct button (index 0 for the first and after that always the last in the list)
    if len(button_quit_clicks) == 1:
        index = 0
    else:
        index = -1

    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    # Start block
    if trigger == 'selection-vis-to-change-dropdown':
        # Here we check what figure was chosen. We then replace the correct figure with block_1.
        # The outputs you see here to make the correct components vissible and hidden
        if chosen_figure == 'extra_vis_1':
            block_1 = general_options_loader(False, True)
            return [block_1, False, True, no_update, True, False, no_update, True, False, chosen_figure]

        elif chosen_figure == 'extra_vis_2':
            block_1 = general_options_loader(False, True)
            return [no_update, True, False, block_1, False, True, no_update, True, False, chosen_figure]

        elif chosen_figure == 'map_vis':
            block_1 = general_map_options_loader(False, True)
            return [no_update, True, False, no_update, True, False, block_1, False, True, chosen_figure]

        else:
            return no_update

    # we check for the correct trigger and if it buttons allready exist. If they don't exist they are None.
    # We also index on the button_clicks because with dynamic indexing it returns a list instead of a single value

    elif 'button-quit' in trigger and button_quit_clicks[index] > 0:
        if chosen_figure == 'extra_vis_1':
            return [no_update, True, False, no_update, no_update, no_update, no_update, no_update, no_update, ""]
        elif chosen_figure == 'extra_vis_2':
            return [no_update, no_update, no_update, no_update, True, False, no_update, no_update, no_update, ""]
        elif chosen_figure == 'map_vis':
            return [no_update, no_update, no_update, no_update, no_update, no_update, no_update, True, False, ""]

    # This needs to be a seperate elif because if the button doesn't exist (when creating a new layer we can't index
    # on it)
    elif 'button-delete' in trigger and button_delete_clicks[index] > 0:
        if chosen_figure == 'extra_vis_1':
            return [no_update, True, False, no_update, no_update, no_update, no_update, no_update, no_update, ""]
        elif chosen_figure == 'extra_vis_2':
            return [no_update, no_update, no_update, no_update, True, False, no_update, no_update, no_update, ""]
        elif chosen_figure == 'map_vis':
            return [no_update, no_update, no_update, no_update, no_update, no_update, no_update, True, False, ""]

    elif 'button-go-back' in trigger and button_back_clicks[index] > 0:
        if chosen_figure == 'extra_vis_1':
            return [no_update, True, False, no_update, no_update, no_update, no_update, no_update, no_update, ""]
        elif chosen_figure == 'extra_vis_2':
            return [no_update, no_update, no_update, no_update, True, False, no_update, no_update, no_update, ""]
        elif chosen_figure == 'map_vis':
            return [no_update, no_update, no_update, no_update, no_update, no_update, no_update, True, False, ""]

    # if else then not an intendent trigger
    else:
        return no_update


@app.callback(
    [Output('general-add-or-edit-dropdown', 'options')],

    [Input('layer-data', 'data'),
     Input('selection-vis-to-change-dropdown', 'value')]
)
def add_general_options(layer_data, vis_id):
    """
    This callback fills the first dropdown of the options menu. It asks if you want to edit a layer, or change an
    existing layer. If no layers exist, it will only offer to add another layer.
    """
    # if layer_data is a dict, find the existing layers
    if isinstance(layer_data, dict):
        # Check if the key exists
        if vis_id in layer_data:
            unique_layers = layer_data[vis_id].keys()
        else:
            unique_layers = []
    else:
        unique_layers = []

    add_edit_dropdown_options = [
        {'label': 'Visualisatie toevoegen', 'value': 'visualisatie toevoegen'}]
    add_edit_dropdown_options.extend(
        [{'label': x, 'value': x} for x in unique_layers])

    return [add_edit_dropdown_options]


@app.callback(
    # Unhide the div and give correct options
    Output('general-options-div-2', 'hidden'),
    Output('figure-title-input', 'value'),
    Output('general-select-data-dropdown', 'options'),

    # if you want to edit an old layer also fill in the data value in advance
    Output('general-select-data-dropdown', 'value'),
    Output('general-select-vis-dropdown', 'value'),

    [Input('general-add-or-edit-dropdown', 'value'),
     State('real-time-data', 'data'),
     State('selection-vis-to-change-dropdown', 'value'),
     State('data', 'data'),

     State('layer-data', 'data')]
)
def add_general_options_part_2(layer_selection, rt_data, chosen_figure, all_data, layer_data):
    """
    This callback is the second part of the general options. In the first part it was asked if you want to edit or
    change a layer. In this part it will show the next options based on that decision. If you want to add a layer you
    will first have to choose the visualization. and what dataset you want to choose. If you want to edit an existing
    layer it wil ... (Functionallity doesn't exist yet)
    """
    all_data = combine_data_dicts(all_data, rt_data)
    # Check if there is any input
    if layer_selection is None:
        return no_update

    elif layer_selection == 'visualisatie toevoegen':
        if isinstance(all_data, dict):
            all_datasets = all_data.keys()
        else:
            all_datasets = []

        options = [{'label': c, 'value': c} for c in all_datasets]

        return [False, "", options, "", ""]

    else:
        if isinstance(all_data, dict):
            all_datasets = all_data.keys()
        else:
            all_datasets = []

        options = [{'label': c, 'value': c} for c in all_datasets]

        figure_name = layer_data[chosen_figure][layer_selection]['figure_name']
        selected_dataset = layer_data[chosen_figure][layer_selection]['selected_dataset']
        selected_visualisation_type = layer_data[chosen_figure][layer_selection]['visualisation_type']

        return [False, figure_name, options, selected_dataset, selected_visualisation_type]


@app.callback(
    [Output('visualization-options-div', 'hidden'),
     Output('visualization-options-div', 'children')],
    [Input('general-select-vis-dropdown', 'value'),
     Input('general-select-data-dropdown', 'value'),
     State('real-time-data', 'data'),
     State('data', 'data'),
     State('layer-data', 'data'),
     State('general-add-or-edit-dropdown', 'value'),
     State('selection-vis-to-change-dropdown', 'value')]
)
def add_vis_specific_options(selected_vis, selected_data, rt_data, all_data, layer_data, selected_layer, chosen_figure):
    """
    This callback shows the last part of the options. These are options specific to the chosen visualization.
    So based on what visualization the use chose it will show different layouts.
    """
    all_data = combine_data_dicts(all_data, rt_data)

    # Check if a layer is being edit
    if selected_layer != 'visualisatie toevoegen':
        # Options for figure visualizations
        layer_name = layer_data[chosen_figure][selected_layer]['layer_name']
        x_data = layer_data[chosen_figure][selected_layer]['x_data']
        x_axis = layer_data[chosen_figure][selected_layer]['x_axis']
        y_data = layer_data[chosen_figure][selected_layer]['y_data']
        y_axis = layer_data[chosen_figure][selected_layer]['y_axis']
        mode = layer_data[chosen_figure][selected_layer]['mode']

        # Options for map visualizations
        map_level = layer_data[chosen_figure][selected_layer]['map_level']
        map_data = layer_data[chosen_figure][selected_layer]['map_data']
        map_labels = layer_data[chosen_figure][selected_layer]['map_labels']
        aggregate_method = layer_data[chosen_figure][selected_layer]['aggregate_method']
        colormap = layer_data[chosen_figure][selected_layer]['colormap']

        # Options to force edit mode
        title_disabled = True
        show_delete_button = True
    else:
        layer_name, x_data, x_axis, y_data, y_axis, mode = "", "", "", "", "", ""
        map_level, map_data, map_labels, aggregate_method, colormap = "", "", "", "", 'viridis'
        title_disabled = False
        show_delete_button = False

    if selected_data == "":
        loader = [dbc.Alert("Er is nog geen data ingeladen", color="warning")]
    elif selected_vis == "":
        loader = [
            dbc.Alert("Er is nog geen data visualisatie gekozen", color="warning")]

    else:
        if selected_vis == 'scatter':
            loader = scatter_options_loader(
                False, all_data, selected_data, layer_name, x_data, x_axis, y_data, y_axis, title_disabled,
                show_delete_button)
        elif selected_vis == 'barchart':
            loader = barchart_options_loader(
                False, all_data, selected_data, layer_name, x_data, x_axis, y_data, y_axis, title_disabled,
                show_delete_button)
        elif selected_vis == 'grouped_barchart':
            loader = grouped_barchart_options_loader(
                False, all_data, selected_data, layer_name, x_data, x_axis, y_data, y_axis, mode, title_disabled,
                show_delete_button)
        elif selected_vis == 'piechart':
            loader = piechart_options_loader(
                False, all_data, selected_data, layer_name, x_data, y_data, title_disabled, show_delete_button)
        elif selected_vis == 'histogram':
            loader = histogram_options_loader(
                False, all_data, selected_data,
                layer_name, x_data, x_axis, title_disabled,
                show_delete_button
            )
        elif selected_vis == 'multi_histogram':
            loader = multi_histogram_options_loader(
                False, all_data, selected_data, layer_name, x_data, mode, title_disabled, show_delete_button)

        # Map options
        elif selected_vis == 'choroplethmapbox':
            loader = choroplethmapbox_options_loader(
                False, all_data, selected_data, 'numerical', layer_name, map_level, map_data, map_labels,
                aggregate_method, colormap, title_disabled, show_delete_button
            )
        elif selected_vis == 'categorical_choroplethmapbox':
            # Categorical uses the exact same inputs except the type. The inputs only have to be used in a different way
            loader = choroplethmapbox_options_loader(
                False, all_data, selected_data, 'categorical', layer_name, map_level, map_data, map_labels,
                aggregate_method, colormap, title_disabled, show_delete_button)
        elif selected_vis == 'bubble_mapbox':
            loader = bubble_choroplethmapbox_options_loader(
                False, all_data, selected_data, layer_name, map_level, map_data, map_labels,
                aggregate_method, colormap, title_disabled, show_delete_button)
        else:
            loader = no_update

    return False, loader


############################################ Error and warnings handeling #############################################
@app.callback([Output('warning-error-popup', 'children'),
               Output('warning-error-popup', 'is_open'),
               Output('open-warnings-error-popup', 'children')],
              [Input('save-layer-warnings-error-store', 'data'),
               Input('update-graph-warnings-error-store', 'data'),
               Input('update-map-warnings-error-store', 'data'),
               Input('sluit-warnings-error-popup', 'n_clicks'),
               Input('open-warnings-error-popup', 'n_clicks')],
              State('warning-error-popup', 'children'),
              prevent_initial_callbacks=True)
def raise_and_fill_popup(save_layer_error, update_graph_error, update_map_error,
                         close_button_clicks, open_button_clicks, old_popup_content):
    """
    Callback that handles the raise dictionaries

    save_layer_error, param update_graph_error, update_map_error <dict>
        Dictionary with two keys: error and warning. Each key has a list with all the acumulated errors or warning
        messages
    close_button_clicks <int>
        number of times that the close button is clicks. This button closes the warning pup if someone clicks on it
    old_popup_content <list>
        List with old content. This is only used for keeping the close button
    """
    ctx = callback_context
    trigger = get_callback_trigger(ctx)

    if trigger == 'No trigger':
        return no_update

    # combine all errors and warnings
    errors = {'error': save_layer_error['error'] + update_graph_error['error'] + update_map_error['error'],
              'warning': save_layer_error['warning'] + update_graph_error['warning'] + update_map_error['warning']}
    open_button_text = f"Bekijk foutmeldingen en waarschuwingen ({len(errors['error']) + len(errors['warning'])})"

    # if close button is clicked, then close the popup
    if close_button_clicks > 0 and trigger == 'sluit-warnings-error-popup':
        return no_update, False, open_button_text
    # if there are none, do not raise de popup
    if len(errors['warning']) == 0 and len(errors['error']) == 0:
        if open_button_clicks > 0 and trigger == 'open-warnings-error-popup':
            errors['error'].append('Geen foutmeldingen')
            pop_modal = True
        else:
            return no_update, False, open_button_text
    elif len(errors['warning']) > 0 and len(errors['error']) == 0:
        # Do not trigger modal if the open button was not clicked and there only warnings
        pop_modal = open_button_clicks > 0 and trigger == 'open-warnings-error-popup'
    else:
        pop_modal = True

    popup_content = []
    for raise_type, alert_type in zip(['error', 'warning'], ['danger', 'warning']):
        if len(errors[raise_type]) > 0:
            # header of popup
            popup_content.append(dbc.ModalHeader({'error': 'Foutmelding', 'warning': 'Waarschuwing'}[raise_type],
                                                 className=f'alert-{alert_type}',
                                                 style={'border': '1px solid black',
                                                        'border-bottom': '0px',
                                                        'margin': '3px',
                                                        'margin-bottom': '0px'}))
            # append all messages to the popup
            for ii, msg in enumerate(errors[raise_type]):
                # remove bottom border and margin if there are multiple warnings or errors so the messages are all
                # nicely joined
                border_bottom = '1px solid black' if ii == len(errors[raise_type]) - 1 else '0px'
                margin_bottom = '3px' if ii == len(errors[raise_type]) - 1 else '0px'
                popup_content.append(dbc.ModalBody(msg, className=f'alert-{alert_type}',
                                                   style={'border': '1px solid black',
                                                          'border-top': '0px',
                                                          'border-bottom': border_bottom,
                                                          'margin': '3px',
                                                          'margin-top': '0px',
                                                          'margin-bottom': margin_bottom}))

    popup_content.append(old_popup_content[-1])
    return popup_content, pop_modal, open_button_text


def get_unique_types(data_list):
    typedict = {
        "<class 'int'>": 'getal',
        "<class 'float'>": 'getal',
        "<class 'str'>": 'tekst/categorisch',
    }
    typelist = []
    for elem in data_list:
        # Get string representation of type
        string_type = str(type(elem))
        try:
            # typedict is like a translation for technical to non-technical types, but sometimes a different type is
            # given, which wil yield a KeyError
            typestr = typedict[string_type]
        except KeyError:
            # If the string representation is in the same format, we can strip down the representation to get a
            # technical type
            # If that is not the case, then we say the type is unknown in order to prevent confusion with the user
            if 'class' in string_type:
                typestr = string_type.strip('class').strip('<').strip('>').strip("'")
            else:
                typestr = 'onbekend'

        # We want an unique set of types, do not add them if they're already in the list
        if typestr in typelist:
            continue
        typelist.append(typestr)
    return typelist
