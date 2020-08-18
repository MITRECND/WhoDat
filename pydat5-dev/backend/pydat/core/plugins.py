import pkgutil
import importlib
import pydat.plugins
from flask import Blueprint, current_app
from pydat.api import preferences_manager
# from pydat.core import preferences

# list of valid Plugin objects
PLUGINS = set()


class PluginBase:
    """Plugin base class that all plugins should extend.

    Attributes:
        name: A string that stores the plugin's identifying name.
        blueprint: A Blueprint that defines the plugin.
    """

    def __init__(self, name, blueprint, preferences=None):
        self.name = name
        self.blueprint = blueprint
        self._prefix = '/api/plugin/'
        self._preferences = None
        if preferences is not None:
            self._preferences = preferences

    @property
    def prefix(self):
        return self._prefix

    @property
    def preferences(self):
        """Returns a dict of plugin's user preferences or None

            Example:
            {
                'mynamespace': [
                    UserPreference(<name>, <type>)
                ]
            }
        """
        return self._preferences

    @property
    def jsfiles(self):
        """Returns a list of plugins' bundled ReactJS files"""
        return []

    def setConfig(self, **kwargs):
        """Function to allow plugin to handle config

        Raises:
            NotImplementedError: Must check for proper configuration.
                            Raise ValueError if needed config isn't there"""
        raise NotImplementedError("Plugin must handle configuration")

    @property
    def blueprint(self):
        """Returns blueprint"""
        return self._blueprint

    @blueprint.setter
    def blueprint(self, new_blueprint):
        if not isinstance(new_blueprint, Blueprint):
            raise TypeError("blueprint must of of type Blueprint")
        self._blueprint = new_blueprint


class PassivePluginBase(PluginBase):
    """Plugin base class that all passive plugins should extend.

    Attributes:
        name: A string that stores the plugin's identifying name.
        blueprint: A Blueprint that defines the plugin.
    """

    def __init__(self, name, blueprint, preferences=None):
        super().__init__(name, blueprint, preferences)
        self._prefix += 'passive/'

    @property
    def blueprint(self):
        """Returns blueprint"""
        return self._blueprint

    @blueprint.setter
    def blueprint(self, passive_bp):
        if not isinstance(passive_bp, Blueprint):
            raise TypeError("blueprint must of of type Blueprint")

        passive_bp.route("/forward", methods=["POST"])(self.forward)
        passive_bp.route("/reverse", methods=["POST"])(self.reverse)

        self._blueprint = passive_bp

    def forward(self):
        """Required forward pdns functionality for passive plugin

        Raises:
            NotImplementedError: subclasses must implement"""
        raise NotImplementedError("Passive Plugin must have forward pdns")

    def reverse(self):
        """Required reverse pdns functionality for passive plugin

        Raises:
            NotImplementedError: subclasses must implement"""
        raise NotImplementedError("Passive Plugin must have reverse pdns")


class PluginManager:
    def __init__(self, namespace=pydat.plugins):
        """Initializes PluginManager

        Args:
            namespace (module, optional): Namespace package to search
                for plugins. Defaults to pydat.plugins.
        """
        self.namespace = namespace
        self._plugins = []

    def gather_plugins(self):
        """Iterates through namespace to execute global module code
        """

        plugins = pkgutil.iter_modules(
            self.namespace.__path__, self.namespace.__name__ + ".")

        for (finder, name, ispkg) in plugins:
            importlib.import_module(name)

        for plugin_class in PLUGINS:
            plugin = plugin_class()

            current_app.logger.info(f"Setting up plugin {plugin.name}")

            if isinstance(plugin, PassivePluginBase):
                config = current_app.config['PDNSSOURCES'].get(
                    plugin.name, None)
            else:
                config = current_app.config['PLUGINS'].get(plugin.name, None)

            if config is None:
                current_app.logger.warning(
                    f"No config for plugin '{plugin.name}', disabling")
                continue

            try:
                plugin.setConfig(**config)
            except (KeyError, ValueError):
                raise ValueError(
                    f"Plugin '{plugin.name}' missing proper configuration")

            try:
                blueprint = plugin.blueprint
            except Exception:
                raise ValueError(
                    f"Plugin '{plugin.name}' unable to get blueprint")

            if not isinstance(blueprint, Blueprint):
                raise ValueError(
                    f"Plugin '{plugin.name}' providing invalid blueprint")

            # Check if there are preferences for the plugin
            if plugin.preferences is not None:
                for (namespace, preferences) in plugin.preferences.items():
                    for preference in preferences:
                        preferences_manager.add_preference(
                            namespace, preference
                        )

            self._plugins.append(plugin)

    @property
    def plugins(self):
        return self._plugins


def register_plugin(plugin):
    """Decorator for registering plugins.

    If the plugin is a valid plugin, the plugin object will be added to
    the global PLUGINS. If the plugin has preferences, they will be added
    to the global USER_PREF with the plugin name as the key.

    Args:
        plugin: Expects a subclass of PluginBase

    Raises:
        TypeError: plugin is not a subclass of PluginBase

    Returns:
        Original class after registering it
    """

    if not issubclass(plugin, PluginBase):
        raise TypeError("Plugin must be subclass of PluginBase")

    PLUGINS.add(plugin)

    return plugin


def register_passive_plugin(plugin):
    """Decorator for registering passive plugins.

    If the plugin is a valid passive plugin, the plugin object will be added to
    the global PLUGINS. If the plugin has preferences, they will be added
    to the global USER_PREF with the plugin name as the key.

    Args:
        plugin: Expects a subclass of PassivePluginBase

    Raises:
        TypeError: The function did not return a valid PassivePluginBase plugin
        ValueError: The proper configuration values were not provided

    Returns:
        Wrapped function that registers and returns valid passive plugins.
    """

    if not issubclass(plugin, PassivePluginBase):
        raise TypeError("Plugin must be subclass of PassivePluginBase")

    return register_plugin(plugin)
