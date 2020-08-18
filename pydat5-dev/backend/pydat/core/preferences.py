from flask import current_app


class UserPreference:
    def __init__(self, name, _type):
        self._name = name
        if not isinstance(_type, type):
            raise ValueError("Second paramater must be a type")
        self._type = _type

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type


class UserPreferenceManager:
    def __init__(self):
        self.app = None

    def init_app(self, app):
        self.app = app
        self.app._preferences_storage = {
            'global': {
                'page_size': 1000
            }
        }

    @property
    def _preferences(self):
        app = current_app or self.app

        if getattr(app, '_preferences_storage', None) is None:
            raise RuntimeError(
                "init_app needs to be called before using this class")

        return app._preferences_storage

    def add_preference(self, namespace, preference):
        if not isinstance(preference, UserPreference):
            raise ValueError("Expected a 'UserPreference' instance")

        if namespace not in self._preferences.keys():
            self._preferences[namespace] = {}

        self._preferences[namespace][preference.name] = preference.type

    def get_preferences(self, namespace=None):
        if namespace is not None:
            if namespace not in self._preferences.keys():
                raise KeyError("No namespace by that name")
            else:
                return self._preferences[namespace]
        else:
            return self._preferences

    def validate_param(self, namespace, name, value):
        if namespace not in self._preferences:
            raise ValueError(f"No namespace {namespace}")

        if name not in self._preferences[namespace].keys():
            raise ValueError(f"No parameter {name} in namespace {namespace}")

        _type = self._preferences[namespace][name]

        if not isinstance(value, _type):
            raise TypeError(
                f"Provided value for {name} is not of type {_type}")
