import pkgutil
import importlib
import pydat.plugins
import yaml

# dictionary of module name and location
MODULES = {}
# list of valid Plugin objects
PLUGINS = []
# dictionary of plugin user preferences
USER_PREF = {}


class PluginBase:
    '''Plugin base class'''
    '''
    name - string
    bp_pref
    user_pref - dictionary
    '''
    user_pref = {}

    def setup(self):
        self.user_pref = self.user_preferences()

    def blueprint_preferences(self):
        pass

    def user_preferences(self):
        pref = None
        try:
            with open("config.yaml") as file:
                pref = yaml.load(file, Loader=yaml.FullLoader)
        except FileNotFoundError:
            pref = None
        if pref is None:
            pref = {}
        return pref

    def name(self):
        return __name__


def iter_namespace(ns_pkg):
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


def get_plugins(namespace=pydat.plugins):
    plugins = iter_namespace(namespace)
    for finder, name, ispkg in plugins:
        MODULES[name] = importlib.import_module(name)


# register decorator
def register(f):
    def wrapped(*args, **kwargs):
        plugin = f(*args, **kwargs)
        if not isinstance(plugin, PluginBase):
            raise TypeError(
                'Cannot register plugin: wrong type {}'.format(type(plugin)))
        name = plugin.name()
        if name not in MODULES.keys():
            raise LookupError(
                'Plugin name not found: {}'.format(name))
        PLUGINS.append(plugin)
        return plugin
    return wrapped
