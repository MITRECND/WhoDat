import pkgutil
import importlib
import pydat.plugins
import functools
from flask import Blueprint
from pydat.core import preferences

# list of valid Plugin objects
PLUGINS = []


class PluginBase:
    """Plugin base class that all plugins should extend.

    Attributes:
        name: A string that stores the plugin's identifying name.
        user_pref: A dict mapping plugin parameter's to their value type.
    """
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

    @property
    def name(self):
        """Returns the plugin's name. Used for preferences and endpoints"""
        return self.__module__.split('.')[-1]


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


def register(func):
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
