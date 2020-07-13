import os
from flask import Flask, send_from_directory
from pydat.api.controller import exceptions
from pydat.core import plugins

from pydat.api.controller.session import session_bp


def create_app(test_config=None):
    # Application Factory
    app = Flask(__name__)
    app.config.from_mapping(SECRET_KEY=os.urandom(16),)

    # load testing, if debugging; else, load deployment config
    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    # Register Error Handler
    exceptions.register_errors(app)

    # Register Framework Blueprints
    app.register_blueprint(session_bp, url_prefix="/api/v2")

    # Register Plugin Blueprints
    # add error handling
    for plugin in plugins.get_plugins():
        app.register_blueprint(
            plugin.blueprint(), url_prefix='/api/v2/' + plugin.name)

    # Catch invalid backend calls
    @app.route("/api/v2/", defaults={"path": ""})
    @app.route("/api/v2/<path:path>")
    def invalid(path):
        raise exceptions.ClientError("Nonexistant view {}".format(path), 404)

    # for rule in app.url_map.iter_rules('static'):
        # app.url_map._rules.remove(rule)

    # Serve React App
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path != "" and os.path.exists(app.static_folder + '/' + path):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')

    return app
