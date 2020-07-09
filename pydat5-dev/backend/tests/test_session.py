from pydat.core.plugins import USER_PREF
from flask import session


# global is required to be in USER_PREF
def test_global(client):
    response = client.get("/api/v2/session/global")
    assert response.status_code == 200


test_point = "teapot"


def test_put(client):
    response = client.put(
        f'/api/v2/session/{test_point}',
        json={
            'pi': 3.1415, 'name': test_point, 'development': True
        })
    assert response.status_code == 404
    assert b'Nonexistant preferences' in response.data

    USER_PREF[test_point] = {
            'pi': float, 'name': str, 'development': bool
        }
    with client:
        response = client.get(f'/api/v2/session/{test_point}')
        json_data = response.get_json()
        for param in json_data.keys():
            assert json_data[param] is None
        assert session.get(test_point) is not None
        assert 'pi' in session[test_point].keys()

    with client:
        response = client.put(
            f'/api/v2/session/{test_point}',
            json={
                'pi': 3.1415, 'name': test_point
            })
        assert response.status_code == 400
        json_data = response.get_json()
        assert "Expected" in json_data['message']
        assert session[test_point]["pi"] is None

    with client:
        response = client.put(
            f'/api/v2/session/{test_point}',
            json={
                'pi': 3.1415, 'name': test_point, 'development': True
            })
        assert response.status_code == 200
        json_data = response.get_json()
        assert session[test_point]["pi"] == 3.1415


def test_patch(client):
    USER_PREF[test_point] = {
            'pi': float, 'name': str, 'development': bool
        }
    with client:
        response = client.patch(
            f'/api/v2/session/{test_point}',
            json={
                'pi': 3.1415, 'name': test_point, 'development': 1
            })
        assert response.status_code == 400
        assert session[test_point]["pi"] == 3.1415
        assert session[test_point]["development"] is None
