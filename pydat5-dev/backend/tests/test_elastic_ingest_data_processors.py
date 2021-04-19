import os
from types import SimpleNamespace
import pytest
from unittest import mock

from pydat.core.elastic.ingest.process_wrapper import PopulatorOptions
from pydat.core.elastic.ingest.data_processors import (
    _generateDocId,
    DataReader
)


def test_generate_doc_id():
    assert _generateDocId("mitre.org") == "org.mitre"

    with pytest.raises(RuntimeError):
        assert _generateDocId(set())

    longdomain = "mitre" * 100 + ".org"
    assert _generateDocId(longdomain) == \
        "org.h.2844603a197e9cbe3dde56e467422d01d1c5ab40"


@pytest.fixture
def fake_data_reader():
    fake_file_queue = mock.Mock()
    fake_data_queue = mock.Mock()
    fake_eventTracker = mock.Mock()
    process_options = PopulatorOptions(
        verbose=True,
        debug=True,
    )

    return DataReader(
        0,
        fake_file_queue,
        fake_data_queue,
        fake_eventTracker,
        process_options
    )


def test_data_reader():
    fake_file_queue = mock.Mock()
    fake_data_queue = mock.Mock()
    fake_eventTracker = mock.Mock()
    process_options = PopulatorOptions(
        verbose=True,
        debug=True,
    )

    assert DataReader(
        0,
        fake_file_queue,
        fake_data_queue,
        fake_eventTracker,
        process_options
    )


def test_data_reader_check_header(fake_data_reader):
    assert fake_data_reader.check_header(
        ['test', 'test', 'test', 'domainName'])
    assert not fake_data_reader.check_header(
        ['test', 'test', 'test', 'test'])


def test_data_reader_parse_csv(monkeypatch, fake_data_reader):
    fake_open = mock.mock_open()
    fake_parse_csv_fn = mock.MagicMock()
    with mock.patch('builtins.open', fake_open):
        fake_stat = mock.Mock(return_value=SimpleNamespace(st_size=100))
        with monkeypatch.context() as monkey:
            monkey.setattr(os, 'stat', fake_stat)
            monkey.setattr(DataReader, "_parse_csv", fake_parse_csv_fn)
            fake_data_reader.parse_csv('testfile.csv')

        fake_stat = mock.Mock(side_effect=Exception())
        with monkeypatch.context() as monkey:
            monkey.setattr(os, 'stat', fake_stat)
            monkey.setattr(DataReader, "_parse_csv", fake_parse_csv_fn)
            fake_data_reader.parse_csv('testfile.csv')

    fake_open = mock.mock_open()
    with mock.patch('builtins.open', fake_open) as mock_file:
        mock_file.side_effect = FileNotFoundError()

        fake_stat = mock.Mock(return_value=SimpleNamespace(st_size=100))
        with monkeypatch.context() as monkey:
            monkey.setattr(os, 'stat', fake_stat)
            monkey.setattr(DataReader, "_parse_csv", fake_parse_csv_fn)
            fake_data_reader.parse_csv('testfile.csv')


def test_data_reader_real_parse_csv(monkeypatch, fake_data_reader, caplog):
    csvdata = [
        "domainName,registrantName",
        "mitre.org,Some Person"
    ]
    fake_data_reader._parse_csv('fakefile', csvdata)

    csvdata = [
        "mitre.org,Some Person"
    ]
    fake_data_reader._parse_csv('fakefile', csvdata)
