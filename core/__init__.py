from core.apps import pagina_data_laden as dl
from core.apps import pagina_visualisatie_kaart as vk
from core.apps import pagina_interactie_kaart as ik
from core.app_multipage import app
from core.app_multipage import server

from core.utils import upload_button_style, get_callback_trigger
from core.data_utils import load_meet_je_stad, aggregate_point_data, load_location_data, \
    read_file, _get_sep, _get_code, load_dataplatform_data, load_gdf_from_json
from core.visualisatie_utils import plolty_figure_wrapper, plolty_gemeente_map_wrapper
