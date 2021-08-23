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
    'uri':                      {'type': 'list',
                                 'schema': {'type': 'string'}
                                 },
    'user':                     {'type': 'string'},
    'password':                 {'type': 'string',
                                 'nullable': True
                                 },
    'ask_password':             {'type': 'boolean'},
    'ca_cert':                  {'type': 'string',
                                 'nullable': True
                                 },
    'disable_sniffing':         {'type': 'boolean'},
    'index_prefix':             {'type': 'string'},
    'rollover_docs':            {'type': 'integer'}
}
CONFIG_SCHEMA = {
    # general
    'debug':                    {'type': 'boolean'},
    'debug_level':              {'type': 'integer',
                                 'min': 0,
                                 'max': 3
                                 },
    'redo':                     {'type': 'boolean',
                                 'excludes': ['config_template_only',
                                              'clear_interrupted'
                                              ]
                                 },
    'config_template_only':     {'type': 'boolean',
                                 'excludes': ['redo',
                                              'clear_interrupted'
                                              ]
                                 },
    'clear_interrupted':        {'type': 'boolean',
                                 'excludes': ['redo',
                                              'config_template_only'
                                              ]
                                 },
    # data populator
    'include':                  {'type': 'list',
                                 'nullable': True,
                                 'excludes': 'exclude',
                                 'schema': {'type': 'string'}
                                 },
    'exclude':                  {'type': 'list',
                                 'nullable': True,
                                 'excludes': 'include',
                                 'schema': {'type': 'string'}
                                 },
    'ingest_day':               {'type': 'string',
                                 'nullable': True
                                 },
    'ignore_field_prefixes':    {'type': 'list',
                                 'nullable': True,
                                 'schema': {'type': 'string'}
                                 },
    'pipelines':                {'type': 'integer'},
    'ingest_directory':         {'type': 'string',
                                 'excludes': 'ingest_file',
                                 'required': True
                                 },
    'ingest_file':              {'type': 'string',
                                 'excludes': 'ingest_directory',
                                 'required': True
                                 },
    'extension':                {'type': 'string'},
    'comment':                  {'type': 'string'},
    'bulk_fetch_size':          {'type': 'integer'},
    'bulk_ship_size':           {'type': 'integer'},
    'verbose':                  {'type': 'boolean'},
    'es':                       {'type': 'dict',
                                 'schema': ELASTIC_SCHEMA
                                 }
}

ELASTIC_DEFAULTS = {
    'uri':                      {'default': ['localhost:9200']},
    'user':                     {'default': None},
    'password':                 {'default': None},
    'ca_cert':                  {'default': None},
    'ask_password':             {'default': False},
    'disable_sniffing':         {'default': False},
    'index_prefix':             {'default': 'pydat'},
    'rollover_docs':            {'default': 50000000}
}
CONFIG_DEFAULTS = {
    # general
    'debug':                    {'default': False},
    'debug_level':              {'default': 1},
    'redo':                     {'default': False},
    'config_template_only':     {'default': False},
    'clear_interrupted':        {'default': False},
    # data populator
    'include':                  {'default': None},
    'exclude':                  {'default': None},
    'ingest_day':               {'default': None},
    'ignore_field_prefixes':    {'default': None},
    'pipelines':                {'default': 2},
    'ingest_directory':         {'default': None},
    'ingest_file':              {'default': None},
    'extension':                {'default': 'csv'},
    'comment':                  {'default': ''},
    'bulk_fetch_size':          {'default': 50},
    'bulk_ship_size':           {'default': 10},
    'verbose':                  {'default': False},
    'es':                       {'type': 'dict',
                                 'schema': ELASTIC_DEFAULTS
                                 }
}


def parse_args(input_args=None):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c", "--config", type=str, dest="config",
        help=(
            "location of configuration file for environment"
            "parameter configuration (example yaml file in /backend)"
        )
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enables debug logging"
    )

    parser.add_argument(
        "--debug-level", dest="debug_level", type=int,
        help="Debug logging level [0-3] (default: 1)"
    )

    parser.add_argument(
        "-r", "--redo", action="store_const", dest="redo", const=True,
        help=(
            "Attempt to re-import a failed import or import more data, "
            "uses stored metadata from previous run"
        )
    )
    parser.add_argument(
        "--config-template-only", action="store_const",
        dest="config_template_only", const=True,
        help="Configure the ElasticSearch template and then exit"
    )

    parser.add_argument(
        "--clear-interrupted-flag", action="store_const",
        dest="clear_interrupted", const=True,
        help="Clear the interrupted flag, forcefully (NOT RECOMMENDED)"
    )

    parser.add_argument(
        "-x", "--exclude", nargs="+", type=str, dest="exclude",
        help="list of keys to exclude if updating entry"
    )

    parser.add_argument(
        "-n", "--include", nargs="+", type=str, dest="include",
        help=(
            "list of keys to include if updating entry "
            "(mutually exclusive to -x)"
        )
    )

    parser.add_argument(
        "-D", "--ingest-day", action="store", dest="ingest_day",
        help=(
            "Day to use for metadata, in the format 'YYYY-MM-dd', e.g.,"
            " '2021-01-01'. Defaults to todays date, use 'YYYY-MM-00' to "
            "indicate a quarterly ingest, e.g., 2021-04-00"
        )
    )

    parser.add_argument(
        "--ignore-field-prefixes", nargs='*', type=str,
        dest="ignore_field_prefixes",
        help=(
            "list of fields (in whois data) to ignore when "
            "extracting and inserting into ElasticSearch"
        )
    )

    parser.add_argument(
        "--pipelines", action="store", type=int,
        metavar="PIPELINES", dest="pipelines",
        help="Number of pipelines (default: 2)"
    )

    parser.add_argument(
        "-f", "--file", dest="ingest_file", help="Input CSV file"
    )

    parser.add_argument(
        "-d", "--directory", dest="ingest_directory",
        help=(
            "Directory to recursively search for CSV files -- mutually"
            " exclusive to '-f' option"
        )
    )

    parser.add_argument(
        "-e", "--extension", dest="extension",
        help=(
            "When scanning for CSV files only parse files with given "
            "extension (default: csv)"
        )
    )

    parser.add_argument(
        "-o", "--comment", dest="comment",
        help="Comment to store with metadata"
    )

    parser.add_argument(
        "-B", "--bulk-size", type=int, dest="bulk_ship_size",
        help="Size of Bulk Elasticsearch Requests (default: 10)"
    )

    parser.add_argument(
        "-b", "--bulk-fetch-size", type=int, dest="bulk_fetch_size",
        help=(
            "Number of documents to search for at a time (default: 50), "
            "note that this will be multiplied by the number of indices you "
            "have, e.g., if you have 10 pydat-<number> indices it results "
            "in a request for 500 documents"
        )
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", dest="verbose",
        help="Be verbose"
    )

    elastic_options = parser.add_argument_group('Elasticsearch Options')
    elastic_options.add_argument(
        "-u", "--es-uri", nargs="*", dest="es__uri",
        help=(
            "Location(s) of ElasticSearch Server (e.g., foo.server.com:9200)"
            " Can take multiple endpoints"
        )
    )

    elastic_options.add_argument(
        "--es-user", dest="es__user",
        help="Username for ElasticSearch when Basic Auth is enabled"
    )

    elastic_options.add_argument(
        "--es-pass", dest="es__password",
        help="Password for ElasticSearch when Basic Auth is enabled"
    )

    elastic_options.add_argument(
        "--es-ask-pass", action="store_true", dest="es__ask_password",
        help="Prompt for ElasticSearch password"
    )

    elastic_options.add_argument(
        "--cacert", dest="es__ca_cert",
        help=""
    )

    elastic_options.add_argument(
        "--es-disable-sniffing", action="store_true",
        dest="es__disable_sniffing",
        help=(
            "Disable ES sniffing, useful when ssl hostname"
            "verification is not working properly"
        )
    )

    elastic_options.add_argument(
        "-p", "--index-prefix", dest="es__index_prefix",
        help="Index prefix to use in ElasticSearch (default: pydat)"
    )

    elastic_options.add_argument(
        "--rollover-size", type=int, dest="es__rollover_docs",
        help=(
            "Set the number of documents after which point a new index "
            "should be created, defaults to 50 milllion, note that this "
            "is fuzzy since the index count isn't continuously updated, "
            "so should be reasonably below 2 billion per ES shard and should"
            " take your ES configuration into consideration"
        )
    )

    if input_args:
        return parser.parse_args(input_args)
    return parser.parse_args()


def expand_argparse(args):
    def set_key(dictionary, keys, value):
        for key in keys[:-1]:
            dictionary = dictionary.setdefault(key, {})
        dictionary[keys[-1]] = value

    nested = dict()
    for arg, val in args.items():
        if val is not None:
            set_key(nested, arg.split('__'), val)
    return nested


def validate_configuration(configuration):
    v = cerberus.Validator(CONFIG_SCHEMA)
    if not v.validate(configuration):
        raise ValueError(v.errors)

    if configuration.get("ingest_file") is None and \
            configuration.get("ingest_directory") is None:
        raise ValueError("A File or Directory source is required")

    n = cerberus.Validator(CONFIG_DEFAULTS)
    return n.normalized(configuration)


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


def process_additional_configuration(configuration, logger):
    if configuration.ingest_day is not None:
        ingest_parts = configuration.ingest_day.strip().rstrip().split('-')
        if len(ingest_parts) != 3:
            logger.error("D/ingest_day format is 'YYYY-MM-dd'")
            sys.exit(1)

        if ingest_parts[2] == '00':
            ingest_parts[2] = 1

        try:
            datetime.date(
                int(ingest_parts[0]),
                int(ingest_parts[1]),
                int(ingest_parts[2])
            )
        except ValueError:
            logger.error("Unable to verify date provided")
            sys.exit(1)
    elif not configuration.redo:
        logger.warning("Ingest Day was not provided, assuming today")

    if configuration.es.ask_password:
        try:
            configuration.es.password = \
                getpass.getpass("Enter ElasticSearch Password: ")
        except Exception:
            # TODO FIXME add better handling
            print("Unable to get password", file=sys.stderr)
            sys.exit(1)


def main(args):
    config = args
    if 'config' in args:
        with open(args.pop('config'), 'r') as c:
            config_file = yaml.safe_load(c)

        config = {**config_file, **args}
        config['es'] = {**config_file.get('es', {}), **args.get('es', {})}

    try:
        config = validate_configuration(config)
        configuration = SimpleNamespace(**config)
        configuration.es = SimpleNamespace(**configuration.es)
    except ValueError as e:
        print(f'invalid configuration: {str(e)}')
        parse_args(["-h"])
        exit(1)

    logger = setup_logging(configuration)
    process_additional_configuration(configuration, logger)

    elastic_arguments = {
        'hosts': configuration.es.uri,
        'username': configuration.es.user,
        'password': configuration.es.password,
        'cacert': configuration.es.ca_cert,
        'disable_sniffing': configuration.es.disable_sniffing,
        'indexPrefix': configuration.es.index_prefix,
        'rollover_size': configuration.es.rollover_docs
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
    main(expand_argparse(vars(parse_args())))
