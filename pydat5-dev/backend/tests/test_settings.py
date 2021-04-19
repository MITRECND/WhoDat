from pydat.core import plugins
from pydat.core.plugins import register_plugin


def test_settings(client):
    response = client.get("/api/v2/settings")
    assert response.status_code == 200
    data = response.json
    assert 'enable_plugin_test_plugin' not in data.keys()


def test_plugin_settings(sample_plugin, fake_create_app):
    # Reset the PLUGINS Set
    plugins.PLUGINS = set()

    register_plugin(sample_plugin)
    assert sample_plugin in plugins.PLUGINS

    app = fake_create_app({
        'PLUGINS': {'test_plugin': {}}
    })

    client = app.test_client()
    response = client.get("/api/v2/settings")
    assert response.status_code == 200
    data = response.json
    assert data['enable_plugin_test_plugin']
