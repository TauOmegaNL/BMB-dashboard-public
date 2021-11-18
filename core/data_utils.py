import pandas as pd
import geopandas as gpd
import numpy as np
from netCDF4 import Dataset

import datetime as dt

from urllib.request import urlopen
from requests.exceptions import HTTPError
from dateutil import tz
import json
import io
import os

from collections import Counter

import warnings

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))


def load_meet_je_stad(start: dt.datetime, end: dt.datetime,
                      timezone=tz.gettz('W. Europe Standard Time'),
                      output_filename: str = None,
                      return_dates: bool = True):
    """
    Reads Meet Je Stad data from api within two dates.

    Input:

    start <dt.datetime>
        start date of which you want the data

    end <dt.datetime>
        end date of which you want the data

    timezone <dateutil.tz.win.tzwin>
        timezone file. Specify in what timezone the start and end dates are

    output_filename <str>
        specify filename if you want to save the data

    return_dates <bool>
        besides the data, set True if you want to return the dates

    Output:

    df <pd.DataFrame>
        Dataframe with meet je stad data

    Start <dt.datetime>
        start date of data (only if return_dates = True)

    End <dt.datetime>
        end date of data (only if return_dates = True)


    Examples:
    ---------
    >>> import datetime as dt
    >>> start = dt.datetime(2021, 5, 4, 11)
    >>> end = dt.datetime(2021, 5, 4, 11, 30)
    >>> df, s, e = load_meet_je_stad(start, end)
    >>> print(s)
    2021-05-04,11:00

    >>> print(e)
    2021-05-04,11:30

    >>> print(df.head())
       row   id                 timestamp  firmware_version  longitude  latitude
    0    0  173 2021-05-04 11:00:04+02:00               2.0    5.38953   52.1732
    1    1  781 2021-05-04 11:00:07+02:00               4.0    5.03516   52.1097
    2    2  789 2021-05-04 11:00:32+02:00               4.0    5.11557   52.0744
    3    3  299 2021-05-04 11:00:33+02:00               4.0    5.37738   52.1635
    4    4   44 2021-05-04 11:00:36+02:00               1.0    5.39499   52.1605

       temperature  humidity      lux  supply  battery  pm2.5  pm10 extra
    0       9.7500  107.8750  35541.0    3.42      NaN    NaN   NaN   NaN
    1       8.9375   97.6250      NaN    3.34      NaN    NaN   NaN   NaN
    2      10.6250   87.0000      NaN    3.32      NaN    NaN   NaN   NaN
    3       9.0625   98.7500      NaN    3.29      NaN    NaN   NaN   NaN
    4       9.5625    2.0625      NaN    3.30      NaN    NaN   NaN   NaN
    """

    start = start.astimezone(timezone)
    end = end.astimezone(timezone)

    assert start < end, 'Start timestamp must be earlier than end timestamp'

    start_str = start.astimezone(dt.timezone.utc).strftime("%Y-%m-%d,%H:%M")
    end_str = end.astimezone(dt.timezone.utc).strftime("%Y-%m-%d,%H:%M")

    with urlopen(f"https://meetjestad.net/data/?type=sensors&format=json&start={start_str}&end={end_str}") as url:
        data = json.loads(url.read().decode())
        assert len(data) > 0, f'No data found for start date ({start}) and end date ({end})'

    df = pd.json_normalize(data)
    df.timestamp = pd.to_datetime(df.timestamp, format='%Y-%m-%d %H:%M:%S', utc=True).dt.tz_convert('Europe/Amsterdam')
    df.timestamp = df.timestamp.apply(lambda x: x.tz_localize(None))
    df = df.set_index('row')

    geom = gpd.points_from_xy(df['longitude'], df['latitude'])
    gdf = gpd.GeoDataFrame(df, geometry=geom, crs=4326)

    if type(output_filename) == str:
        gdf.to_csv(output_filename, sep=';')
    elif output_filename is not None:
        warnings.warn('Output_filename is given, but was not a string. Convert filename to string if the dataframe '
                      'needs to be saved')

    if return_dates:
        return gdf, start, end

    return gdf


def load_location_data(level="Buurt", gemeente='Tilburg', path_to_datasets="datasets/shape_data"):
    """
    This function loads the shape data of a chosen Gemeente. In this github repo we have the shape file of the
    Netherlands, but if you wish to use your own that's possible

    Input:
    level <str>
        The level at which you want to load the gemeente data. The choices are "Buurt", "Wijk" and "Gemeente".
        The shape file is located in the datasets folder of this repo. Default: "Buurt"


    gemeente <str>
        The name of the gemeente you want a shape file from. You can also give the keyword 'All' if so than you make no
        subset Default: Tilburg

    path_to_datasets <str>
        The path where the shape datasets are safed. If you are working from the apps directory this is the defaul
        output. Default: "../datasets/shape_data"

    Output:
    df_gemeente <geopanda dataframe>
        a geopanda dataframe with all the data that was safed in the .shp file. The dataframe will be in EPSG:4326
        format


    Examples:
    ---------

    >>> level = 'Buurt'
    >>> gemeente = 'Tilburg'
    >>> Tilburg_geo_df = load_location_data(level = level, gemeente = gemeente, path_to_datasets = "../core/datasets/shape_data")
    >>> Tilburg_geo_df.head()
        BU_CODE      JRSTATCODE           BU_NAAM   WK_CODE     WK_NAAM  \
        8788  BU08551001  2020BU08551001   Binnenstad West  WK085510  Binnenstad
        8789  BU08551002  2020BU08551002   Binnenstad Oost  WK085510  Binnenstad
        8790  BU08551003  2020BU08551003      Koningsplein  WK085510  Binnenstad
        8791  BU08551004  2020BU08551004         Oude Dijk  WK085510  Binnenstad
        8792  BU08551101  2020BU08551101  Veemarktkwartier  WK085511   Hoogvenne

            GM_CODE  GM_NAAM  IND_WBI  H2O POSTCODE  ...  P_ANT_ARU  P_SURINAM  \
        8788  GM0855  Tilburg        1  NEE     5038  ...          2          2
        8789  GM0855  Tilburg        1  NEE     5038  ...          3          1
        8790  GM0855  Tilburg        1  NEE     5038  ...          2          1
        8791  GM0855  Tilburg        1  NEE     5038  ...          2          1
        8792  GM0855  Tilburg        1  NEE     5038  ...  -99999999  -99999999

            P_TURKIJE  P_OVER_NW  OPP_TOT  OPP_LAND  OPP_WATER   Shape_Leng  \
        8788          1          5       25        25          0  2117.250595
        8789          2          6       28        28          0  2155.213479
        8790          0          5        8         8          0  1190.557261
        8791          0          2       18        18          0  1841.562871
        8792  -99999999  -99999999       10        10          0  1451.616394

                Shape_Area                                           geometry
        8788  247784.814923  POLYGON ((5.08232 51.56028, 5.08290 51.56025, ...
        8789  283951.559094  POLYGON ((5.08920 51.55972, 5.09129 51.55956, ...
        8790   83014.280557  POLYGON ((5.09057 51.55501, 5.09057 51.55496, ...
        8791  180330.367156  POLYGON ((5.08145 51.55484, 5.08202 51.55473, ...
        8792  100710.950514  POLYGON ((5.09799 51.55989, 5.09796 51.55987, ...
    """
    if level == 'Buurt':
        shape_file = os.path.join(THIS_FOLDER, path_to_datasets, "buurt_2020_v1.shp")
    elif level == 'Wijk':
        shape_file = os.path.join(THIS_FOLDER, path_to_datasets, "wijk_2020_v1.shp")
    elif level == 'Gemeente':
        shape_file = os.path.join(THIS_FOLDER, path_to_datasets, "gemeente_2020_v1.shp")
    else:
        # If something wrong choses choose Buurt
        print("level has to be Buurt, Wijk or Gemeente. None of these were chosen so Buurt wil be loaded")
        shape_file = os.path.join(THIS_FOLDER, path_to_datasets, "buurt_2020_v1.shp")

    # Read shape file as geopanda dataframe
    df = gpd.read_file(shape_file)

    # Select the corresponding gemeente
    if gemeente != 'All':
        df = df[df['GM_NAAM'] == gemeente]

    # Make sure the shape files are in the correct CRS format
    df = df.to_crs("EPSG:4326")
    # Drop everything except the BU/WK/GM code and the shapes
    code = _get_code(level)
    name = code[:-5] + "_NAAM"
    df = df[[code, name, 'geometry']]

    return df


def _add_level_column(row, shapes, code):
    """
    Function for the apply of aggregate point data
    """
    punt = row['geometry']
    selectie = shapes['geometry'].contains(punt)
    name = code[:-5] + "_NAAM"
    code = shapes.loc[selectie, [code, name]]

    if len(code.values) == 0:
        return ['onbekend', 'onbekend']
    else:
        return [code.values[0][0], code.values[0][1]]


def aggregate_point_data(df, shapes, level='Buurt', gemeente="Tilburg", lat_name='latitude', lon_name='longitude'):
    """
    This function finds the corresponding 'Buurt' or 'Wijk' of point data (given with latitude/longitude).

    Input:
    df <dataframe or geopandasdataframe>
        The dataframe that contains the point data that you want to find the shape data for. This can either be a normal
        dataframe or a geopandasdataframe

    shapes <geopandasdataframe>
        A geopandas that contains the shapes of the Buurt, Gemeente or Wijk

    level <str>
        The level at which you want to find the shape data. The choices are "Buurt", "Wijk" and "Gemeente".
        Default: "Buurt"

    gemeente <str>
        The name of the gemeente that the location points are located in. You can also use the keyword 'All' to use all
        the gemeenten (this may slow down the function) Default: Tilburg

    lat_name, lon_name <str>
        The column name which contains the latitude and longitude of the points.

    Output:
    geo_df <geopanda dataframe>
        A geopanda dataframe which contains all the information of the input df but added a column with the code of the
        Buurt, Wijk or Gemeente

    Examples:
    ---------

    >>> start = dt.datetime(2021, 5, 4, 11, 30)
    >>> end = dt.datetime(2021, 5, 4, 12, 30)
    >>> df, s, e = load_meet_je_stad(start, end)
    >>> level = 'Buurt'
    >>> gemeente = 'Tilburg'
    >>> Tilburg_shapes = load_location_data(level=level, gemeente='Tilburg', path_to_datasets="..\core\datasets\shape_data")
    >>> gdf_MJS = aggregate_point_data(df, Tilburg_shapes, level = level, gemeente = 'Tilburg')
    >>> geo_df.head()
            row   id                 timestamp  firmware_version  longitude  latitude  \
        0    0  391 2021-05-04 11:30:06+02:00               2.0    5.30258   60.3470
        1    1  384 2021-05-04 11:30:14+02:00               4.0    5.34442   60.3904
        2    2  728 2021-05-04 11:30:15+02:00               4.0    5.12119   52.0981
        3    3  730 2021-05-04 11:30:20+02:00               4.0    6.00714   52.2374
        4    4  118 2021-05-04 11:30:23+02:00               3.0    5.38989   52.1564

        temperature  humidity  supply  lux  battery  pm2.5  pm10 extra  \
        0       9.6250   53.4375    3.37  NaN      NaN    NaN   NaN   NaN
        1      12.3750   45.0625    3.25  NaN      NaN    NaN   NaN   NaN
        2       9.6875   97.6875    3.38  NaN      NaN    NaN   NaN   NaN
        3       9.2500   63.6250    3.39  NaN      NaN    NaN   NaN   NaN
        4       9.3750   65.7500    3.45  NaN      NaN    NaN   NaN   NaN

                        geometry   BU_CODE
        0  POINT (5.30258 60.34700)  onbekend
        1  POINT (5.34442 60.39040)  onbekend
        2  POINT (5.12119 52.09810)  onbekend
        3  POINT (6.00714 52.23740)  onbekend
        4  POINT (5.38989 52.15640)  onbekend
    """
    code = _get_code(level)
    # If a normal dataframe is passed transform it to a geo dataframe
    if type(df) == pd.DataFrame:
        geo_df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_name], df[lat_name]))
    else:
        geo_df = df
    # First set all values of code to 'onbekend' (unknown) later we fill all the values that we can find with the
    # Corresponding code
    code_column = geo_df.apply(lambda x: _add_level_column(x, shapes, code), axis=1)
    name = code[:-5] + "_NAAM"
    temp_df = pd.DataFrame(code_column.to_list(), columns=[code, name])
    # df = pd.DataFrame(code_column, columns = [code, name])
    geo_df[code] = temp_df[code]
    geo_df[name] = temp_df[name]
    return geo_df


def read_file(filename: str, header: int = 1, latitude_col: str = 'latitude', longitude_col: str = 'longitude',
              geometry_col: str = 'geometry', codecol: str = 'BU_CODE', read_type: str = 'latlong', crs: int = 4326,
              sep: str = None, nrows: int = None, contents=None, make_geo=True, return_sep: bool = False,
              path_to_shapes=os.path.join('datasets', 'shape_data')):
    """
    General file reader. It can read xlsx files or textbased files csv and txt. For text based files, the reader guesses
    the separator, but it is a user argument as well. The table gets converted to a GeoPandas dataframe with standard
    coordinate reference system 4326 (GPS coordinates).

    Input:
    filename <str>
        Filename of the table that needs to be read.

    Optional:
    header <int>
        Row in file with column names. Starts counting from 1.
        Default: 1

    latitude_col, longitude_col <str>
        Column names of latitude and longitude columns. Only used if read_type == 'latlong'.
        Default: latitude, longitude

    geometry_col <str>
        Column name of geometry column. Alternative to latitude and longitude system.
        Only used if read_type == 'latlong'
        Default: geometry

    codecol <str>
        Column name for BUURTcode, WIJKcode or GEMEENTEcode in dataset. Standard columns are: 'BU_CODE', 'WK_CODE',
        'GM_CODE', but they can deviate.
        Default: BU_CODE

    read_type <str>
        Decides wheter to use latitude and longitude, BUURTcode, WIJKcode or GEMEENTEcode.
        Options:
            'latlong', --> Latitude and longitude
            'Buurt', --> Buurt code as defined in CBS (Central Bureau of Statistics (NL))
            'Wijk', --> Wijk code as defined in CBS
            'Gemeente', --> Gemeente code as defined in CBS
            'geometry' --> A geometry column is already given.
        Default: 'latlong'

    crs <int>
        Coordinate Reference System from EPSG. Standard is EPSG:4326. Read more here: https://epsg.io/4326
        Default: 4326

    sep <str>
        Column separator for textbased data. If None, then the function get_sep() will be used to guess the separator.
        Default: None

    nrows <int>
        Number of rows that need to be loaded.
        Default: None (all)

    contents <bytestr>
        The uploaded contents to the dashboard. This is optional, but will always be used in the dashboard. It is not
        necessary for prototyping.

    make_geo <bool>
        Wheter or not a geometry column should be added. If the dataset is loaded to read the settings, then a geocol
        should not be made.

    return_sep <bool>
        Wheter or not to return the seperator. If it is an excel load, the sep is None.

    path_to_shapes <str>
        Path to all the shape files that will be loaded with the load_location_data function.
        Default: core\datasets\shape_data

    Output: gdf <GeoDataFrame>
        Geopandas dataframe with data from file. Converted to geo with crs given in arguments.
        If read_type == 'latlong', a new column is added called 'geometry' with latitude and longitude in Coordinate
        Point format.

    Example
    --------
    >>> file = 'bomen.csv'
    >>> lat_colname = 'latitude'
    >>> long_colname = 'longitude'
    >>> gdf = read_file(file, latitude_col=lat_colname, longitude_col= long_colname)
    >>> gdf.head()
       datum_gemeten        bron   bwz_attributen             bwz_ligging  \
    0            NaN  boombeheer  ***************  buiten de bebouwde kom
    1            NaN  boombeheer  ***************  buiten de bebouwde kom
    2            NaN  boombeheer  ***************  buiten de bebouwde kom
    3            NaN  boombeheer  ***************  buiten de bebouwde kom
    4            NaN  boombeheer  ***************  buiten de bebouwde kom

      bwz_waarde boombeheer_attributen      boomnummer latijnse_boomnaam  \
    0        NaN       ***************  302.3012.bm323     quercus robur
    1        NaN       ***************  302.3012.bm322     quercus robur
    2        NaN       ***************  302.3012.bm321     quercus robur
    3        NaN       ***************  302.3012.bm347  acer saccharinum
    4        NaN       ***************  302.3012.bm346  acer saccharinum

      nederlandse_boomnaam doelstelling  ...               eigendom  \
    0             zomereik          NaN  ...  gemeentelijk eigendom
    1             zomereik          NaN  ...  gemeentelijk eigendom
    2             zomereik          NaN  ...  gemeentelijk eigendom
    3        zilveresdoorn          NaN  ...  gemeentelijk eigendom
    4        zilveresdoorn          NaN  ...  gemeentelijk eigendom

               aannemer standplaats   latitude  longitude geodb_oid objectid  \
    0       particulier        gras  51.635766   5.152344        54       54
    1       particulier        gras  51.635685   5.152416        55       55
    2       particulier        gras  51.635568   5.152547        56       56
    3  gemeente tilburg        gras  51.637685   5.150297        57       57
    4  gemeente tilburg        gras  51.637640   5.150340        58       58

      se_anno_cad_data    _z                  geometry
    0              NaN -9999  POINT (5.15234 51.63577)
    1              NaN -9999  POINT (5.15242 51.63568)
    2              NaN -9999  POINT (5.15255 51.63557)
    3              NaN -9999  POINT (5.15030 51.63769)
    4              NaN -9999  POINT (5.15034 51.63764)

    [5 rows x 27 columns]

    """
    assert header >= 0, 'header must be a positive integer or 0'
    read_type_options = ['latlong', 'Buurt', 'Wijk', 'Gemeente', 'geometry']
    assert read_type in read_type_options, f'read_type is not one of the read type options: {read_type_options}'

    # Start counting from 1. If header = 0, we assume the user counted from 0.
    if header == 0:
        header = 1

    # retrieve extension
    file_ext = filename.split('.')[-1]
    if file_ext == 'xlsx':
        sep = None
        if contents is None:
            contents = filename
        else:
            contents = io.BytesIO(contents)
        df = pd.read_excel(contents, engine='openpyxl', nrows=nrows)

        # In dutch excel, the decimal point is a comma and the point is the thousand delimitor. If the latitude and
        # longitude exceeds expected values, try to scale it down.
        if read_type == 'latlong' and make_geo:
            if not (latitude_col in df.columns and longitude_col in df.columns):
                raise ValueError('Latitude or longitude column names are not in table headers')
            df = _convert_excel_decimals(df, latitude_col, longitude_col)

    elif file_ext == 'csv' or file_ext == 'txt':
        if contents is None:
            contents = filename
            # if no seperator was given, try to guess separator
            if sep is None:
                sep = _get_sep(contents)
        else:
            try:
                decode = contents.decode('utf-8')
            except UnicodeError:
                decode = contents.decode('ISO-8859-1')
            contents = io.StringIO(decode)
            # if no seperator was given, try to guess separator
            if sep is None:
                sep = _get_sep(decode.split('\n'), is_file=False)

        # Try reading in the data with normal utf-8 encoding. If that doesnt work, try ISO.
        try:
            df = pd.read_table(contents, sep=sep, low_memory=False, header=header - 1, nrows=nrows)
        except UnicodeError:
            df = pd.read_table(contents, encoding="ISO-8859-1", sep=sep, low_memory=False, header=header - 1,
                               nrows=nrows)
    else:
        raise IOError('File extension not recognised. Must be one of [xlsx, csv, txt]')

    if not make_geo:
        if return_sep:
            return df, sep
        return df

    if read_type == 'latlong':
        if not (latitude_col in df.columns and longitude_col in df.columns):
            raise ValueError('Latitude or longitude column names are not in table headers')
        try:
            # Convert latitude and longitude floats to points
            geom = gpd.points_from_xy(df[longitude_col], df[latitude_col])
        except ValueError as e:
            raise ValueError('Getting points from the given longitude and latitude columns failed')
    elif read_type == 'geometry':
        if not (geometry_col in df.columns):
            raise ValueError('Geometry column name is not in table headers')
        # Use geometry_col as geometry
        geom = geometry_col
    else:
        shapes = load_location_data(level=read_type, path_to_datasets=path_to_shapes)
        shape_code = {'Buurt': 'BU_CODE', 'Wijk': 'WK_CODE', 'Gemeente': 'GM_CODE'}[read_type]
        df = df.merge(shapes, left_on=codecol, right_on=shape_code)
        if len(df) == 0:
            raise ValueError('Result dataframe is empty after merging location shape data and given dataset')
        geom = 'geometry'

    gdf = gpd.GeoDataFrame(df, geometry=geom, crs=crs)

    if return_sep:
        return gdf, sep
    return gdf


def _convert_excel_decimals(df, latcol, longcol, latbase=51, longbase=3):
    # Setup conversation function
    # The coordinate will be divided by 10 to the power of the number of times you have to multiply 10 to get in the
    # range of the current coordinate. For example: The latitude coordinate 5163576559424015 is given. The latitude
    # coordinates of The Netherlands is roughly between 51 and 54. This indicates that the coordinate should be
    # 51.63576559424015 which is the original devided by 10^14. On the other hand, if this was not the latitude, but the
    # given longitude instead, it should be devided by 10^15 because the longitude coordinates should be between 3 and 8
    convert_lat_long = lambda x, coord_base: x / (10 ** (np.floor(np.log10(x // coord_base))))

    if (df[latcol] < 51).all() | (df[latcol] > 54).all():
        converted_lat = df[latcol].apply(lambda x: convert_lat_long(x, coord_base=latbase))
        if (converted_lat < 51).all() | (converted_lat > 54).all():
            warnings.warn('Latitude coordinates deviates from expected values and can not be succesfully scaled. Be '
                          'cautious in using these coordinates')
        else:
            warnings.warn('Latitude coordinates deviates from expected values. The values will be scaled.')
            df[latcol] = converted_lat

    if (df[longcol] < 3).all() | (df[longcol] > 8).all():
        converted_long = df[longcol].apply(lambda x: convert_lat_long(x, coord_base=longbase))
        if (converted_long < 3).all() | (converted_long > 8).all():
            warnings.warn('Longitude coordinates deviates from expected values and can not be succesfully scaled. Be '
                          'cautious in using these coordinates')
        else:
            warnings.warn('Longitude coordinates deviate from expected values. The values will be scaled.')
            df[longcol] = converted_long

    return df


def convert_data_types(df, dtypedict):
    """
    Convert data types in DataFrame for certain columns.

    Input:
    df <GeoDataFrame> or <pd.DataFrame>
        Dataframe which columns should be converted

    dtypedict <dict>
        Dictionary with column names in the keys and data type in the values. If either column or dtype is not a valid
        input, the conversion will be ignored

    Output:
    df <GeoDataFrame> or <pd.DataFrame>
        Dataframe with converted columns

    Examples
    ------

    >>> df = read_file('bomen.csv')
    >>> df.dtypes[['diameter', 'diameter_in_cm', 'boomhoogte']]
    diameter                   object
    diameter_in_cm              int64
    boomhoogte                 object

    >>> df = convert_data_types(df, dtypedict)
    >>> df.dtypes[['diameter', 'diameter_in_cm', 'boomhoogte']]
    ..\core\data_utils.py:700: UserWarning: Values not suitable for conversion of (float). ValueError was raised:
    could not convert string to float: '20 cm'

    ..\core\data_utils.py:700: UserWarning: Values not suitable for conversion of (float). ValueError was raised:
    could not convert string to float: '15-18 m.'

    diameter           object
    diameter_in_cm    float64
    boomhoogte         object
    dtype: object
    """
    for column in dtypedict.keys():
        if column not in df.columns:
            warnings.warn(f'({column}) not in DataFrame columns. Ignoring datatype conversion')
            continue
        try:
            try:
                df[column] = df[column].astype(dtypedict[column])
            except TypeError:
                warnings.warn(
                    f'Data type ({dtypedict[column]}) for column ({column}) was not understood. Data type conversion '
                    f'for this column will be ignored')
        except ValueError as e:
            warnings.warn(f'Values not suitable for conversion of ({dtypedict[column]}). ValueError was raised:\n{e}')

    return df


def _get_sep(file, is_file=True):
    # Get first and second line from file
    if is_file:
        with open(file, r'r') as enc:
            lines = enc.readlines()
    else:
        lines = file

    first = lines[0]
    second = lines[1]

    # Get character frequency and sort by most common
    counter_first = Counter(first).most_common()

    # Get character frequency and do not sort since this converts it into a tuple
    counter_second = Counter(second)

    for c, freq in counter_first:
        # Check if character is a letter, a digit or a new line character
        if c.isalpha() or c.isdigit() or c == '\n':
            continue

        # if there are as many characters in the first line as in the second line, this could mean this is the seperator
        if counter_second[c] == freq:
            return c

    warnings.warn('No separator found. Using tab as separator')
    return '\t'


def load_dataplatform_data(url: str):
    """
    Load dataset from dataplatform

    Input:
    url <str>
    dataplatform geojson url which can be found here for example:
    https://data.overheid.nl/dataset/stedelijk-groen-gebieden-tilburg or here
    https://ckan.dataplatform.nl/dataset/stedelijk-groen-gebieden-tilburg

    Output: geopandas dataframe
        Dataframe with data from geojson file
    """
    assert 'ckan.dataplatform.nl' in url, 'All dataplatform urls should start with ckan.dataplatform.nl'

    try:
        url_opener = urlopen(url)
        return gpd.read_file(url_opener)
    except HTTPError as e:
        warnings.warn(str(e))
        return gpd.GeoDataFrame()


def _get_code(level):
    """Function to find the corresponding code to a level """
    if level == 'Buurt':
        code = "BU_CODE"
    elif level == 'Wijk':
        code = "WK_CODE"
    elif level == "Gemeente":
        code = "GM_CODE"
    else:
        return None
    return code


def _find_middle_point(code, level, shapes):
    """
    Function that finds the coordinates of the middle point of a shape
    """
    level_code = _get_code(level)
    if code == 'onbekend':
        return [None, None]
    else:
        geometry = shapes[shapes[level_code] == code]['geometry'].values[0]
        middle_point = geometry.centroid
        lon = middle_point.x
        lat = middle_point.y
        return [lon, lat]


def load_gdf_from_json(jsonstr):
    """
    Loads geopandas dataframe from json-string
    """
    return gpd.GeoDataFrame.from_features(json.loads(jsonstr)['features'], crs=4326)


def combine_data_dicts(data1, data2):
    for key in data2.keys():
        data1[key] = data2[key]

    return data1
