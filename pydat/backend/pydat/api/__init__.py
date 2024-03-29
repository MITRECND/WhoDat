import os
import sys
import logging
from flask import Flask, send_from_directory
from flask_caching import Cache
from pydat.core.config_parser import ConfigParser, DEFAULT_CONFIG
from pydat.core.elastic.search.flask_handler import FlaskElasticHandler


CACHE_TIMEOUT = 300  # Flask cache timeout


elasticsearch_handler = FlaskElasticHandler()
flask_cache = Cache()


def create_app(config=None):
    # Application Factory
    app = Flask(__name__)
    app.config.from_mapping(SECRET_KEY=os.urandom(16),)

    app.config.from_object(DEFAULT_CONFIG)

    if config is not None:
        app.config.from_mapping(config)

    config_parser = ConfigParser(app)
    config_parser.parse()

    # Setup cache configuration
    app.config["CACHE_TYPE"] = "SimpleCache"
    app.config["CACHE_DEFAULT_TIMEOUT"] = CACHE_TIMEOUT

    flask_cache.init_app(app)

    if app.config['DEBUG']:
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)

    static_folder = app.config.get('STATICFOLDER', '')
    if static_folder != '':
        app.static_folder = static_folder

    # Initialize Plugins
    elasticsearch_handler.init_app(app)

    # Register Error Handler
    from pydat.api.controller import exceptions
    exceptions.register_errors(app)

    # Register Framework Blueprints
    from pydat.api.controller.v1.whois import whoisv1_bp
    from pydat.api.controller.v2.whois import whoisv2_bp
    from pydat.api.controller.v2.settings import settings_bp
    app.register_blueprint(settings_bp, url_prefix="/api/v2")
    app.register_blueprint(whoisv2_bp, url_prefix="/api/v2")

    # version 1 backwards compatibility
    app.register_blueprint(whoisv1_bp, url_prefix="/api/v1")

    from pydat.core.plugins import PluginManager
    plugin_manager = PluginManager()

    # Register Plugin Blueprints and JSfiles
    # add error handling
    installed_plugins = []
    with app.app_context():
        try:
            plugin_manager.gather_plugins()
        except ValueError as e:
            print(f"Unable to instantiate plugins: {str(e)}")
            sys.exit(1)

        for plugin in plugin_manager.plugins:
            installed_plugins.append(plugin.name)
            url_prefix = os.path.join(plugin.prefix, plugin.name)
            app.register_blueprint(plugin.blueprint, url_prefix=url_prefix)

    app.config['PYDAT_PLUGINS'] = installed_plugins

    # Remove default 'static' endpoint and mapping
    # which interferes with routing frontend components
    for rule in app.url_map.iter_rules('static'):
        app.url_map._rules.remove(rule)

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
            return send_from_directory(app.static_folder, 'index.html')

    return app
