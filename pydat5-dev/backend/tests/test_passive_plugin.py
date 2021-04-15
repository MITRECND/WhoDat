from pydat.core import plugins
from pydat.core.plugins import (
    PluginManager,
    PassivePluginBase,
    register_passive_plugin,
)
import pytest
from flask import Blueprint, Flask


# def test_no_config_registration(config_app, sample_passive_plugin):
#     # Reset the PLUGINS Set
#     plugins.PLUGINS = set()

#     register_passive_plugin(sample_passive_plugin)

#     app = create_app({"TESTING": True, })
#     with app.app_context():
#         with pytest.raises(ValueError):
#             assert start_plugin()

#     test_plugin = create_passive_plugin("fake_plugin")
#     with config_app.app_context():
#         with pytest.raises(ValueError):
#             start_plugin()


def test_registration(sample_passive_plugin):
    # Reset the PLUGINS Set
    plugins.PLUGINS = set()

    register_passive_plugin(sample_passive_plugin)

    assert sample_passive_plugin in plugins.PLUGINS

    app = Flask(__name__)
    app.config['PDNSSOURCES'] = {'passive_plugin': {}}
    app.config['PLUGINS'] = dict()

    with app.app_context():
        plugin_manager = PluginManager()
        plugin_manager.gather_plugins()
        loaded = plugin_manager.plugins
        assert len(loaded) == 1
        assert isinstance(loaded[0], sample_passive_plugin)


def test_registration_bp(sample_passive_plugin, fake_create_app):
    # Reset the PLUGINS Set
    plugins.PLUGINS = set()

    # check bp properly registered
    register_passive_plugin(sample_passive_plugin)
    plugin_name = 'passive_plugin'

    app = fake_create_app(
        {"TESTING": True, "PDNSSOURCES": {"passive_plugin": {}}}
    )
    routes = [str(p) for p in app.url_map.iter_rules()]
    assert f'/api/plugin/passive/{plugin_name}/hello' in routes

    client = app.test_client()
    response = client.get(f'/api/plugin/passive/{plugin_name}/hello')
    assert response.status_code == 200
    response = client.post(f'/api/plugin/passive/{plugin_name}/forward')
    assert response.status_code == 200
    response = client.post(f'/api/plugin/passive/{plugin_name}/reverse')
    assert response.status_code == 200


def test_invalid_plugin(config_app):
    # Reset the PLUGINS Set
    plugins.PLUGINS = set()

    bp = Blueprint("fake_plugin", __name__)

    # Doesn't have forward
    class MissingForward(PassivePluginBase):
        def reverse(self):
            return "Reverse success!"

        def setConfig(self, **kwargs):
            self.config = kwargs

    # Doesn't have reverse
    class MissingReverse(PassivePluginBase):
        def forward(self):
            return "Forward success!"

        def setConfig(self, **kwargs):
            self.config = kwargs

    # Doesn't have setConfig
    class MissingConfig(PassivePluginBase):
        def reverse(self):
            return "Reverse success!"

        def forward(self):
            return "Forward success!"

    test_plugin = MissingForward("MissingForward", bp)

    with pytest.raises(NotImplementedError):
        test_plugin.forward()

    test_plugin = MissingReverse("MissingReverse", bp)
    with pytest.raises(NotImplementedError):
        test_plugin.reverse()

    test_plugin = MissingConfig("MissingConfig", bp)
    with pytest.raises(NotImplementedError):
        test_plugin.setConfig()
