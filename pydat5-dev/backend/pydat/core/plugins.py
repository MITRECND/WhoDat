import pkgutil
import importlib
import pydat.plugins
import functools

# dictionary of module name and location
MODULES = {}
# list of valid Plugin objects
PLUGINS = []
# dictionary of plugin user preferences
USER_PREF = {}


class PluginBase:
    """Plugin base class that all plugins should extend.

    Attributes:
        name: A string that stores the plugin's identifying name.
        user_pref: A dict mapping plugin parameter's to their value type.
    """

    def __init__(self):
        """Inits PluginBase with set_name() and set_user_pref()"""
        self.name = self.set_name()
        self.user_pref = self.set_user_pref()

    def setup(self):
        pass

    def blueprint(self):
        """Returns the plugin's Blueprint. Must be overriden."""
        return None

    def set_user_pref(self):
        """Returns a dict of plugin's user preferences or None"""
        return None

    def set_name(self):
        """Returns the plugin's name. Used for preferences and endpoints"""
        return self.__module__.split('.')[-1]


def iter_namespace(ns_pkg):
    """Finds modules under a namespace package. Helper method for get_plugins.

    Args:
        ns_pkg (module): A package to search under for modules

    Returns:
        A generator that yields found modules.
    """
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


def get_plugins(namespace=pydat.plugins):
    """Imports all modules found under namespace. Stores them in global MODULES.

    Args:
        namespace (module, optional): Namespace package to search for plugins.
            Defaults to pydat.plugins.
    """
    plugins = iter_namespace(namespace)
    for finder, name, ispkg in plugins:
        MODULES[name] = importlib.import_module(name)


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
        if plugin.blueprint() is None:
            raise NotImplementedError(
                'Cannot register plugin: must have blueprint')
        PLUGINS.append(plugin)
        # check if there are preferences for the plugin
        if plugin.user_pref is not None:
            USER_PREF[plugin.name] = plugin.user_pref
        return plugin
    return wrapped
