import pytest
from unittest.mock import MagicMock
from pydat.api.utils import es as elastic
import socket


# identical code to testing metadata v1 (shared)
@pytest.mark.parametrize("version", ("version", -1, 1))
def test_metadata(monkeypatch, client, version):
    # metadata is always valid
    mock_meta = MagicMock(return_value="success")
    monkeypatch.setattr(elastic, "metadata", mock_meta)

    # type checking
    response = client.get(f"/api/v2/metadata/{version}")
    if isinstance(version, int) and version > 0:
        assert response.status_code == 200
    else:
        assert response.status_code == 400

    # error: versioin doesn't exist
    mock_meta.side_effect = elastic.NotFoundError
    with pytest.raises(elastic.NotFoundError):
        assert elastic.metadata()
    assert client.get("/api/v2/metadata/1").status_code == 404


def test_resolve(monkeypatch, client):
    response = client.get("/api/v2/resolve")
    assert response.status_code == 404

    mock_socket = MagicMock(return_value=("valid", ["v2", "v2"], ["127"]))
    monkeypatch.setattr(socket, "gethostbyname_ex", mock_socket)
    response = client.get("/api/v2/resolve/test")
    assert response.status_code == 200
    assert mock_socket.called

    mock_socket.side_effect = socket.gaierror
    response = client.get("/api/v2/resolve/test")
    assert response.status_code == 400

    mock_socket.side_effect = socket.timeout
    response = client.get("/api/v2/resolve/test")
    assert response.status_code == 504


@pytest.mark.parametrize("version", ("version", -1, 3, 100, 1.2, -0.1))
def test_domains(monkeypatch, config_app, version):
    client = config_app.test_client()
    # search is always valid
    mock_search = MagicMock(return_value={"total": 100, "data": [0] * 100})
    monkeypatch.setattr(elastic, "search", mock_search)

    # test checking valid search keys
    for key in config_app.config["SEARCH_KEYS"]:
        response = client.post(
            f"/api/v2/domains/{key}", json={"value": "value"}
        )
        assert response.status_code == 200
    # required value not provided
    assert client.post("/api/v2/domains/domainName").status_code == 400
    # invalid search key
    assert (
        client.post(
            "/api/v2/domains/fake_key", json={"value": "value"}
        ).status_code
        == 400
    )

    # test valid version
    response = client.post(
        "/api/v2/domains/domainName",
        json={"value": "fake", "version": f"{version}"},
    )
    try:
        version = int(version)
        assert response.status_code == 200
    except ValueError:
        assert response.status_code == 400

    # test offset/chunk_size
    response = client.post(
        "/api/v2/domains/domainName", json={"value": "value"}
    )
    assert response.is_json
    json_data = response.get_json()
    assert json_data["total"] == mock_search.return_value["total"]
    assert json_data["results"] == mock_search.return_value["data"]
    response = client.post(
        "/api/v2/domains/domainName",
        json={
            "value": "value",
            "chunk_size": mock_search.return_value["total"] + 1,
        },
    )
    json_data = response.get_json()
    assert json_data["total"] == mock_search.return_value["total"]
    response = client.post(
        "/api/v2/domains/domainName",
        json={
            "value": "value",
            "chunk_size": mock_search.return_value["total"] / 5,
            "offset": 6,
        },
    )
    assert response.status_code == 400

    mock_search.return_value["total"] = 0
    mock_search.return_value["data"] = []
    response = client.post(
        "/api/v2/domains/domainName", json={"value": "value", "chunk_size": 40}
    )
    assert response.status_code == 200
    assert response.get_json()["results"] == []
    response = client.post(
        "/api/v2/domains/domainName", json={"value": "value", "chunk_size": 0}
    )
    assert response.status_code == 400


def test_domains_diff(monkeypatch, config_app):
    client = config_app.test_client()

    mock_diff = MagicMock(return_value={"data": [{"success": 1}]})
    monkeypatch.setattr(elastic, "search", mock_diff)
    # required parameters
    response = client.post("/api/v2/domains/diff", json={})
    assert response.status_code == 400
    response = client.post("/api/v2/domains/diff", json={"domain": "value"})
    assert response.status_code == 400
    response = client.post(
        "/api/v2/domains/diff", json={"domain": "value", "version1": 0}
    )
    assert response.status_code == 400
    response = client.post(
        "/api/v2/domains/diff",
        json={"domain": "value", "version1": 0, "version2": 1},
    )
    assert response.status_code == 200

    # diff functionality is equivalent to v1


def test_query(monkeypatch, config_app):
    client = config_app.test_client()

    mock_adv = MagicMock(return_value={"total": 100, "data": []})
    monkeypatch.setattr(elastic, "advanced_search", mock_adv)

    response = client.post("/api/v2/query")
    assert response.status_code == 400
    response = client.post("/api/v2/query", json={"query": "query"})
    assert response.status_code == 200
    # valid sort key
    response = client.post(
        "/api/v2/query", json={"query": "query", "sort_key": "domainName"}
    )
    assert response.status_code == 200
    response = client.post(
        "/api/v2/query", json={"query": "query", "sort_key": "fake_key"}
    )
    assert response.status_code == 400
    response = client.post(
        "/api/v2/query",
        json={
            "query": "query",
            "chunk_size": mock_adv.return_value["total"] / 5,
            "offset": 6,
        },
    )
    assert response.status_code == 400
    response = client.post(
        "/api/v2/query",
        json={
            "query": "query",
            "chunk_size": mock_adv.return_value["total"] / 5.0,
            "offset": 4,
        },
    )
    assert response.status_code == 400

    mock_adv.side_effect = elastic.SearchError
    response = client.post("/api/v2/query", json={"query": "query"})
    assert response.status_code == 400


def test_connection_error(monkeypatch, config_app):
    mock_connection = MagicMock(side_effect=elastic.ConnectionError)
    client = config_app.test_client()

    # search connection error
    monkeypatch.setattr(elastic, "search", mock_connection)
    with pytest.raises(elastic.ConnectionError):
        assert elastic.search()
    # Domains
    response = client.post(
        "/api/v2/domains/domainName", json={"value": "value"}
    )
    assert response.status_code == 500
    response = client.post(
        "/api/v2/domains/diff",
        json={"domain": "value", "version1": 0, "version2": 1},
    )
    assert response.status_code == 500

    monkeypatch.setattr(elastic, "metadata", mock_connection)
    with pytest.raises(elastic.ConnectionError):
        assert elastic.metadata()
    # Metadata
    response = client.get("/api/v2/metadata")
    assert response.status_code == 500
    response = client.get("/api/v2/metadata/1")
    assert response.status_code == 500

    monkeypatch.setattr(elastic, "advanced_search", mock_connection)
    with pytest.raises(elastic.ConnectionError):
        assert elastic.advanced_search()
    # Query
    response = client.post("/api/v2/query", json={"query": "query"})
    assert response.status_code == 500
