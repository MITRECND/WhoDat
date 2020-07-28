from pydat.api import create_app
import pytest
from unittest.mock import patch
from pydat.api.utils import es as elastic
import mock_es

NAMESPACE = 'pydat.api.controller.v1.whoisv1.elastic'


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
@patch(f'{NAMESPACE}.search', side_effect=mock_es.search)
def test_domains(mock_search, config_app, low, high):
    client = config_app.test_client()
    # test valid search keys
    for key in config_app.config['SEARCH_KEYS']:
        response = client.get(f"/api/v1/domains/{key}/fake")
        assert response.status_code == 200
    assert client.get("/api/v1/domains/fake_key/fake").status_code == 400
    assert client.get("/api/v1/domains/fake_key").status_code == 404

    # test valid low/high parameters
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


@patch(f'{NAMESPACE}.search', side_effect=mock_es.diff_search)
def test_domain_diff(mock_search, client):
    assert client.get('/api/v1/domain/test/diff/false/true').status_code == 400
    assert client.get('/api/v1/domain/test/diff/1/true').status_code == 400

    response = client.get('/api/v1/domain/test/diff/1/2')
    assert response.status_code == 404
    assert 'test' in response.get_json()['error']

    response = client.get('/api/v1/domain/greetings/diff/1/3')
    assert response.status_code == 404
    assert 'version' in response.get_json()['error']

    response = client.get('/api/v1/domain/greetings/diff/1/2')
    assert response.status_code == 200
    v1_data = response.get_json()['data']
    response = client.get('/api/v1/domain/greetings/diff/2/1')
    assert response.status_code == 200
    v2_data = response.get_json()['data']
    assert v1_data != v2_data
    assert v1_data.keys() == v2_data.keys()
    # "hello": True, "hi": 1, "goodbye": [-1.1, False], "hola": ["", "spanish"]
    assert v1_data['hola'] == ["", "spanish"]
    assert v2_data['hola'] == ["spanish", ""]
    assert "Version" not in v1_data.keys()
    assert v1_data["hello"] is True
    assert v1_data["hi"] == 1
    assert v1_data['goodbye'] == [-1.1, False]


@pytest.mark.parametrize("version", ("version", -1, 3, 1))
@patch(f'{NAMESPACE}.metadata', side_effect=mock_es.metadata)
def test_metadata(mock_meta, client, version):
    assert client.get('/api/v1/metadata').status_code == 200

    response = client.get(f'/api/v1/metadata/{version}')
    if isinstance(version, int) and version > 0:
        if version == 1:
            assert response.status_code == 200
        else:
            assert response.status_code == 404
    else:
        assert response.status_code == 400


@patch(f'{NAMESPACE}.advanced_search', side_effect=mock_es.query)
def test_query(mock_advanced, client):
    response = client.get("/api/v1/query")
    assert response.status_code == 400

    response = client.get("/api/v1/query",
                          query_string={"query": "query", "size": 20.1})
    assert response.status_code == 400
    response = client.get("/api/v1/query",
                          query_string={"query": "query", "page": 1.1})
    assert response.status_code == 400
    response = client.get("/api/v1/query",
                          query_string={"query": "query", "size": -20})
    assert response.status_code == 400
    response = client.get("/api/v1/query",
                          query_string={"query": "query", "page": -1})
    assert response.status_code == 400

    response = client.get("/api/v1/query",
                          query_string={"query": "query", "unique": True})
    assert response.status_code == 200

    response = client.get("/api/v1/query",
                          query_string={"query": "query", "size": 1000})
    assert response.status_code == 200
    response = client.get("/api/v1/query",
                          query_string={"query": "query", "page": 501})
    assert response.status_code == 400
    assert '501' in response.get_json()['error']


@patch(f'{NAMESPACE}.search', side_effect=elastic.ConnectionError)
@patch(f'{NAMESPACE}.metadata', side_effect=elastic.ConnectionError)
@patch(f'{NAMESPACE}.advanced_search', side_effect=elastic.ConnectionError)
def test_connection_error(mock_advanced, mock_meta, mock_search, config_app):
    client = config_app.test_client()

    # Domains
    response = client.get('/api/v1/domains/domainName/value')
    assert response.status_code == 500
    json_data = response.get_json()
    assert 'connect' in json_data['error']
    response = client.get('/api/v1/domains/domainName/value/1/2')
    assert response.status_code == 500
    response = client.get('/api/v1/domains/domainName/value/latest')
    assert response.status_code == 500

    # Domain
    response = client.get('/api/v1/domain/value')
    assert response.status_code == 500
    response = client.get('/api/v1/domain/value/diff/1/2')
    assert response.status_code == 500

    # Metadata
    response = client.get('/api/v1/metadata')
    assert response.status_code == 500
    response = client.get('/api/v1/metadata/1')
    assert response.status_code == 500

    # Query
    response = client.get('/api/v1/query', query_string={"query": "query"})
    assert response.status_code == 500
