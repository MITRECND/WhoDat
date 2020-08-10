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
        blueprint: A Blueprint that defines the plugin.
        config: A dictionary of specific plugin config details.
    """

    def __init__(self, name, blueprint, config=None):
        self.name = name
        self.blueprint = blueprint
        self.config = config

    @property
    def user_pref(self):
        """Returns a dict of plugin's user preferences or None"""
        return None

    @property
    def jsfiles(self):
        """Returns a list of plugins' bundled ReactJS files"""
        return []

    def setConfig(self, plugin_config):
        """Sets available configuration settings for plugin"""
        self.config = plugin_config


class PassivePluginBase(PluginBase):
    """Plugin base class that all passive plugins should extend.

    Attributes:
        name: A string that stores the plugin's identifying name.
        blueprint: A Blueprint that defines the plugin.
    """

    def __init__(self, name, blueprint):
        super().__init__(name, blueprint)

    @property
    def blueprint(self):
        """Returns blueprint with added forward and reverse endpoints"""
        return self._blueprint

    @blueprint.setter
    def blueprint(self, passive_bp):
        @passive_bp.route("/forward_pdns", methods=["GET", "POST"])
        def handle_forward():
            return self.forward_pdns()

        @passive_bp.route("/reverse_pdns", methods=["GET", "POST"])
        def handle_reverse():
            return self.reverse_pdns()

        self._blueprint = passive_bp

    def forward_pdns(self):
        """Required forward pdns functionality for passive plugin

        Raises:
            NotImplementedError: subclasses must implement"""
        raise NotImplementedError("Passive Plugin must have forward pdns")

    def reverse_pdns(self):
        """Required reverse pdns functionality for passive plugin

        Raises:
            NotImplementedError: subclasses must implement"""
        raise NotImplementedError("Passive Plugin must have reverse pdns")

    def setConfig(self, passive_config):
        """Validates and sets passive configuration settings

        Raises:
            ValueError: Configuration does not contain proper information"""
        if not passive_config.get("API_KEY"):
            raise ValueError
        super().setConfig(passive_config)


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
        TypeError: The function did not return a proper PluginBase plugin

    Returns:
        Wrapped function that registers and returns valid plugins.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        plugin = func(*args, **kwargs)
        if not isinstance(plugin, PluginBase):
            raise TypeError(
                "Cannot register plugin: wrong type {}".format(type(plugin))
            )
        plugin_bp = plugin.blueprint
        if not isinstance(plugin_bp, Blueprint):
            raise TypeError("Cannot register plugin, must return a blueprint")
        PLUGINS.append(plugin)
        # check if there are preferences for the plugin
        if plugin.user_pref is not None:
            preferences.add_user_pref(plugin.name, plugin.user_pref)
        return plugin

    return wrapped


def register_passive_plugin(func):
    """Decorator for registering passive plugins.

    If the plugin is a valid passive plugin, the plugin object will be added to
    the global PLUGINS. If the plugin has preferences, they will be added
    to the global USER_PREF with the plugin name as the key.

    Args:
        func: Expects a function that returns a PassivePluginBase object

    Raises:
        TypeError: The function did not return a valid PassivePluginBase plugin
        ValueError: The proper configuration values were not provided
    Returns:
        Wrapped function that registers and returns valid passive plugins.
    """

    @functools.wraps(func)
    @register_plugin
    def wrapped(*args, **kwargs):
        plugin = func(*args, **kwargs)
        if not isinstance(plugin, PassivePluginBase):
            raise TypeError(
                "Cannot register plugin: wrong type {}".format(type(plugin))
            )
        # check config
        try:
            plugin_config = current_app.config["PASSIVE"][plugin.name]
            plugin.setConfig(plugin_config)
        except (KeyError, ValueError):
            raise ValueError("Passive plugin missing correct config values")

        return plugin

    return wrapped
