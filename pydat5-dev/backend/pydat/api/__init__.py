import os

from flask import Flask, send_from_directory


def create_app(test_config=None):
    # Application Factory
    app = Flask(__name__, instance_relative_config=True, static_folder='build')
    app.config.from_mapping(SECRET_KEY="dev",)

    # load testing, if debugging; else, load deployment config
    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    # create instance folder if it doesn't exist
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register Framework Blueprints


    # Register Plugin Blueprints

 
    # catch invalid backend calls
    @app.route("/api/v1/", defaults={"path": ""})
    @app.route("/api/v1/<path:path>")
    def invalid(path):
        raise exceptions.InvalidUsage("Nonexistant view {}".format(path), 404)

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
