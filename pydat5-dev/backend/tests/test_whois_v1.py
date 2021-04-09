import pytest
from unittest.mock import MagicMock
from pydat.core.elastic.exceptions import (
    ESConnectionError,
    ESQueryError,
    ESNotFoundError
)


@pytest.mark.parametrize("low", ("low", -1, 3, 100, 1, -21))
@pytest.mark.parametrize("high", ("high", -1, 4, 2, 200))
def test_domains(monkeypatch, config_app, low, high, es_handler):
    client = config_app.test_client()
    # search is always valid
    mock_search = MagicMock(return_value={"data": [{
        "test": "output",
        "dataVersion": 99
    }]})
    monkeypatch.setattr(es_handler, 'search', mock_search)

    # test checking valid search keys
    for key in config_app.config['SEARCHKEYS']:
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


def test_latest(monkeypatch, config_app, es_handler):
    # search and lastVersion are always valid
    mock_search = MagicMock(return_value={"data": [{
        "test": "output",
        "dataVersion": 99
    }]})
    mock_last = MagicMock(return_value=1)
    monkeypatch.setattr(es_handler, 'search', mock_search)
    monkeypatch.setattr(es_handler, 'last_version', mock_last)

    client = config_app.test_client()
    for key in config_app.config['SEARCHKEYS']:
        response = client.get(f"/api/v1/domains/{key}/fake/latest")
        assert response.status_code == 200
        response = client.get("/api/v1/domain/fake/latest")
        assert response.status_code == 200

    # error: unable to find last version
    mock_last.side_effect = ESQueryError
    response = client.get("/api/v1/domain/fake/latest")
    assert response.status_code == 500
    response = client.get(f"/api/v1/domains/{key}/fake/latest")
    assert response.status_code == 500


def test_domain_diff(monkeypatch, client, es_handler):
    # type checks independent of search
    assert client.get('/api/v1/domain/test/diff/false/true').status_code == 400
    assert client.get('/api/v1/domain/test/diff/1/true').status_code == 400

    # error: no data for domainName/version
    mock_diff = MagicMock(return_value={'data': []})
    monkeypatch.setattr(es_handler, 'search', mock_diff)
    response = client.get('/api/v1/domain/greetings/diff/3/4')
    assert response.status_code == 404
    assert 'version' in response.get_json()['error']

    # test diff functunality
    v1_res = {"data": [{"hey": True, "hi": 1, "bye": -1.1, "Version": 1}]}
    v2_res = {"data": [{"hey": 1, "hi": 1, "bye": False, "si": "yes"}]}
    mock_diff.side_effect = [v1_res, v2_res, v2_res, v1_res]
    response = client.get('/api/v1/domain/greetings/diff/1/2')
    # ensure call search(low=1) and search(low=2)
    assert mock_diff.call_count == 4
    assert response.status_code == 200
    v1_data = response.get_json()['data']

    response = client.get('/api/v1/domain/greetings/diff/2/1')
    assert response.status_code == 200
    v2_data = response.get_json()['data']
    assert v1_data != v2_data
    assert v1_data.keys() == v2_data.keys()
    assert v1_data == {
        "hey": True,
        "hi": 1,
        "bye": [-1.1, False],
        "si": ["", "yes"]
    }
    assert v2_data['si'] == ["yes", ""]


@pytest.mark.parametrize("version", ("version", -1, 1, 2))
def test_metadata(monkeypatch, client, version, es_handler):
    # metadata is always valid
    mock_meta = MagicMock(return_value=[{"test": "record"}])
    monkeypatch.setattr(es_handler, 'metadata', mock_meta)

    # type checking
    response = client.get(f'/api/v1/metadata/{version}')
    if isinstance(version, int) and version > 0:
        assert response.status_code == 200
    else:
        assert response.status_code == 400


def test_metadata_notfound(monkeypatch, client, es_handler):
    # error: version doesn't exist
    mock_meta = MagicMock(side_effect=ESNotFoundError)
    monkeypatch.setattr(es_handler, 'metadata', mock_meta)

    assert client.get('/api/v1/metadata/1').status_code == 404


def test_query(monkeypatch, client, es_handler):
    # must have query
    response = client.get("/api/v1/query")
    assert response.status_code == 400

    # type checking
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

    # test page specification
    mock_query = MagicMock(return_value={'total': 1000, 'data': []})
    monkeypatch.setattr(es_handler, 'advanced_search', mock_query)
    response = client.get("/api/v1/query",
                          query_string={"query": "query", "size": 1000})
    assert response.status_code == 200
    response = client.get("/api/v1/query",
                          query_string={"query": "query", "page": 501})
    assert response.status_code == 400
    assert '501' in response.get_json()['error']


def test_connection_error(monkeypatch, config_app, es_handler):
    mock_connection = MagicMock(side_effect=ESConnectionError)
    client = config_app.test_client()

    # search connection error
    monkeypatch.setattr(es_handler, 'search', mock_connection)
    with pytest.raises(ESConnectionError):
        assert es_handler.search()
    # Domains
    response = client.get('/api/v1/domains/domainName/value')
    assert response.status_code == 500
    response = client.get('/api/v1/domains/domainName/value/1/2')
    assert response.status_code == 500
    response = client.get('/api/v1/domains/domainName/value/latest')
    assert response.status_code == 500
    # Domain
    response = client.get('/api/v1/domain/value')
    assert response.status_code == 500
    response = client.get('/api/v1/domain/value/diff/1/2')
    assert response.status_code == 500

    monkeypatch.setattr(es_handler, 'metadata', mock_connection)
    with pytest.raises(ESConnectionError):
        assert es_handler.metadata()
    # Metadata
    response = client.get('/api/v1/metadata')
    assert response.status_code == 500
    response = client.get('/api/v1/metadata/1')
    assert response.status_code == 500

    monkeypatch.setattr(es_handler, 'advanced_search', mock_connection)
    with pytest.raises(ESConnectionError):
        assert es_handler.advanced_search()
    # Query
    response = client.get('/api/v1/query', query_string={"query": "query"})
    assert response.status_code == 500
