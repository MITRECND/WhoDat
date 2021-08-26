#!/usr/bin/env python

import sys
import yaml
import datetime
import argparse
import getpass
import logging
from types import SimpleNamespace
from logging import StreamHandler

import cerberus

from pydat.core.elastic.ingest import (
    DataPopulator,
    InterruptedImportError,
    NoDataError,
    MetadataError,
)
from pydat.core.elastic.ingest.debug_levels import DebugLevel


# ---------------- cerberus configuration schema objects -------------------
ELASTIC_SCHEMA = {
    "uri": {
        "type": "list",
        "schema": {"type": "string"},
        "default": ["localhost:9200"],
    },
    "user": {
        "type": "string",
        "nullable": True,
        "default": None
    },
    "password": {
        "type": "string",
        "nullable": True,
        "default": None
    },
    "ca_cert": {
        "type": "string",
        "nullable": True,
        "default": None
    },
    "disable_sniffing": {
        "type": "boolean",
        "default": False
    },
    "index_prefix": {
        "type": "string",
        "default": "pydat"
    },
    "rollover_docs": {
        "type": "integer",
        "default": 50000000
    },
}

CONFIG_SCHEMA = {
    # general
    "debug": {
        "type": "boolean",
        "default": False
    },
    "debug_level": {
        "type": "integer",
        "min": 0,
        "max": 3,
        "default": 1
    },
    "verbose": {
        "type": "boolean",
        "default": False
    },
    "stats": {
        "type": "boolean",
        "default": False
    },
    "extension": {
        "type": "string",
        "default": "csv"
    },
    # data populator
    "include": {
        "type": "list",
        "nullable": True,
        "default": None,
        "schema": {"type": "string"},
    },
    "exclude": {
        "type": "list",
        "nullable": True,
        "default": None,
        "schema": {"type": "string"},
    },
    "ignore_field_prefixes": {
        "type": "list",
        "nullable": True,
        "default": None,
        "schema": {"type": "string"},
    },
    # performance
    "pipelines": {
        "type": "integer",
        "default": 2
    },
    "shipper_threads": {
        "type": "integer",
        "default": 2
    },
    "fetcher_threads": {
        "type": "integer",
        "default": 2
    },
    "bulk_fetch_size": {
        "type": "integer",
        "default": 50
    },
    "bulk_ship_size": {
        "type": "integer",
        "default": 10
    },
    # elastic
    "es": {
        "type": "dict",
        "schema": ELASTIC_SCHEMA
    },
}


def generate_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        dest="config",
        default=argparse.SUPPRESS,
        help=(
            "location of configuration file for environment"
            "parameter configuration (example yaml file in /backend)"
        ),
    )

    # Config File Options
    parser.add_argument(
        "--debug",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Enables debug logging"
    )

    parser.add_argument(
        "--debug-level",
        dest="debug_level",
        default=argparse.SUPPRESS,
        type=int,
        help="Debug logging level [0-3] (default: 1)",
    )

    parser.add_argument(
        "-x",
        "--exclude",
        nargs="+",
        type=str,
        default=argparse.SUPPRESS,
        dest="exclude",
        help="list of keys to exclude if updating entry",
    )

    parser.add_argument(
        "-n",
        "--include",
        nargs="+",
        type=str,
        default=argparse.SUPPRESS,
        dest="include",
        help=(
            "list of keys to include if updating entry "
            "(mutually exclusive to -x)"
        ),
    )

    parser.add_argument(
        "--ignore-field-prefixes",
        nargs="*",
        type=str,
        default=argparse.SUPPRESS,
        dest="ignore_field_prefixes",
        help=(
            "list of fields (in whois data) to ignore when "
            "extracting and inserting into ElasticSearch"
        ),
    )

    parser.add_argument(
        "-e",
        "--extension",
        default=argparse.SUPPRESS,
        dest="extension",
        help=(
            "When scanning for CSV files only parse files with given "
            "extension (default: csv)"
        ),
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=argparse.SUPPRESS,
        dest="verbose",
        help="Be verbose",
    )

    parser.add_argument(
        "-s",
        "--stats",
        action="store_true",
        dest="stats",
        default=argparse.SUPPRESS,
        help="Print out Stats after running"
    )

    # Performance Related Options
    performance = parser.add_argument_group("Performance Options")

    performance.add_argument(
        "--pipelines",
        action="store",
        type=int,
        default=argparse.SUPPRESS,
        metavar="PIPELINES",
        dest="pipelines",
        help="Number of pipelines (default: 2)",
    )

    performance.add_argument(
        "--shipper-threads",
        action="store",
        dest="shipper_threads",
        type=int,
        default=argparse.SUPPRESS,
        help=(
            "How many threads per pipeline to spawn to send bulk ES messages."
            " The larger your cluster, the more you can increase this, "
            "defaults to 1"
        ),
    )

    performance.add_argument(
        "--fetcher-threads",
        action="store",
        dest="fetcher_threads",
        type=int,
        default=argparse.SUPPRESS,
        help=(
            "How many threads to spawn to search ES. The larger your cluster,"
            " the more you can increase this, defaults to 2"
        ),
    )

    performance.add_argument(
        "--bulk-ship-size",
        type=int,
        dest="bulk_ship_size",
        default=argparse.SUPPRESS,
        help="Size of Bulk Elasticsearch Requests (default: 10)"
    )

    performance.add_argument(
        "--bulk-fetch-size",
        type=int,
        dest="bulk_fetch_size",
        default=argparse.SUPPRESS,
        help=(
            "Number of documents to search for at a time (default: 50), "
            "note that this will be multiplied by the number of indices you "
            "have, e.g., if you have 10 pydat-<number> indices it results "
            "in a request for 500 documents"
         )
     )

    # Elastic-related options
    elastic_options = parser.add_argument_group("Elasticsearch Options")

    # Elastic Config File Options
    elastic_options.add_argument(
        "-u",
        "--es-uri",
        nargs="*",
        default=argparse.SUPPRESS,
        dest="es_uri",
        help=(
            "Location(s) of ElasticSearch Server (e.g., foo.server.com:9200)"
            " Can take multiple endpoints"
        ),
    )

    elastic_options.add_argument(
        "--es-user",
        default=argparse.SUPPRESS,
        dest="es_user",
        help="Username for ElasticSearch when Basic Auth is enabled",
    )

    elastic_options.add_argument(
        "--es-pass",
        default=argparse.SUPPRESS,
        dest="es_password",
        help="Password for ElasticSearch when Basic Auth is enabled",
    )

    elastic_options.add_argument(
        "--cacert",
        dest="es_ca_cert",
        default=argparse.SUPPRESS,
        help="Path to a CA Certicate bundle to enable https support"
    )

    elastic_options.add_argument(
        "--es-disable-sniffing",
        action="store_true",
        dest="es_disable_sniffing",
        default=argparse.SUPPRESS,
        help=(
            "Disable ES sniffing, useful when ssl hostname"
            "verification is not working properly"
        ),
    )

    elastic_options.add_argument(
        "-p",
        "--index-prefix",
        dest="es_index_prefix",
        default=argparse.SUPPRESS,
        help="Index prefix to use in ElasticSearch (default: pydat)",
    )

    elastic_options.add_argument(
        "--rollover-size",
        type=int,
        default=argparse.SUPPRESS,
        dest="es_rollover_docs",
        help=(
            "Set the number of documents after which point a new index "
            "should be created, defaults to 50 million, note that this "
            "is fuzzy since the index count isn't continuously updated, "
            "so should be reasonably below 2 billion per ES shard and should"
            " take your ES configuration into consideration"
        ),
    )

    # Elastic Command Line Only Options
    elastic_options.add_argument(
        "--ask-pass",
        action="store_true",
        dest="ask_password",
        help="Prompt for ElasticSearch password",
        default=False
    )

    runmode = parser.add_mutually_exclusive_group()
    # Command Line Only Options
    runmode.add_argument(
        "-r",
        "--redo",
        action="store_true",
        dest="redo",
        default=False,
        help=(
            "Attempt to re-import a failed import or import more data, "
            "uses stored metadata from previous run"
        ),
    )

    runmode.add_argument(
        "--config-template-only",
        action="store_true",
        default=False,
        dest="config_template_only",
        help="Configure the ElasticSearch template and then exit",
    )

    runmode.add_argument(
        "--clear-interrupted-flag",
        action="store_true",
        default=False,
        dest="clear_interrupted",
        help="Clear the interrupted flag, forcefully (NOT RECOMMENDED)",
    )

    input_source = parser.add_mutually_exclusive_group()

    input_source.add_argument(
        "-f",
        "--file",
        default=None,
        dest="ingest_file",
        help="Input CSV file"
    )

    input_source.add_argument(
        "-d",
        "--directory",
        default=None,
        dest="ingest_directory",
        help=(
            "Directory to recursively search for CSV files -- mutually"
            " exclusive to '-f' option"
        ),
    )

    parser.add_argument(
        "-D",
        "--ingest-day",
        action="store",
        default=None,
        dest="ingest_day",
        help=(
            "Day to use for metadata, in the format 'YYYY-MM-dd', e.g.,"
            " '2021-01-01'. Defaults to todays date, use 'YYYY-MM-00' to "
            "indicate a quarterly ingest, e.g., 2021-04-00"
        ),
    )

    parser.add_argument(
        "-o",
        "--comment",
        default=None,
        dest="comment",
        help="Comment to store with metadata",
    )

    return parser


def process_elastic_args(args):
    out_args = {}
    elastic_args = {}
    for (name, val) in args.items():
        if name.startswith('es_'):
            elastic_args[name[3:]] = val
        else:
            out_args[name] = val

    return (out_args, elastic_args)


def process_config_file(config_filename):
    with open(config_filename, "r") as c:
        config = yaml.safe_load(c)

    validator = cerberus.Validator(CONFIG_SCHEMA)
    if not validator.validate(config):
        raise ValueError(validator.errors)

    return validator.normalized(config)


def process_config(args, elastic_args):
    config = args
    elastic_config = elastic_args

    if "config" in args:
        config_filename = args.pop("config")

        try:
            config_file = process_config_file(config_filename)
        except ValueError as e:
            print(f"unable to parse configuration file: {str(e)}")
            exit(1)

        elastic_config = {**config_file.pop("es", {}), **elastic_args}
        config = {**config_file, **args}

    configuration = SimpleNamespace(**config)
    elastic_configuration = SimpleNamespace(**elastic_config)

    return (configuration, elastic_configuration)


def setup_logging(configuration):
    if configuration.debug:
        configuration.debug = DebugLevel(configuration.debug_level)
    else:
        configuration.debug = DebugLevel.DISABLED

    # Setup Logging
    debug_level = logging.DEBUG
    root_debug_level = logging.WARNING
    default_level = logging.INFO
    root_default_level = logging.WARNING

    try:
        log_handler = StreamHandler(sys.stdout)
    except Exception as e:
        print(f"Unable to setup logger to stdout\nError Message: {str(e)}\n")
        sys.exit(1)

    if configuration.debug:
        log_format = (
            "%(levelname) -10s %(asctime)s %(name) -15s %(funcName) "
            "-20s %(lineno) -5d: %(message)s"
        )
    else:
        log_format = "%(message)s"

    log_formatter = logging.Formatter(log_format)

    # Set defaults for all loggers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    log_handler.setFormatter(log_formatter)
    root_logger.addHandler(log_handler)
    logger = logging.getLogger(__name__)

    if configuration.debug:
        root_logger.setLevel(root_debug_level)
        logger.setLevel(debug_level)
    else:
        root_logger.setLevel(root_default_level)
        logger.setLevel(default_level)

    return logger


def process_additional_configuration(
    configuration,
    elastic_configuration,
    logger
):
    if configuration.ingest_day is not None:
        ingest_parts = configuration.ingest_day.strip().rstrip().split("-")
        if len(ingest_parts) != 3:
            logger.error("D/ingest_day format is 'YYYY-MM-dd'")
            sys.exit(1)

        if ingest_parts[2] == "00":
            ingest_parts[2] = 1

        try:
            datetime.date(
                int(ingest_parts[0]),
                int(ingest_parts[1]),
                int(ingest_parts[2]),
            )
        except ValueError:
            logger.error("Unable to verify date provided")
            sys.exit(1)
    elif not configuration.redo:
        logger.warning("Ingest Day was not provided, assuming today")

    if configuration.ask_password:
        try:
            elastic_configuration.password = getpass.getpass(
                "Enter ElasticSearch Password: "
            )
        except Exception:
            # TODO FIXME add better handling
            print("Unable to get password", file=sys.stderr)
            sys.exit(1)

    if not any([
        configuration.redo,
        configuration.config_template_only,
        configuration.clear_interrupted
    ]) and not any([
        configuration.ingest_file,
        configuration.ingest_directory
    ]):
        logger.error("Ingest File or Directory is required")
        sys.exit(1)


def main():
    parsed_args = generate_parser().parse_args()
    (args, elastic_args) = process_elastic_args(vars(parsed_args))
    (configuration, elastic_configuration) = process_config(args, elastic_args)

    logger = setup_logging(configuration)
    process_additional_configuration(
        configuration,
        elastic_configuration,
        logger
    )

    elastic_arguments = {
        "hosts": elastic_configuration.uri,
        "username": elastic_configuration.user,
        "password": elastic_configuration.password,
        "cacert": elastic_configuration.ca_cert,
        "disable_sniffing": elastic_configuration.disable_sniffing,
        "indexPrefix": elastic_configuration.index_prefix,
        "rollover_size": elastic_configuration.rollover_docs,
    }

    data_populator = DataPopulator(
        elastic_args=elastic_arguments,
        include_fields=configuration.include,
        exclude_fields=configuration.exclude,
        ingest_day=configuration.ingest_day,
        ignore_field_prefixes=configuration.ignore_field_prefixes,
        pipelines=configuration.pipelines,
        ingest_directory=configuration.ingest_directory,
        ingest_file=configuration.ingest_file,
        extension=configuration.extension,
        comment=configuration.comment,
        bulk_fetch_size=configuration.bulk_fetch_size,
        bulk_ship_size=configuration.bulk_ship_size,
        num_shipper_threads=configuration.shipper_threads,
        num_fetcher_threads=configuration.fetcher_threads,
        verbose=configuration.verbose,
        debug=configuration.debug,
    )

    if configuration.config_template_only:
        data_populator.configTemplate()
        sys.exit(0)

    if configuration.clear_interrupted:
        data_populator.clearInterrupted()
        sys.exit(0)

    try:
        if not configuration.redo:
            data_populator.ingest()
        else:
            data_populator.reingest()
    except InterruptedImportError as e:
        logger.error(str(e))
        sys.exit(1)
    except NoDataError as e:
        logger.error(str(e))
        sys.exit(1)
    except MetadataError:
        logger.exception("Error processing metadata records")
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected/unhandled exception")
        sys.exit(1)

    if configuration.stats:
        stats = data_populator.stats
        print((
            "\nStats:\n"
            f"Total Entries:\t\t {stats.total}\n"
            f"New Entries:\t\t {stats.new}\n"
            f"Updated Entries:\t {stats.updated}\n"
            f"Duplicate Entries\t {stats.duplicates}\n"
            f"Unchanged Entries:\t {stats.unchanged}\n"
        ))


if __name__ == "__main__":
    main()
