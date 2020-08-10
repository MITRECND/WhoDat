from pydat.core import preferences
from flask import session
import pytest


# global is required to be in USER_PREF
def test_global(client):
    response = client.get("/api/v2/session/global")
    assert response.status_code == 404


# helper method for _put_get, _patch
# checks PUT/PATCH validation methods for parameter-values
def check_invalid(json_data, param_pref, type_pref):
    for param in session["fake_endpoint"].keys():
        assert session["fake_endpoint"][param] is None

    # check shared is_valid and get_valid_param of PUT/PATCH
    error_mes = ' '.join(json_data['error'])
    for param in param_pref.keys():
        if param not in session["fake_endpoint"].keys():
            assert f'Nonexistant parameter {param}' in error_mes
        elif not isinstance(param_pref[param], type_pref[param]):
            assert (
                f'Type mismatch of {type(param_pref[param])} ' +
                f'and {type_pref[param]} for {param}'
            )
        else:
            assert param not in error_mes


@pytest.mark.parametrize("type_pref", (
    {}, {"name": str}, {"pi": float, "dev": bool},
    {"name": str, "pi": float, "id": int}
))
@pytest.mark.parametrize("param_pref", (
    {}, {"name": "test"}, {"name": 123, "pi": 123, "id": 1},
    {"pi": 3.1415, "dev": True}
))
def test_put_get(client, type_pref, param_pref):
    # attempt to put when preference does not exist
    response = client.put(
        '/api/v2/session/fake_endpoint',
        json=param_pref
    )
    assert response.status_code == 404
    assert response.is_json
    assert 'fake_endpoint' in response.get_json()['error']

    # set preferences and check get, session[fake] is created
    preferences.add_user_pref('fake_endpoint', type_pref)
    with client:
        response = client.get('/api/v2/session/fake_endpoint')
        assert response.status_code == 200
        assert response.is_json
        json_data = response.get_json()
        for param in json_data.keys():
            assert json_data[param] is None
        assert session.get('fake_endpoint') is not None
        assert type_pref.keys() == session['fake_endpoint'].keys()

    # try putting in param_pref data
    with client:
        response = client.put(
            '/api/v2/session/fake_endpoint',
            json=param_pref
        )
        # must exist now
        assert response.status_code != 404
        assert response.is_json

        if response.status_code == 200:
            # check valid status code
            assert len(param_pref) == len(type_pref)
            assert param_pref.keys() == type_pref.keys()
            for param in param_pref.keys():
                assert isinstance(param_pref[param], type_pref[param])
            # check valid put
            assert param_pref == session["fake_endpoint"]

        if response.status_code == 400:
            json_data = response.get_json()
            # PUT specific check
            if len(type_pref) != len(param_pref):
                assert "Expected" in json_data['error']
            else:
                check_invalid(json_data, param_pref, type_pref)

    # cleanup
    preferences.USER_PREF.pop("fake_endpoint")


@pytest.mark.parametrize("type_pref", (
    {}, {"name": str}, {"pi": float, "dev": bool},
    {"name": str, "pi": float, "id": int}
))
@pytest.mark.parametrize("param_pref", (
    {}, {"name": "test"}, {"name": 123, "pi": 123, "id": 1},
    {"pi": 3.1415, "dev": True}
))
def test_patch(client, type_pref, param_pref):
    preferences.add_user_pref('fake_endpoint', type_pref)
    with client:
        response = client.patch(
            '/api/v2/session/fake_endpoint',
            json=param_pref)

        assert response.status_code != 404
        assert response.is_json
        if response.status_code == 200:
            for param in param_pref.keys():
                assert isinstance(param_pref[param], type_pref[param])
                assert session["fake_endpoint"][param] == param_pref[param]
        if response.status_code == 400:
            check_invalid(response.get_json(), param_pref, type_pref)

    # cleanup
    preferences.USER_PREF.pop("fake_endpoint")
