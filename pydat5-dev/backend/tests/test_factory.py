from pydat.api import create_app


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
