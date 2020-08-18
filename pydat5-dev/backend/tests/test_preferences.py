from pydat.core.preferences import UserPreference, UserPreferenceManager
from flask import Flask
import pytest


def test_bad_pref():
    with pytest.raises(ValueError):
        UserPreference('test', 'test')


def test_pref():
    pref = UserPreference('test', str)
    assert pref
    assert pref.name == 'test'
    assert pref.type == str


def test_manager():
    manager = UserPreferenceManager()
    app = Flask(__name__)
    manager.init_app(app)

    with pytest.raises(KeyError):
        manager.get_preferences('foo')

    all_prefs = manager.get_preferences()
    assert 'global' in all_prefs.keys()

    with pytest.raises(ValueError):
        manager.add_preference('global', None)

    manager.add_preference('testnamespace', UserPreference('test', int))
    manager.add_preference('global', UserPreference('test', int))
    global_prefs = manager.get_preferences('global')
    test_prefs = manager.get_preferences('testnamespace')

    assert global_prefs
    assert test_prefs

    assert global_prefs['test'] == int
    assert test_prefs['test'] == int


def test_manager_validation():
    manager = UserPreferenceManager()
    app = Flask(__name__)
    manager.init_app(app)

    manager.add_preference('global', UserPreference('test', int))
    with pytest.raises(ValueError):
        manager.validate_param('foo', 'test', 'test')

    with pytest.raises(ValueError):
        manager.validate_param('global', 'foo', 'test')

    with pytest.raises(TypeError):
        manager.validate_param('global', 'test', 'test')

    manager.validate_param('global', 'test', 1)


def test_manager_no_app():
    manager = UserPreferenceManager()
    with pytest.raises(RuntimeError):
        manager.get_preferences()
