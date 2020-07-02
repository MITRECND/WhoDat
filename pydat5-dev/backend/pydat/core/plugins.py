import pkgutil
import importlib
import pydat.plugins

PLUGINS = {}
ENABLE_PLUGIN = {}


class PluginBase:
    '''Plugin base class'''
    def blueprint_preferences():
        pass

    def user_preferences():
        pass

    def get_preferences():
        pass


def iter_namespace(ns_pkg):
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


def get_plugins(namespace=pydat.plugins):
    plugins = iter_namespace(namespace)
    for finder, name, ispkg in plugins:
        PLUGINS[name] = importlib.import_module(name)


# register decorator
def register(cls):
    if not isinstance(cls, PluginBase):
        raise TypeError(
            'Cannot register plugin: wrong type {}'.format(type(cls)))
    ENABLE_PLUGIN[cls] = True
    return cls
