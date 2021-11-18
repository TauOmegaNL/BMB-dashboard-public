import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import os

from core.data_utils import _get_code, _find_middle_point

import json

basic_colors = px.colors.qualitative.Alphabet
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))


class plolty_figure_wrapper(object):
    """
    This class initalises an empty graph object and gives you the option to fill it with one or more visualizations.
    The class itself can contain important and simple information such as the title of a figure, a unique id etc.
    Most of the important information like data has to be given when creating a figure.

    Input:
    id <str>
        A unique id for the figure

    title <str>
        The title the figure will have

    Example:
    ------
    >>> df = px.data.iris
    >>> scatter_figure = plolty_figure_wrapper(id = "scatter_fig_1", title = "Scatter plot")
    >>> scatter_fig.create_scatter(x = df['sepal_length'], y = df['sepal_width'], name = "sepal_width")
    >>> scatter_fig.create_scatter(x = df['sepal_length'], y = df['petal_length'], name = 'petal_length')
    >>> scatter_fig.show()
    """

    def __init__(self,
                 id: str,
                 title: str):
        self.id = id
        self.figure = go.Figure()
        self.title = title
        self.layout = {"title": {"text": self.title}}

    def clear_figure(self):
        self.figure = go.Figure()

    def show(self):
        self.figure.update_layout(self.layout)
        self.figure.show()

    def create_scatter(self, x, y, mode='markers', name=None):
        """
        This functions creates a go.scatter visualization and adds it to the figure class. It will be added as a layer
        of the figure.

        Input:
        x, y <list/array/panda series>
            A list, array or series that contain the x and y values that need to be plotted. x and y should always
            have the same length.

        mode <str>
            The scatter mode that you want to use for the visualization. This defines if you only visualize dots,
            dots and lines or just lines. The possible values are: 'markers', 'lines+markers' or 'lines'. Default: 'markers'

        name <str>
            The name of this specific visualization that is added to the figure. This is different from the title.
            If multipile visualizations are added than this name will be the one shown in the legenda. Default: None
        """
        data = go.Scatter(x=x, y=y, mode=mode, name=name)
        self.figure.add_trace(data)

    def create_barchart(self, x, y, name=None):
        """
        This functions creates a go.barchart visualization and adds it to the figure class. It will be added as a layer
        of the figure.

        Input:
        x, y <list/array/panda series>
            A list, array or series that contain the x and y values that need to be plotted. x and y should always
            have the same length.

        name <str>
            The name of this specific visualization that is added to the figure. This is different from the title.
            If multipile visualizations are added than this name will be the one shown in the legenda. Default: None
        """
        data = go.Bar(x=x, y=y, name=name)
        self.figure.add_trace(data)

    def create_grouped_barchart(self, data_dict, mode='group'):
        """
        This functions will add multipile go.barchart visualizations to the figure class in a grouped manner. This
        means it can show multipile bars with the same x value on the same axis. This can either be grouped or
        stacked (defined by the mode). Grouped means the bars we be plotted next to each other on the same x
        value and stacked means they will be stacked on top of each other for the x value. This visualization will then
        be added to the figure as a layer.

        Input:
        data_dict <dict>
            The data_dict is a dictonairy that contains all the neccesary information to create multipile barchart.
            The format of this dictionary should be:
            {'name of visualization 1' : {x : [a,b,c], y : [3, 4, 5]},
             'name of visualization 2' : {x : [a,b,c], y : [1, 2, 3]}}
            It will only group bars with the same x variable.

        mode <string>
            mode defines how the barcharts will be grouped. The options are 'group' and 'stack'. 'group' is used
            to compare multipile groups and 'stack' is used to add them together and compare them as a whole'.
            Default: 'group'
        """
        group_names = data_dict.keys()
        for group in group_names:
            group_dict = data_dict[group]
            self.figure.add_trace(
                go.Bar(name=group, x=group_dict['x'], y=group_dict['y']))

        self.figure.update_layout(barmode=mode)

    def create_pie_chart(self, labels, values):
        """
        This functions creates a go.piechart visualization and adds it to the figure class. It pie
        will show the distrubution of the values over the labels.

        Input:
        lables <list/array/panda series>
            A list, array or series that contains the labels that are used in the pie chart.

        values <list/array/panda series>
            A list, array or series that contains the numbers matching the labels. The distrubution will be calculated
            based on the given values. This distribution should be given in numbers, but the numbers can be either
            strings, int or float.
        """
        data = go.Pie(labels=labels, values=values)
        self.figure.add_trace(data)

    def create_histogram(self, x, name=None):
        """
        This functions creates a go.histogram visualization and adds it to the figure class. It will be added as
        a layer of the figure.

        Input:
        x <list/array/panda series>
            A list, array or series that contain the x values. The histogram will count how often unique values occur
            and visualize this in the plot.

        name <str>
            The name of this specific visualization that is added to the figure. This is different from the title.
            If multipile visualizations are added than this name will be the one shown in the legenda. Default: None
        """
        data = go.Histogram(x=x, name=name)
        self.figure.add_trace(data)
        self.figure.update_yaxes(title_text='frequentie')

    def create_multi_histogram(self, data_dict, mode='overlay'):
        """
        This functions will add multipile go.Histograms visualizations to the figure class in a grouped manner. This
        means it can count values from multipile columns. You can choose to either plot this two histogram over each
        other or stack them up. This is defined by the 'mode'. This visualization will then be added to the figure
        as a layer.

        Input:
        data_dict <dict>
            The data_dict is a dictonairy that contains all the neccesary information to create multipile histograms.
            The format of this dictionary should be:
            {'name of visualization 1' : {x : [1,2,3]},
             'name of visualization 2' : {x : [1,1,2]}}

        mode <string>
            mode defines how the barcharts will be grouped. The options are 'overlay' and 'stack'. 'overlay' is used
            to compare multipile groups and 'stack' is used to add them together and visualize them as a whole'.
            Default: 'overlay'
        """
        groups = data_dict.keys()
        for group in groups:
            group_dict = data_dict[group]
            self.figure.add_trace(go.Histogram(x=group_dict['x'], name=group))

        self.figure.update_layout(barmode=mode)
        self.figure.update_traces(opacity=0.75)
        self.figure.update_yaxes(title_text='frequentie')


class plolty_gemeente_map_wrapper(object):
    """
    This class is made to create visualizations of a Gemeente in the Netherlands. The class will initialise
    an empty graph object. You can then fill this object with different map visualizations. When creating a map
    visualization you'll have to give the data corresponding to the original level. The level defines if you want to
    visualize a "buurt", "wijk" or "gemeente" level.

    Input:
    id <str>
        A unique id for the figure

    title <str>
        The title the figure will have

    level <str>
        The level at which you want to visualize. The options are: "Buurt", "Wijk" or "Gemeente"

    gdf_gemeente <geo.dataframe>
        a geo dataframe that contains the geometry of the chosen level.

    Example:
        ------
    >>> level = 'Wijk'
    >>> start = dt.datetime(2021, 5, 4, 11, 30)
    >>> end = dt.datetime(2021, 5, 4, 12, 30)
    >>> Tilburg_shapes = load_location_data(level=level, gemeente='Tilburg', path_to_datasets="..\core\datasets\shape_data")
    >>> gdf_MJS = aggregate_point_data(df, level = level, gemeente = 'Tilburg')
    >>> gdf_MJS_tilburg = gdf_MJS[gdf_MJS['BU_CODE'] != 'onbekend']

    >>> figuur = plolty_gemeente_map_wrapper(title = 'multipile layers', gdf_gemeente = Tilburg_shapes, level = level)
    >>> figuur.add_gemeente_background(show_legend = True)
    >>> figuur.add_level_choroplethmapbox_layer(data = gdf_MJS_tilburg['temperature'], data_key = gdf_MJS_tilburg['BU_CODE'], name = 'MJS', show_legend = True, legend_group = 'MJS', color_name = 'temperatuur', color_scale = 'Viridis')
    >>> figuur.show()
    """

    def __init__(self,
                 title: str,
                 level: str,
                 gdf_gemeente):
        self.title = title
        self.level = level
        self.gdf_gemeente = gdf_gemeente
        self.figure = go.Figure()
        self.scale_count = 0
        self.category_count = 0

        # Add WK/BU/GM code
        self.code = _get_code(self.level)

        # Create geojson for visualizations
        string_shapes_json = self.gdf_gemeente.to_json()
        self.json_gemeente = json.loads(string_shapes_json)

        # Add value to gdf for background visualizations
        self.gdf_gemeente['background'] = 0

    def show(self, mapbox_style="carto-positron", token=None):
        """
        This function shows the figure. This is mostly used in notebooks.
        """

        # Update the layout of the figure so it has the correct center and mapbox style
        self.figure.update_layout(mapbox=dict(accesstoken=token,
                                              zoom=8.5, center={"lat": 51.57, "lon": 5.07},
                                              style=mapbox_style),
                                  legend_orientation='h')
        self.figure.show()

    def clear_figure(self):
        """
        This function resets the figure attribute in the class. So it deletes all the data and traces inside it
        and create an empty go.Figure object.
        """
        self.figure = go.Figure()

    def check_length(self, obj1, obj2):
        if len(obj1) == len(obj2):
            return None
        else:
            raise ValueError(
                "Two inputs are not of the same length. This error arises because of: {} and {}".format(obj1, obj2))

    def add_gemeente_background(self, show_legend=False, opacity=0.2):
        """
        This function adds a trace to the figure that contains the shapes of the gemeente. This can either be shapes of buurten,
        wijken or the whole gemeente. This depends on the level that was given to the class. The function finds the shapes
        in the geo dataframe that was given when creating the class.

        input:
        show_legend <bool>
            show_legend is a boolean that determine if the background shapes should be shown in the legenda. by showing
            it in the legenda you have the option to easily turn them off and on. Default: False

        opacity <float>
            opacity has to be between 0 and 1. The opacity defines how see through the background shapes are. Default: 0.2
        """
        # This is the standard location for the BU/WK/GM code
        id_str_name = 'properties.' + self.code

        map_vis_background = go.Choroplethmapbox(geojson=self.json_gemeente, locations=self.gdf_gemeente[self.code],
                                                 z=self.gdf_gemeente.background,
                                                 featureidkey=id_str_name, marker_opacity=opacity, showscale=False,
                                                 hoverinfo='skip',
                                                 name='background shapes', legendgroup='background shapes',
                                                 showlegend=show_legend)

        icons = go.Scattermapbox(
            lat=[51.560403],
            lon=[5.083441],
            mode="markers+text",
            showlegend=False,
            text=['Station Tilburg'],
            textposition="top center",
            textfont=dict(size=25, color='black',
                          family='TilburgsAns'),
            hoverlabel=dict(font=dict(family='TilburgsAns', size=25)),
            marker=dict(size=5)
        )

        self.figure.add_trace(map_vis_background)
        # self.figure.add_trace(icons)

    def add_ringbaan_and_spoor(self, show_legend=True):
        """
        This function adds the ring roads and trainrails of Tilburg to the map
        """
        filename = os.path.join(THIS_FOLDER, 'datasets', 'Wegen_spoor_Tilburg.json')
        with open(filename, 'r') as f:
            roads = json.load(f)

        ringbaan_data = []
        spoor_data = []
        for key, values in roads.items():
            if values['Type'] == 'Ringbaan':
                for color, width in zip(['#444444', "#FCD6A4"], [4, 2]):
                    ringbaan_data.append(go.Scattermapbox(
                        lat=values['Latitude'],
                        lon=values['Longitude'],
                        mode="lines",
                        line=dict(width=width, color=color),
                        showlegend=(len(ringbaan_data) == 1) and show_legend,
                        legendgroup='ringbaan',
                        name='Ringbaan',
                        text=key))
            elif values['Type'] == 'Spoor':
                for color, width in zip(['#555555', '#777777'], [4, 2]):
                    spoor_data.append(go.Scattermapbox(
                        lat=np.array(values['Latitude']),
                        lon=values['Longitude'],
                        mode="lines",
                        line=dict(width=width, color=color),
                        showlegend=(len(spoor_data) == 1) and show_legend,
                        legendgroup='spoor',
                        name='Spoor',
                        text='Spoor'
                    ))
        map_data = ringbaan_data + spoor_data
        self.figure.add_traces(map_data)

    def create_standard_choroplethmapbox(self,
                                         data,
                                         data_key,
                                         opacity=0.5,
                                         show_legend=False,
                                         show_scale=True,
                                         show_background_shapes=False):
        """
        This functions creates a standard choroplethmapbox and adds it as a whole to the figure object. This is
        mostly used when you want the bare minimum with as little input as possible. So it's not possible to add
        multipile layers, or do anything fancy.

        Input:
        data <list/array/panda series>
            The data that you want to visualize on the choroplethmapbox. This data should contain either floats or integers.

        data_key <list/array/panda series>
            The corresponding keys to the data. This is a list/array/pandas with the same length as data. This key should contain
            either a BU_CODE, WK_CODE or GM_CODE to link the data to the given shapes files. To further explain, every data point
            has a corresponding CODE. This way the visualization knows which array corresponds to which value of the given data.

        opacity <float>
            opacity has to be between 0 and 1. The opacity defines how see through the shapes are. Default: 0.5

        show_legend <boolean>
            This boolean defines if you want to show the legend in the standard visualization. Default : False

        show_scale <boolean>
            This boolean defines if you want to show the color scale in the standard visualization. Default : True

        show_background_shapes <boolean>
            This boolean defines if the background shapes of the gemeente will be shown. If it's true it will add a
            layer with the shapes. Default: False

        """
        self.clear_figure()
        self.check_length(data, data_key)

        if show_background_shapes:
            self.add_gemeente_background()

        self.add_level_choroplethmapbox_layer(data=data, data_key=data_key, opacity=opacity,
                                              show_legend=show_legend, show_scale=show_scale)

    def add_level_choroplethmapbox_layer(self, data,
                                         data_key,
                                         opacity=0.5,
                                         show_legend=True,
                                         show_scale=True,
                                         legend_group=None,
                                         name=None,
                                         color_scale=None,
                                         reverse_scale=False,
                                         color_name=None,
                                         hover_template=None,
                                         text=None,
                                         custom_data=None):
        """
        This function creates a choropletmapbox layer that is linked to the gemeentes shapes files (defined by the
        given level). The layer wil then be added to the figure of this class, you can add multipile of these layers
        to one figure.

        Input:
        data <list/array/panda series>
            The data that you want to visualize on the choroplethmapbox. This data should contain either floats or integers.

        data_key <list/array/panda series>
            The corresponding keys to the data. This is a list/array/pandas with the same length as data. This key should contain
            either a BU_CODE, WK_CODE or GM_CODE to link the data to the given shapes files.To further explain, every data point
            has a corresponding CODE. This way the visualization knows which array corresponds to which value of the given data.

        opacity <float>
            opacity has to be between 0 and 1. The opacity defines how see through the shapes are. Default: 0.5

        show_legend <boolean>
            This boolean defines if you want to show this specific layer in the legend of the figure. Default : True

        show_scale <boolean>
            This boolean defines if you want to show the color scale of this specific layer in the figure. Default : True

        legend_group <str>
            This string defines in which legend group the layer should be. You can use this to combine multipile layers to one
            legend item. Default: None

        name <str>
            A string name for the visualization layer. This name will be linked with the given data and it's also the name
            that will be shown in the legenda. Default: None

       color_scale <str or list>
            The color_scale defines from  what color to what color the color scale should
            range. There are two ways to give the input of this variable. First you can give a standard string
            color_scale name, for example: 'viridis' or 'blues'. You can find the standard values here:
            https://plotly.com/python/builtin-colorscales/. The second option is to define your own scale. This can be
            done by giving a list that contains multipile list with information. The information is a float between 0 and
            1 and a corresponding string that contains the RGB information. The float defines at which point the color
            starts (0 and the bottom of the scale and 1 at the top).This should look something like this: [[0, 'rgb(50,
            205,50)'], [1, 'rgb(0,0,250)']]

        reverse_scale <boolean>
            If true the whole color scale will be reversed. Default: False

        color_name <str>
            The color_name is the string that is shown at the top of the color_scale. Default: None

        text <list/array/panda series>
            A list/array/panda series that says what text to show for each section of the choropleth
        """
        self.check_length(data, data_key)

        # This is where the data_key of the shapes files are stored
        id_str_name = 'properties.' + self.code

        map_vis = go.Choroplethmapbox(geojson=self.json_gemeente, locations=data_key, z=data,
                                      featureidkey=id_str_name, marker_opacity=opacity, showscale=show_scale,
                                      legendgroup=legend_group, showlegend=show_legend, hovertemplate=hover_template,
                                      colorbar=dict(title=color_name, x=1.02 + (0.2 * self.scale_count)), name=name,
                                      colorscale=color_scale, reversescale=reverse_scale, text=text,
                                      customdata=custom_data)

        self.figure.add_trace(map_vis)

        # We keep count of how many color scales are shown to adjust where we place them.
        if show_scale:
            self.scale_count += 1

    def add_categorical_level_choroplethmapbox(self,
                                               gdf,
                                               key_column,
                                               categorie_column,
                                               opacity=0.5,
                                               show_legend=True,
                                               legend_group=None,
                                               colors=None,
                                               text=None):
        """
        This function creates a choropletmapbox based on categorical values. The values will be linked to the corresponding key.

        Input:
        gdf <geo data frame>
            The geodataframe that contains the data that needs to be visalized

        key_columns <str>
            The string name of the column that contains the datakey (BU_CODE, WK_CODE, or GM_CODE)

        categorie_column <str>
            The string name of the column that contains the category
            
        opacity <float>
            opacity has to be between 0 and 1. The opacity defines how see through the shapes are. Default: 0.5

        show_legend <boolean>
            This boolean defines if you want to show this specific layer in the legend of the figure. Default : True

        legend_group <str>
            This string defines in which legend group the layer should be. You can use this to combine multipile layers to one
            legend item. In this case all the categorisch will be bound to the same legend, and an extra string will be added
            to the name to show they belong together.  Default: None

        colors <list>
            A list of colors that the function can use the get colors from. If no are given it will use the basic colors of the plotly library
        """
        grouped_gdf = gdf.groupby([key_column, categorie_column], as_index=False).count()
        grouped_gdf = grouped_gdf.groupby(key_column, as_index=False).max()

        # Add the name of the region as text
        name = key_column[:-5] + "_NAAM"
        # if the name column is allready in the grouped df we drop it (because it still contains the count)
        if name in grouped_gdf:
            grouped_gdf.drop(name, axis=1, inplace=True)
        merged_df = grouped_gdf.merge(self.gdf_gemeente, on=key_column)

        data = merged_df[categorie_column]
        data_key = merged_df[key_column]
        text = merged_df[name]

        self.check_length(data, data_key)

        # This is where the data_key of the shapes files are stored
        id_str_name = 'properties.' + self.code

        # Create name for grouped categories
        if legend_group is not None:
            legend_group_name = legend_group + ": "
        else:
            legend_group_name = ""

        # If no colors are given use basic colors
        if colors is None:
            colors = basic_colors

        # Create an array with all unique categories in the data
        unique_categories = np.unique(data)

        for category in unique_categories:
            assert self.category_count < len(colors), f"There are more categories {len(unique_categories)} than colors " \
                                                      f"{len(colors)}, so there are no more colors to choose from "

            name = legend_group_name + str(category)
            # create an index to filter the data. This way we have a sub_data dataset that only contains
            # data of category we are currently looping over.
            index = data == category
            sub_data = data[index]
            sub_text = text[index]
            sub_keys = data_key[index]

            # To be able to create a Choroplethmapbox we need float data, so we create an array of 0's per category
            # These 0's are then plotted with the correct color.
            fake_sub_data = np.zeros(len(sub_data))

            # Here a custom color scale is created. The scale only has 1 color. So in the end this will mean it visualize
            # this category with the color we are looping over.
            custom_scale = [[0, colors[self.category_count]],
                            [1, colors[self.category_count]]]

            # We create a customhover format so that it only show's the key and category and not the 0 needed for the choroplethmapbox
            custom_data = [category] * len(sub_data)
            hover_template = "%{text}<br>%{customdata}"

            map_vis = go.Choroplethmapbox(geojson=self.json_gemeente, locations=sub_keys, z=fake_sub_data,
                                          featureidkey=id_str_name, legendgroup=legend_group, showlegend=show_legend,
                                          name=name, hovertemplate=hover_template, text=sub_text,
                                          customdata=custom_data,
                                          colorscale=custom_scale, showscale=False, marker_opacity=opacity)

            self.figure.add_trace(map_vis)

            # Only count up category count when using basic colors
            if colors == basic_colors:
                self.category_count += 1

    def add_bubble_layer(self,
                         data_key,
                         size,
                         text=None,
                         custom_data=None,
                         name=None,
                         hover_template=None,
                         show_legend=True,
                         color='rgb(255, 0, 0)',
                         color_scale=None,
                         color_name=None,
                         show_scale=False,
                         reverse_scale=False,
                         max_size=20,
                         min_size=3):
        """
        This function appends a bubble layer to the figure. The bubbles are always in the middle of a buurt,
        wijk or gemeente to make sure no personal data is used. Because of one of the inputs is a data_key. The
        bubbles can vary in size and color.

        Input:
        data_key <list/array/panda series>
            The corresponding keys to the data. This is a list/array/pandas with the same length as data. This key should contain
            either a BU_CODE, WK_CODE or GM_CODE to link the data to the given shapes files. To further explain, every data point
            has a corresponding CODE. This way the visualization knows which array corresponds to which value of the given data.

        size <list/array/panda series>
            The data that you want to define the size of the bubbles. This data should contain either floats or integers.

        text <list/array/panda series>
            The text that should be shown when hovering of the bubbles. This is a unique text for each bubble. Default: None

        name <str>
            A string name for the visualization layer. This name will be linked with the given data and it's also the name
            that will be shown in the legenda. Default: None

        show_legend <boolean>
            This boolean defines if you want to show this specific layer in the legend of the figure. Default : True

        color <string or list/array/panda series>
            There are two ways you can use this color. First of all you can give a rgb value in the form of a string. For example:
            'rgb(255,0,0)'. If used this way then every bubble will have that color. The second way to use it is to give a
            list/array/panda series of values. The color of the bubbles will then correspond to the values in this input.

        color_scale <str or list>
            The color_scale defines from  what color to what color the color scale should
            range. There are two ways to give the input of this variable. First you can give a standard string
            color_scale name, for example: 'viridis' or 'blues'. You can find the standard values here:
            https://plotly.com/python/builtin-colorscales/. The second option is to define your own scale. This can be
            done by giving a list that contains multipile list with information. The information is a float between 0 and
            1 and a corresponding string that contains the RGB information. The float defines at which point the color
            starts (0 and the bottom of the scale and 1 at the top).This should look something like this: [[0, 'rgb(50,
            205,50)'], [1, 'rgb(0,0,250)']]

        color_name <str>
            The color_name is the string that is shown at the top of the color_scale. Default: None

        show_scale <boolean>
            This boolean defines if you want to show the color scale of this specific layer in the figure. Default : False

        reverse_scale <boolean>
            If true the whole color scale will be reversed. Default: False

        max_size <int>
            define the max size of the bubbles. All the bubbles will be scaled towards this max size. Default: 6
        """
        # self.check_length(size, data_key)

        # Data_key has to be a series
        data_key = pd.Series(data_key)

        # Convert the keys (BU/GM/WK) to lon/lat data of the middle points of those keys.
        middle_points = data_key.apply(
            lambda x: _find_middle_point(x, self.level, self.gdf_gemeente))
        lon_data = middle_points.apply(lambda x: x[0])
        lat_data = middle_points.apply(lambda x: x[1])

        # Scale size (recommended by: https://plotly.com/python/bubble-maps/)
        # sizeref = 2. * max(size) / (max_size ** 2)
        sizeref = max(size) / max_size

        bubble_vis = go.Scattermapbox(lon=lon_data, lat=lat_data,
                                      name=name, showlegend=show_legend,
                                      hovertemplate=hover_template, hoverinfo='text',
                                      text=text,  # hovertext=text,
                                      customdata=custom_data,
                                      marker=dict(size=size,
                                                  sizeref=sizeref,
                                                  sizemin=min_size,
                                                  color=color,
                                                  colorbar=dict(title=color_name, x=1.02 + (0.2 * self.scale_count)),
                                                  colorscale=color_scale,
                                                  showscale=show_scale,
                                                  reversescale=reverse_scale),
                                      opacity=1
                                      )

        bubble_vis_border = go.Scattermapbox(lon=lon_data, lat=lat_data, showlegend=False,
                                             marker=dict(size=size.apply(lambda x: min(x * 1.2, x + 2)),
                                                         sizeref=sizeref,
                                                         sizemin=min(min_size * 1.2, min_size + 2),
                                                         color='rgb(10, 10, 10)',
                                                         showscale=False),
                                             opacity=1,
                                             hoverinfo='skip'
                                             )
        self.figure.add_trace(bubble_vis_border)
        self.figure.add_trace(bubble_vis)

        if show_scale:
            self.scale_count += 1
