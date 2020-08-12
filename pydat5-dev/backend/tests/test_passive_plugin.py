from pydat.core.plugins import (
    PassivePluginBase,
    register_passive_plugin,
    PLUGINS
)
from pydat.api import create_app
import pytest
from flask import Blueprint


def test_no_config_registration(config_app, create_passive_plugin):
    test_plugin = create_passive_plugin("TestPassive")

    @register_passive_plugin
    def start_plugin():
        return test_plugin

    app = create_app({"TESTING": True, })
    with app.app_context():
        with pytest.raises(ValueError):
            assert start_plugin()

    test_plugin = create_passive_plugin("fake_plugin")
    with config_app.app_context():
        with pytest.raises(ValueError):
            start_plugin()


def test_registration(config_app, create_passive_plugin):
    test_plugin = create_passive_plugin("TestPassive")

    @register_passive_plugin
    def start_plugin():
        return test_plugin

    with config_app.app_context():
        start_plugin()

    plugin_exists = False
    for obj in PLUGINS:
        if obj is test_plugin:
            plugin_exists = True
    assert plugin_exists
    assert isinstance(test_plugin, PassivePluginBase)

    app = create_app({"TESTING": True, })
    client = app.test_client()
    response = client.get(f'/api/v2/passive/{test_plugin.name}/forward_pdns')
    assert response.status_code == 200
    response = client.get(f'/api/v2/passive/{test_plugin.name}/reverse_pdns')
    assert response.status_code == 200


def test_invalid_plugin(config_app):

    bp = Blueprint("fake_plugin", __name__)

    # Doesn't have forward
    class MissingForward(PassivePluginBase):
        def reverse_pdns(self):
            return "Reverse success!"

        def setConfig(self, test_config):
            self.config = test_config

    # Doesn't have reverse
    class MissingReverse(PassivePluginBase):
        def forward_pdns(self):
            return "Forward success!"

        def setConfig(self, test_config):
            self.config = test_config

    # Doesn't have setConfig
    class MissingConfig(PassivePluginBase):
        def reverse_pdns(self):
            return "Reverse success!"

        def forward_pdns(self):
            return "Forward success!"

    test_plugin = MissingForward("MissingForward", bp)

    with pytest.raises(NotImplementedError):
        test_plugin.forward_pdns()

    test_plugin = MissingReverse("MissingReverse", bp)
    with pytest.raises(NotImplementedError):
        test_plugin.reverse_pdns()

    test_plugin = MissingConfig("MissingConfig", bp)
    with pytest.raises(NotImplementedError):
        test_plugin.setConfig("fake_config")
