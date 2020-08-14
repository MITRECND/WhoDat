import pytest
from pydat.api import create_app, elasticsearch_handler
from pydat.core.plugins import (
    PluginBase,
    register_plugin,
    PassivePluginBase,
)
from flask import Blueprint


@pytest.fixture
def config_app():
    app = create_app(
        {
            "TESTING": True,
            "SEARCHKEYS": [
                        ('domainName', 'Domain'),
                        ('registrant_name', 'Registrant Name'),
                        ('contactEmail', 'Contact Email'),
                        ('registrant_telephone', 'Telephone')
                        ],
            "PDNSSOURCES": {
                "TestPassive": {

                }
            }
        }
    )
    return app


@pytest.fixture
def client():
    app = create_app({"TESTING": True, })
    return app.test_client()


# simple test plugin, returns created valid plugin
@pytest.fixture
def create_plugin():
    def _create_plugin(user_pref=None, name="hello", jsfiles=[]):
        bp = Blueprint(name, __name__)

        @bp.route("/hello")
        def hello():
            return "Success!"

        class TestPlugin(PluginBase):
            @property
            def user_pref(self):
                return user_pref

            @property
            def jsfiles(self):
                return jsfiles

        @register_plugin
        def start_plugin():
            test = TestPlugin(name, bp)
            return test

        test_plugin = start_plugin()
        return test_plugin

    return _create_plugin


# simple test passive plugin, returns created valid plugin
@pytest.fixture
def create_passive_plugin():
    def _create_passive_plugin(name="TestPassive", user_pref=None, jsfiles=[]):
        bp = Blueprint(name, __name__)

        @bp.route("/hello")
        def hello():
            return "Success!"

        class TestPassivePlugin(PassivePluginBase):
            @property
            def user_pref(self):
                return user_pref

            @property
            def jsfiles(self):
                return jsfiles

            def forward_pdns(self):
                return "Forward success!"

            def reverse_pdns(self):
                return "Reverse success!"

            def setConfig(self, test_config):
                self.config = test_config

        return TestPassivePlugin(name, bp)

    return _create_passive_plugin


@pytest.fixture
def es_handler():
    """ElasticSearch Handler"""
    return elasticsearch_handler