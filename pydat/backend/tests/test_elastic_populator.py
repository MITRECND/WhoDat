from types import SimpleNamespace
import pytest
from unittest import mock
import logging
from pydat.scripts.elasticsearch_populate import (
    generate_parser,
    process_elastic_args,
    process_config_file,
    process_additional_configuration,
)


@pytest.fixture
def populator_config():
    return [
        "--es-uri", "localhost:9200",
        "--es-disable-sniffing",
        "--rollover-size", "100000",
        # "--es-user", None,
        # "--es-password", None,
        # "--es-ca-cert", None,
        # "--es-index-prefix", "pydat",
        "--include", ','.join([
            "registrarName",
            "contactEmail",
            "whoisServer",
            "nameServers",
            "registrant-email",
            "registrant-name",
            "registrant-organization"
        ]),
        # "--ignore-field-prefixes", ','.join([
        #     "zoneContact",
        #     "billingContact",
        #     "technicalContact"
        # ]),
        "--pipelines", "2",
        "--shipper-threads", "1",
        "--fetcher-threads", "2",
        "--bulk-fetch-size", "50",
        "--bulk-ship-size", "10",
        "--verbose",
        "--debug",
        "--debug-level", "1",
        "--stats",
        "--extension", "csv",
        # "--exclude", None
    ]


def test_parser(populator_config):
    parser = generate_parser()
    assert(parser)
    assert(parser.parse_args(populator_config))


def test_parser_elastic_handling(populator_config):
    parser = generate_parser()
    args = parser.parse_args(populator_config)
    (args, elastic) = process_elastic_args(vars(args))
    assert(elastic == {
        "uri": ["localhost:9200"],
        "disable_sniffing": True,
        "rollover_docs": 100000,
    })


def test_config_ingest(monkeypatch):
    mock_open = mock.mock_open(read_data="""---
# Elastic Configuration Options
es:
  uri:
    - localhost:9200
  disable_sniffing: true
  rollover_docs: 500000

# General ingest and processing options
ignore_field_prefixes:
  - zoneContact
  - billingContact
  - technicalContact

# Performance Tuning Options
pipelines: 4
shipper_threads: 2
fetcher_threads: 2
bulk_fetch_size: 50
bulk_ship_size: 10

""")

    with monkeypatch.context() as m:
        m.setattr('builtins.open', mock_open)
        config = process_config_file("foobarfoo")

    assert(config)


@pytest.fixture
def ingest_test_data():
    return SimpleNamespace(
        ingest_day=None,
        redo=False,
        ask_password=False,
        config_template_only=False,
        clear_interrupted=False,
        ingest_file="file",
        ingest_directory=None
    )


def test_additional_config_ingest_day(ingest_test_data, caplog):
    process_additional_configuration(
        ingest_test_data,
        SimpleNamespace(),
        logging.getLogger("test")
    )

    assert("assuming today" in caplog.text)


def test_additional_config_ingest_day_parse_failure_1(
    ingest_test_data,
    caplog
):
    ingest_test_data.ingest_day = "WRONG"

    with pytest.raises(SystemExit):
        process_additional_configuration(
            ingest_test_data,
            SimpleNamespace(),
            logging.getLogger("test")
        )

    assert("ingest_day format is" in caplog.text)


def test_additional_config_ingest_day_parse_failure_2(
    ingest_test_data,
    caplog
):
    ingest_test_data.ingest_day = "2021-00-01"

    with pytest.raises(SystemExit):
        process_additional_configuration(
            ingest_test_data,
            SimpleNamespace(),
            logging.getLogger("test")
        )

    assert("Unable to verify date" in caplog.text)


def test_additional_config_ingest_day_parse_failure_3(
    ingest_test_data,
    caplog
):
    ingest_test_data.ingest_day = "2021-01-32"

    with pytest.raises(SystemExit):
        process_additional_configuration(
            ingest_test_data,
            SimpleNamespace(),
            logging.getLogger("test")
        )

    assert("Unable to verify date" in caplog.text)


def test_additional_config_inges_day_parse_1(ingest_test_data):
    ingest_test_data.ingest_day = "2021-01-00"

    process_additional_configuration(
        ingest_test_data,
        SimpleNamespace(),
        logging.getLogger("test")
    )


def test_additional_config_inges_day_parse_2(ingest_test_data):
    ingest_test_data.ingest_day = "2021-01-01"

    process_additional_configuration(
        ingest_test_data,
        SimpleNamespace(),
        logging.getLogger("test")
    )
