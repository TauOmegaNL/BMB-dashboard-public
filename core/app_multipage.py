import dash
import os

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

BS = "https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css"
BMB = os.path.join(THIS_FOLDER, "/core/assets/stylebieb.css")

# meta_tags are required for the app layout to be mobile responsive
app = dash.Dash(__name__, suppress_callback_exceptions=True,
                meta_tags=[{'name': 'viewport',
                            'content': 'width=device-width, initial-scale=0.5'}],
                external_stylesheets=[BMB, BS],
                prevent_initial_callbacks=False)

app.config.suppress_callback_exceptions = True
app.server.config.suppress_callback_exceptions = True
app.config['suppress_callback_exceptions'] = True

server = app.server
