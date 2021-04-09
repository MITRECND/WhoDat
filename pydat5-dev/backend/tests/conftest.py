import pytest
from pydat.api import create_app, elasticsearch_handler
from pydat.core.plugins import (
    PluginBase,
    PassivePluginBase,
)
from flask import Blueprint


@pytest.fixture
def config_app():
    app = create_app(
        {
            "TESTING": True,
            "SEARCHKEYS": [
                'domainName',
                'registrant_name',
                'contactEmail',
                'registrant_telephone',
            ],
            "PDNSSOURCES": {
                "TestPassive": {}
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
def sample_plugin():

    class TestPlugin(PluginBase):
        bp = Blueprint('test_plugin', __name__)

        def __init__(self):
            super().__init__('test_plugin', self.bp)
            self.bp.route('/hello')(self.hello)

        @property
        def jsfiles(self):
            return ['testfile.js', 'testfile2.js']

        def hello(self):
            return "Success!"

        def setConfig(self, **kwargs):
            pass

    return TestPlugin


# simple test passive plugin, returns created valid plugin
@pytest.fixture
def sample_passive_plugin():

    class TestPassivePlugin(PassivePluginBase):
        bp = Blueprint('passive_plugin', __name__)

        def __init__(self):
            super().__init__('passive_plugin', self.bp)
            self.bp.route("/hello")(self.hello)

        @property
        def jsfiles(self):
            return ['testfile1.js', 'testfile2.js']

        def forward(self):
            return {}

        def reverse(self):
            return {}

        def setConfig(self, **kwargs):
            self.config = kwargs

        def hello(self):
            return "Success!"

    return TestPassivePlugin


@pytest.fixture
def es_handler():
    """ElasticSearch Handler"""
    return elasticsearch_handler
