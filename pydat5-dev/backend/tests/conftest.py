import pytest
from pydat.api import create_app


@pytest.fixture
def app():
    # create app in test mode
    app = create_app({"TESTING": True, })

    yield app


@pytest.fixture
def client(app):
    return app.test_client()
