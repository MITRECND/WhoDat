import pytest
from unittest import mock
from pydat.core.elastic import ElasticHandler
import elasticsearch


def test_handler():
    elastic_handler = ElasticHandler(
        "localhost:9200",
        indexPrefix="testing"
    )
    assert elastic_handler
    assert elastic_handler.indexNames.prefix == "testing"


def test_handler_security_args():
    with pytest.raises(ValueError):
        ElasticHandler("localhost:9200", username="foo")

    elastic_handler = ElasticHandler("localhost:9200", cacert="test")
    assert elastic_handler.elastic_args["use_ssl"]
    assert elastic_handler.elastic_args["ca_certs"] == "test"


def test_get_version(monkeypatch):
    fake_connect = mock.Mock()
    fake_connect.return_value.cat.nodes.return_value = "7.0\n7.10\n"

    elastic_handler = ElasticHandler("localhost:9200")
    monkeypatch.setattr(elastic_handler, "connect", fake_connect)
    assert elastic_handler.getVersion() == 7


def test_get_version_old(monkeypatch):
    fake_connect = mock.Mock()
    fake_connect.return_value.cat.nodes.return_value = "6.7\n6.8\n"

    elastic_handler = ElasticHandler("localhost:9200")
    monkeypatch.setattr(elastic_handler, "connect", fake_connect)
    with pytest.raises(ValueError):
        elastic_handler.getVersion()


def test_check_version(monkeypatch):
    fake_get_version = mock.MagicMock(return_value="7")
    elastic_handler = ElasticHandler("localhost:9200")
    monkeypatch.setattr(elastic_handler, "getVersion", fake_get_version)

    with monkeypatch.context() as monkey:
        monkey.setattr(elasticsearch, 'VERSION', ["7", "0"])
        elastic_handler.checkVersion()

    with monkeypatch.context() as monkey:
        monkey.setattr(elasticsearch, 'VERSION', ["6", "0"])
        with pytest.raises(RuntimeError):
            elastic_handler.checkVersion()
