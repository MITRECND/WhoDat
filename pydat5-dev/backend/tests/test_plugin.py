from pydat.core import plugins
from pydat.core.plugins import PluginManager
from flask import Flask, Blueprint
from pydat.core.plugins import PluginBase, register_plugin
import pytest
# from pydat.core import preferences


def test_registration(sample_plugin):
    # Reset the PLUGINS Set
    plugins.PLUGINS = set()

    register_plugin(sample_plugin)
    assert sample_plugin in plugins.PLUGINS

    app = Flask(__name__)
    app.config['PDNSSOURCES'] = dict()
    app.config['PLUGINS'] = {'test_plugin': {}}

    with app.app_context():
        plugin_manager = PluginManager()
        plugin_manager.gather_plugins()
        loaded = plugin_manager.plugins
        assert len(loaded) == 1
        assert isinstance(loaded[0], sample_plugin)


def test_registration_bp(sample_plugin, fake_create_app):
    # Reset the PLUGINS Set
    plugins.PLUGINS = set()

    # check bp properly registered
    register_plugin(sample_plugin)

    app = fake_create_app(
        {"TESTING": True, "PLUGINS": {"test_plugin": {}}}
    )
    routes = [str(p) for p in app.url_map.iter_rules()]
    assert '/api/plugin/test_plugin/hello' in routes

    client = app.test_client()
    response = client.get('/api/plugin/test_plugin/hello')
    assert response.status_code == 200

    # with client:
    #     response = client.get('/api/v2/session/test_plugin')
    #     assert response.is_json
    #     json_data = response.get_json()
    #     assert test_pref.keys() == json_data.keys()
    #     assert "test_plugin" in session.keys()
    #     assert test_pref.keys() == session["test_plugin"].keys()


# test invalid plugins
def test_invalid_plugin():
    # Reset the PLUGINS Set
    plugins.PLUGINS = set()

    # Not child of PluginBase
    class FakePlugin():
        def set_name(self):
            return "fake"

    with pytest.raises(TypeError):
        register_plugin(FakePlugin)


def test_invalid_plugin_bp():
    # Reset the PLUGINS Set
    plugins.PLUGINS = set()

    # does not return proper blueprint
    class BadPlugin(PluginBase):
        def __init__(self):
            super().__init__('bad_plugin', Blueprint('test', 'test'))

        @property
        def blueprint(self):
            return ["fake"]

        @blueprint.setter
        def blueprint(self, newbp):
            self._blueprint = newbp

        def setConfig(self, **kwargs):
            pass

    register_plugin(BadPlugin)

    app = Flask(__name__)
    app.config['PDNSSOURCES'] = dict()
    app.config['PLUGINS'] = {'bad_plugin': {}}

    with app.app_context():
        plugin_manager = PluginManager()
        with pytest.raises(ValueError):
            plugin_manager.gather_plugins()
