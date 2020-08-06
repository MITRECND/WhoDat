import pkgutil
import importlib
import pydat.plugins
import functools
from flask import Blueprint, current_app
from pydat.core import preferences

# list of valid Plugin objects
PLUGINS = []


class PluginBase:
    """Plugin base class that all plugins should extend.

    Attributes:
        name: A string that stores the plugin's identifying name.
        user_pref: A dict mapping plugin parameter's to their value type.
    """
    def __init__(self, name, blueprint):
        self.name = name

    @property
    def blueprint(self):
        """Returns the plugin's Blueprint. Must be overriden."""
        raise NotImplementedError(
                'Plugin must have blueprint')

    @property
    def user_pref(self):
        """Returns a dict of plugin's user preferences or None"""
        return None

    @property
    def jsfiles(self):
        """Returns a list of plugins' bundled ReactJS files"""
        return []


class PassivePluginBase(PluginBase):
    @property
    def blueprint(self):
        return self._blueprint

    @blueprint.setter
    def blueprint(self, passive_bp):
        @passive_bp.route("/passive_dns", methods=["POST"])
        def handle_passive():
            self.passive_dns()

        @passive_bp.route("/reverse_dns", methods=["POST"])
        def handle_reverse():
            self.reverse_dns()

    def passive_dns(self):
        pass

    def reverse_dns(self):
        pass

    @property
    def config(self):
        return None


def get_plugins(ns_pkg=pydat.plugins):
    """Imports all modules found under namespace. Stores them in global MODULES.

    Args:
        namespace (module, optional): Namespace package to search for plugins.
            Defaults to pydat.plugins.
    """
    plugins = pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")
    for finder, name, ispkg in plugins:
        importlib.import_module(name)
    return PLUGINS


def register_plugin(func):
    """Decorator for registering plugins.

    If the plugin is a valid plugin, the plugin object will be added to
    the global PLUGINS. If the plugin has preferences, they will be added
    to the global USER_PREF with the plugin name as the key.

    Args:
        func: Expects a function that returns a PluginBase subclass object

    Raises:
        TypeError: The function did not return a PluginBase plugin
        NotImplementedError: The subclass did not override blueprint()

    Returns:
        Wrapped function that registers valid plugins.
    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        plugin = func(*args, **kwargs)
        if not isinstance(plugin, PluginBase):
            raise TypeError(
                'Cannot register plugin: wrong type {}'.format(type(plugin)))
        plugin_bp = plugin.blueprint
        if not isinstance(plugin_bp, Blueprint):
            raise TypeError('Cannot register plugin, must return a blueprint')
        PLUGINS.append(plugin)
        # check if there are preferences for the plugin
        if plugin.user_pref is not None:
            preferences.add_user_pref(plugin.name, plugin.user_pref)
        return plugin
    return wrapped


@register_plugin
def register_passive_plugin(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        plugin = func(*args, **kwargs)
        if not isinstance(plugin, PassivePluginBase):
            raise TypeError(
                'Cannot register plugin: wrong type {}'.format(type(plugin)))
        # check config
        try:
            plugin_config = current_app.config["PASSIVE"][plugin.name]
            api_key = plugin_config["API_KEY"]
            plugin.config = plugin_config
        except KeyError:
            raise ValueError("Passive plugin needs correct config values")

        return plugin
    return wrapped
