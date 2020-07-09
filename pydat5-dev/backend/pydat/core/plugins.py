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
    '''Plugin base class'''

    def setup(self):
        self.name = self.set_name()
        self.user_pref = self.set_user_pref()

    # return blueprint
    def blueprint(self):
        return None

    # find and parse config file
    def set_user_pref(self):
        return {}

    def set_name(self):
        return self.__module__.split('.')[-1]


# helper method for get_plugins
def iter_namespace(ns_pkg):
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


# import plugins
def get_plugins(namespace=pydat.plugins):
    plugins = iter_namespace(namespace)
    for finder, name, ispkg in plugins:
        MODULES[name] = importlib.import_module(name)


# register decorator
def register(func):
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
        USER_PREF[plugin.name] = plugin.user_pref
        return plugin
    return wrapped
