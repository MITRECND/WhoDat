from pydat.api import preferences_manager
from pydat.core.preferences import UserPreference
from flask import session
import pytest


def test_pref_not_exist(client):
    # attempt to put when preference does not exist
    response = client.patch(
        '/api/v2/session/fake_endpoint',
        json={'test': 'data'}
    )
    assert response.status_code == 404
    assert response.is_json
    assert 'fake_endpoint' in response.get_json()['error']


@pytest.mark.parametrize("type_pref", (
    [],
    [UserPreference("name", str)],
    [UserPreference("pi", float), UserPreference("dev", bool)],
    [UserPreference("name", str),
     UserPreference("pi",  float),
     UserPreference("id", int)]
))
@pytest.mark.parametrize("param_pref", (
    {},
    {"name": "test"},
    {"name": 123, "pi": 123, "id": 1},
    {"pi": 3.1415, "dev": True}
))
def test_get(client, type_pref, param_pref):
    # set preferences and check get, session[fake] is created

    with client:
        for pref in type_pref:
            preferences_manager.add_preference('fake_endpoint', pref)

        response = client.get('/api/v2/session/fake_endpoint')
        if len(type_pref) == 0:
            assert response.status_code == 404
        else:
            assert response.status_code == 200
            assert response.is_json
            json_data = response.get_json()
            for param in json_data.keys():
                assert json_data[param] is None
            assert session.get('fake_endpoint') is not None
            assert preferences_manager.get_preferences(
                'fake_endpoint').keys() == session['fake_endpoint'].keys()


@pytest.mark.parametrize("type_pref", (
    [UserPreference("name", str)],
    [UserPreference("pi", float), UserPreference("dev", bool)],
    [UserPreference("name", str),
     UserPreference("pi",  float),
     UserPreference("id", int)]
))
@pytest.mark.parametrize("param_pref", (
    {},
    {"name": "test"},
    {"name": 123, "pi": 123, "id": 1},
    {"pi": 3.1415, "dev": True}
))
def test_patch(client, type_pref, param_pref):
    with client:
        for pref in type_pref:
            preferences_manager.add_preference('fake_endpoint', pref)

        response = client.patch(
            '/api/v2/session/fake_endpoint',
            json=param_pref)

        assert response.status_code != 404
        assert response.is_json

        if response.status_code == 200:
            for param in param_pref.keys():
                assert session["fake_endpoint"][param] == param_pref[param]
