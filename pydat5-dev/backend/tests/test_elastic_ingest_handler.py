import pytest
from unittest import mock
from pydat.core.elastic.ingest.ingest_handler import IngestHandler
import elasticsearch


@pytest.fixture
def mock_handler(monkeypatch):
    fake_connect = mock.MagicMock()
    ingest_handler = IngestHandler(hosts="localhost:9200")
    monkeypatch.setattr(ingest_handler, "connect", fake_connect)

    return ingest_handler


def test_template_fn(mock_handler):
    mock_handler.connect.return_value.indices.get_template.return_value = \
        {}

    assert mock_handler.templateExists

    mock_handler.connect.return_value.indices.get_template.side_effect = \
        elasticsearch.exceptions.NotFoundError

    assert not mock_handler.templateExists


def test_metaexists_fn(mock_handler):
    mock_handler.connect.return_value.indices.exists.return_value = \
        True

    assert mock_handler.metaExists

    mock_handler.connect.return_value.indices.exists.return_value = \
        False

    assert not mock_handler.metaExists


def test_metarecord_fn(mock_handler):
    mock_handler.connect.return_value.get.return_value = {
        'found': True,
        '_source': {}
    }

    assert mock_handler.metaRecord == {}

    mock_handler.connect.return_value.get.return_value = {
        'found': False,
        '_source': {}
    }

    assert mock_handler.metaRecord is None

    mock_handler.connect.return_value.get.side_effect = Exception()

    with pytest.raises(RuntimeError):
        mock_handler.metaRecord


def test_getmetadata_fn(mock_handler):
    mock_handler.connect.return_value.get.return_value = {
        'test': 'record',
        '_source': {}
        }
    assert mock_handler.getMetadata(1) == {}

    mock_handler.connect.return_value.get.side_effect = Exception()
    with pytest.raises(RuntimeError):
        mock_handler.getMetadata(1)
