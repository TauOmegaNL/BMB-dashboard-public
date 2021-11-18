import geopandas as gpd
import json

import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

from core.app_multipage import app

# Import own functions
from core.data_utils import load_location_data, \
    load_gdf_from_json, combine_data_dicts
from core.visualisatie_utils import plolty_gemeente_map_wrapper

graph_style = {
    'height': '39vh'
}

card_style_head = {
    'font-size': '18px'
}
card_style_top = {
    'font-size': '18px',
    'font-weight': 'bold'
}

# Layout of the map page
layout = dbc.Col([dcc.Graph(id='kaart', figure={"layout": {"title": '',
                                                           "display": 'inline-block',
                                                           "horizontalAlign": 'middle'}}, style={'height': '100vh'}, config = {"editable" : True})],
                 width=12, className='Map_SingleMapPage', style={
        'margin-left': '0%',
        'margin-right': '0%',
        'margin-top': '0%',
        'margin-bottom': '0%',
        'height': '100vh',
        'overflow': 'hidden'
    })


def _group_values(gdf, groupby_value, group_method, group_to=None):
    """This functions groups a given geo dataframe with a certain method and then return the dataframe"""

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


# map callback
@app.callback(
    [Output(component_id='kaart', component_property='figure')],
    [Input(component_id='url', component_property='pathname'),
     Input('real-time-data', 'data'),
     State('layer-data', 'data'),
     State('data', 'data'),
     State('shape-data', 'data')]
)
def update_graph(url, rt_data, layer_data, all_data, shape_data):
    # First check if there are any layers to visualize. If there are None, we create a fake dictionary. This makes it
    # possible to still Show the background even when there is no data yet.
    if isinstance(layer_data, dict):
        if 'map_vis' not in layer_data.keys():
            layer_data['map_vis'] = {}
    else:
        layer_data = {'map_vis': {}}

    all_data = combine_data_dicts(all_data, rt_data)

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
    figure_wrapper = plolty_gemeente_map_wrapper(title='', gdf_gemeente=tilburg_shapes, level=chosen_level)
    figure_wrapper.add_gemeente_background(opacity=0.35)
    figure_wrapper.add_ringbaan_and_spoor()

    # if the figure has layers, then we loop over the layers to add them to the visualization
    for key, value in layer_data['map_vis'].items():
        # Load dataset
        dataset_name = value['selected_dataset']
        datadict = json.loads(all_data[dataset_name]['data'])
        columns = all_data[dataset_name]['columns']
        gdf = gpd.GeoDataFrame.from_features(
            datadict['features']).loc[:, columns]

        # Drop unknown values in the gdf. We do this otherwise the axis are not representative of Tilburg
        gdf = gdf[gdf[value['map_labels']] != 'onbekend']

        if value['visualisation_type'] is None:
            continue

        # Return the correct visualization based on the layer options
        elif value['visualisation_type'] == 'choroplethmapbox':
            labels = value['map_labels']
            regio_name = value['map_labels'][:-5] + "_NAAM"
            if regio_name in gdf:
                text = regio_name
                groupby_values = [labels, text]
                hover_template = "%{text}<br>%{customdata}: %{z}"
            else:
                text = None
                groupby_values = labels
                hover_template = "%{location}<br>%{customdata}: %{z}"

            grouped_df = _group_values(
                gdf, groupby_values, value['aggregate_method'], value['map_data'])

            if value['aggregate_method'] == 'frequency':
                color_name = 'Aantal'
            else:
                color_name = value['map_data']

            figure_wrapper.add_level_choroplethmapbox_layer(
                data=grouped_df[value['map_data']],
                data_key=grouped_df[labels],
                name=value['layer_name'],
                show_legend=True,
                color_name=color_name,
                color_scale=value['colormap'],
                hover_template=hover_template,
                text=grouped_df[text] if text is not None else None,
                custom_data=[value['map_data']] * len(grouped_df)
            )

        elif value['visualisation_type'] == 'categorical_choroplethmapbox':
            figure_wrapper.add_categorical_level_choroplethmapbox(
                gdf=gdf,
                key_column=value['map_labels'],
                categorie_column=value['map_data'],
                legend_group=value['layer_name'],
                show_legend=True,
            )

        elif value['visualisation_type'] == 'bubble_mapbox':
            # In this function we make the neccesary steps to process the dashboard data to create a bubble mapbox layer
            labels = value['map_labels']
            # With the hover template you can define what text to show on the hover. The variables have to be
            # variables that are defined in a go.Scattermapbox
            regio_name = value['map_labels'][:-5] + "_NAAM"
            if regio_name in gdf:
                text = regio_name
                groupby_values = [labels, text]
                hover_template = "%{text}<br>%{customdata}: %{marker.color}"
            else:
                text = None
                groupby_values = labels
                hover_template = "%{location}<br>%{customdata}: %{marker.color}"

            grouped_df = _group_values(
                gdf, groupby_values, value['aggregate_method'], value['map_data'])

            if value['aggregate_method'] == 'frequency':
                color_name = 'Aantal'
            else:
                color_name = value['map_data']

            figure_wrapper.add_bubble_layer(
                data_key=grouped_df[value['map_labels']],
                color=grouped_df[value['map_data']] if value['map_data'] is not "" else None,
                size=grouped_df[value['map_data']] if value['map_data'] is not "" else None,
                show_legend=True,
                name=value['layer_name'],
                hover_template=hover_template,
                show_scale=True,
                color_name=color_name,
                text=grouped_df[text] if text is not None else None,
                color_scale=value['colormap'],
                custom_data=[value['map_data']] * len(grouped_df)
            )

    figure_wrapper.figure.update_layout(mapbox_style="open-street-map",
                                        mapbox_zoom=11.5, mapbox_center={"lat": 51.57, "lon": 5.07},
                                        legend_orientation='v',
                                        legend={'x': 0, 'y': 0},
                                        margin=dict(l=0, r=2, t=0, b=0),
                                        )

    # The title of the map figure is defined by the last layer added. But only add if there is atleast one layer
    if len(layer_data['map_vis'].items()) > 0:
        first_layer = list(layer_data['map_vis'].keys())[0]
        figure_wrapper.figure.update_layout(title={'text': layer_data['map_vis'][first_layer]['figure_name'],
                                                   'x': 0.5,
                                                   'y': 0.99,
                                                   'xanchor': 'center',
                                                   'font': {'size': 28}})
    return [figure_wrapper.figure]
