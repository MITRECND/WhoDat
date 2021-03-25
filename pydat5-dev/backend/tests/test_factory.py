from pydat.api import create_app
from flask import template_rendered
from contextlib import contextmanager
from unittest.mock import MagicMock
import pytest


def test_config():
    # check that if a config is passed, default is overridden
    assert not create_app().testing
    assert create_app({"TESTING": True}).testing


def test_error(client):
    # check that non-routed api namespace lead to 404
    response = client.get("/api/v2/session/illegal")
    assert response.status_code == 404

    response = client.get("/api/v2/illegal")
    assert response.status_code == 404


@contextmanager
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def test_index():
    app = create_app({"TESTING": True, })
    # with captured_templates(app) as templates:
    response = app.test_client().get("/")
    assert response.status_code == 200
    # assert len(templates) == 1
    # template, context = templates[0]
    # assert template.name == 'index.html'


def test_debug():
    create_app({"DEBUG": True})


def test_plugin_failure(monkeypatch):
    with monkeypatch.context() as m:
        mockPluginManager = MagicMock(side_effect=ValueError)
        m.setattr(
            'pydat.core.plugins.PluginManager.gather_plugins',
            mockPluginManager)
        with pytest.raises(SystemExit):
            create_app()
