import os
import sys
import logging
from flask import Flask, send_from_directory, render_template
from pydat.core.config_parser import ConfigParser, DEFAULT_CONFIG
from pydat.core.es import ElasticsearchHandler
from pydat.core.preferences import UserPreferenceManager


elasticsearch_handler = ElasticsearchHandler()
preferences_manager = UserPreferenceManager()


def create_app(config=None):
    # Application Factory
    app = Flask(__name__)
    app.config.from_mapping(SECRET_KEY=os.urandom(16),)

    app.config.from_object(DEFAULT_CONFIG)

    if config is not None:
        app.config.from_mapping(config)

    config_parser = ConfigParser(app)
    config_parser.parse()

    if app.config['DEBUG']:
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)

    # Initialize Plugins
    elasticsearch_handler.init_app(app)

    preferences_manager.init_app(app)

    # Register Error Handler
    from pydat.api.controller import exceptions
    exceptions.register_errors(app)

    # Register Framework Blueprints
    from pydat.api.controller.session import session_bp
    from pydat.api.controller.v1.whois import whoisv1_bp
    from pydat.api.controller.v2.whois import whoisv2_bp
    app.register_blueprint(session_bp, url_prefix="/api/v2")
    app.register_blueprint(whoisv2_bp, url_prefix="/api/v2")

    # version 1 backwards compatibility
    app.register_blueprint(whoisv1_bp, url_prefix="/api/v1")

    from pydat.core.plugins import PluginManager
    plugin_manager = PluginManager()

    # Register Plugin Blueprints and JSfiles
    # add error handling
    included_jsfiles = []
    with app.app_context():
        try:
            plugin_manager.gather_plugins()
        except ValueError as e:
            print(f"Unable to instantiate plugins: {str(e)}")
            sys.exit(1)

        for plugin in plugin_manager.plugins:
            url_prefix = os.path.join(plugin.prefix, plugin.name)
            app.register_blueprint(plugin.blueprint, url_prefix=url_prefix)
            included_jsfiles.extend(plugin.jsfiles)

    # Catch invalid backend calls
    @app.route("/api", defaults={"path": ""})
    @app.route("/api/<path:path>")
    def invalid(path):
        raise exceptions.ClientError("Nonexistant view {}".format(path), 404)

    # Serve React App

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path != "" and os.path.exists(app.static_folder + '/' + path):
            return send_from_directory(app.static_folder, path)
        else:
            return render_template('index.html', jsfiles=included_jsfiles)

    return app
