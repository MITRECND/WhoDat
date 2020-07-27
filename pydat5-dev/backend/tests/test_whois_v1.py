from pydat.api import create_app
import pytest


@pytest.fixture
def config_app():
    app = create_app(
        {
            "TESTING": True,
            "SEARCH_KEYS": ['domainName', 'registrant_name',
                            'contactEmail', 'registrant_telephone'],
            'LIMIT': 100, })
    return app


@pytest.mark.parametrize("low", ("low", -1, 3, 100, 1.2, -.1))
@pytest.mark.parametrize("high", ("high", -1.2, 4.6, 2, 200))
def test_domains(config_app, low, high):
    client = config_app.test_client()
    for key in config_app.config['SEARCH_KEYS']:
        response = client.get(f"/api/v1/domains/{key}/fake")
        assert response.status_code == 200
    assert client.get("/api/v1/domains/fake_key/fake").status_code == 400
    assert client.get("/api/v1/domains/fake_key").status_code == 404

    response = client.get(f"/api/v1/domains/domainName/fake/{low}")
    if (isinstance(low, float) or isinstance(low, int)) and low > 0:
        assert response.status_code == 200
    else:
        assert response.status_code == 400
    response = client.get(f"/api/v1/domains/domainName/fake/{low}/{high}")
    if (isinstance(low, float) or isinstance(low, int)) \
        and (isinstance(high, float) or isinstance(high, int)) \
            and low < high and low > 0:
        assert response.status_code == 200
    else:
        assert response.status_code == 400


def test_latest(config_app):
    client = config_app.test_client()
    for key in config_app.config['SEARCH_KEYS']:
        response = client.get(f"/api/v1/domains/{key}/fake/latest")
        assert response.status_code == 200
        response = client.get("/api/v1/domain/fake/latest")
        assert response.status_code == 200


def test_domain_diff(client):
    assert client.get('/api/v1/domain/test/diff/false/true').status_code == 400


@pytest.mark.parametrize("version", ("version", -1, 3, 1.2))
def test_metadata(client, version):
    assert client.get('/api/v1/metadata').status_code == 200

    response = client.get(f'/api/v1/metadata/{version}')
    if isinstance(version, int) and version > 0:
        assert response.status_code == 200
    else:
        assert response.status_code == 400


def test_query(client):
    response = client.get("/api/v1/query")
    assert response.status_code == 400

    response = client.get("/api/v1/query",
                          query_string={"query": "query", "size": 20.1})
    assert response.status_code == 400

    response = client.get("/api/v1/query",
                          query_string={"query": "query", "page": 1.1})
    assert response.status_code == 400

    response = client.get("/api/v1/query",
                          query_string={"query": "query", "unique": True})
    assert response.status_code == 200
