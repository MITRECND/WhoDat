from pydat.core.plugins import PLUGINS, USER_PREF
from flask import Blueprint, session
from pydat.api import create_app


def test_plugin(create_plugin):
    test_pref = {"name": str, "test": True}
    plugin = create_plugin(
        test_pref,
        "test_plugin"
    )
    # check valid plugin and registration
    assert plugin.name == "test_plugin"
    assert plugin.user_pref == test_pref
    assert isinstance(plugin.blueprint(), Blueprint)
    assert "test_plugin" in USER_PREF.keys()
    assert USER_PREF["test_plugin"] == test_pref
    plugin_exists = False
    for obj in PLUGINS:
        if obj is plugin:
            plugin_exists = True
    assert plugin_exists

    # check bp properly registered
    app = create_app({"TESTING": True, })
    routes = [str(p) for p in app.url_map.iter_rules()]
    assert '/api/v2/test_plugin/hello' in routes

    client = app.test_client()
    response = client.get('/api/v2/test_plugin/hello')
    assert response.status_code == 200

    with client:
        response = client.get('/api/v2/session/test_plugin')
        assert response.is_json
        json_data = response.get_json()
        assert test_pref.keys() == json_data.keys()
        assert "test_plugin" in session.keys()
        assert test_pref.keys() == session["test_plugin"].keys()