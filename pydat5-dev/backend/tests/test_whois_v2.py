import pytest
from unittest.mock import MagicMock
from pydat.api.utils import es as elastic
import socket


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

    mock_socket = MagicMock(return_value=("valid", ["v1", "v2"], ["127"]))
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
