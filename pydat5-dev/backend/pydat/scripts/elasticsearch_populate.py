#!/usr/bin/env python

import sys
import datetime
import argparse
import getpass
import logging
from logging import StreamHandler

from pydat.core.elastic.ingest import (
    DataPopulator,
)
from pydat.core.elastic.ingest.debug_levels import DebugLevel


def main():
    parser = argparse.ArgumentParser()

    dataSource = parser.add_mutually_exclusive_group()
    dataSource.add_argument(
        "-f", "--file", action="store", dest="file",
        default=None, help="Input CSV file")
    dataSource.add_argument(
        "-d", "--directory", action="store",
        dest="directory", default=None,
        help=(
            "Directory to recursively search for CSV files -- mutually "
            "exclusive to '-f' option"
        )
    )

    parser.add_argument(
        "-e", "--extension", action="store", dest="extension",
        default='csv',
        help=(
            "When scanning for CSV files only parse files with given "
            "extension (default: 'csv')"
        )
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "-r", "--redo", action="store_true", dest="redo",
        default=False,
        help=(
            "Attempt to re-import a failed import or import more data, "
            "uses stored metadata from previous run"
        )
    )
    mode.add_argument(
        "--config-template-only", action="store_true",
        default=False, dest="config_template_only",
        help=("Configure the ElasticSearch template and then exit")
    )

    mode.add_argument(
        "--clear-interrupted-flag", action="store_true",
        default=False, dest="clear_interrupted",
        help=("Clear the interrupted flag, forcefully (NOT RECOMMENDED")
    )

    parser.add_argument(
        "-D", "--ingest-day", action="store", dest="ingest_day",
        default=None, help=(
            "Day to use for metadata, in the format 'YYYY-MM-dd', e.g.,"
            " '2021-01-01'. Defaults to todays date, use 'YYYY-MM-00' to "
            "indicate a quarterly ingest"
        )
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", dest="verbose",
        default=False, help="Be verbose"
    )
    parser.add_argument(
        "-s", "--stats", action="store_true", dest="stats",
        default=False, help="Print out Stats after running"
    )

    updateMethod = parser.add_mutually_exclusive_group()
    updateMethod.add_argument(
        "-x", "--exclude", action="store",
        dest="exclude", default="",
        help=("Comma separated list of keys to exclude if updating entry"))
    updateMethod.add_argument(
        "-n", "--include", action="store",
        dest="include", default="",
        help=(
            "Comma separated list of keys to include if updating entry "
            "(mutually exclusive to -x)"
        )
    )

    parser.add_argument(
        "-o", "--comment", action="store", dest="comment",
        default="", help="Comment to store with metadata"
    )

    elasticOptions = parser.add_argument_group('Elasticsearch Options')
    elasticOptions.add_argument(
        "-u", "--es-uri", nargs="*", dest="es_uri",
        default=['localhost:9200'],
        help=(
            "Location(s) of ElasticSearch Server (e.g., foo.server.com:9200)"
            " Can take multiple endpoints"
        )
    )
    elasticOptions.add_argument(
        "--es-user", action="store", dest="es_user",
        default=None,
        help=("Username for ElasticSearch when Basic Auth is enabled")
    )
    elasticOptions.add_argument(
        "--es-pass", action="store", dest="es_pass",
        default=None,
        help=("Password for ElasticSearch when Basic Auth is enabled")
    )
    elasticOptions.add_argument(
        "--es-ask-pass", action="store_true",
        dest="es_ask_pass", default=False,
        help="Prompt for ElasticSearch password"
    )
    elasticOptions.add_argument(
        "--es-enable-ssl", action="store",
        dest="es_cacert", default=None,
        help=("The path, on disk to the cacert of the "
              "ElasticSearch server to enable ssl/https "
              "support")
    )
    elasticOptions.add_argument(
        "--es-disable-sniffing", action="store_true",
        dest="es_disable_sniffing", default=False,
        help=(
            "Disable ES sniffing, useful when ssl hostname"
            "verification is not working properly"
        )
    )
    elasticOptions.add_argument(
        "-p", "--index-prefix", action="store",
        dest="index_prefix", default='pydat',
        help=("Index prefix to use in ElasticSearch (default: pydat)")
    )
    elasticOptions.add_argument(
        "-B", "--bulk-size", action="store", dest="bulk_size",
        type=int, default=1000,
        help="Size of Bulk Elasticsearch Requests"
    )
    elasticOptions.add_argument(
        "-b", "--bulk-fetch-size", action="store",
        dest="bulk_fetch_size", type=int, default=50,
        help=(
            "Number of documents to search for at a time (default 50), "
            "note that this will be multiplied by the number of indices you "
            "have, e.g., if you have 10 pydat-<number> indices it results "
            "in a request for 500 documents"
        )
    )
    elasticOptions.add_argument(
        "--rollover-size", action="store", type=int,
        dest="rollover_docs", default=50000000,
        help=(
            "Set the number of documents after which point a new index "
            "should be created, defaults to 50 milllion, note that this "
            "is fuzzy since the index count isn't continuously updated, "
            "so should be reasonably below 2 billion per ES shard and should"
            " take your ES configuration into consideration"
        )
    )

    parser.add_argument(
        "--pipelines", action="store", dest="procs", type=int,
        metavar="PIPELINES",
        default=2, help="Number of pipelines, defaults to 2"
    )
    parser.add_argument(
        "--shipper-threads", action="store",
        dest="shipper_threads", type=int, default=1,
        help=(
            "How many threads per pipeline to spawn to send bulk ES messages."
            " The larger your cluster, the more you can increase this, "
            "defaults to 1"
        )
    )
    parser.add_argument(
        "--fetcher-threads", action="store",
        dest="fetcher_threads", type=int, default=2,
        help=(
            "How many threads to spawn to search ES. The larger your cluster,"
            " the more you can increase this, defaults to 2")
    )
    parser.add_argument(
        "--ignore-field-prefixes", nargs='*',
        dest="ignore_field_prefixes", type=str,
        default=[
            'zoneContact',
            'billingContact',
            'technicalContact'
        ],
        help=(
            "list of fields (in whois data) to ignore when "
            "extracting and inserting into ElasticSearch"
        )
    )

    parser.add_argument(
        "--debug", action="store_true", default=False,
        help="Enables debug logging"
    )
    parser.add_argument(
        "--debug-level", dest="debug_level", action="store", type=int,
        default=1, help="Debug logging level [1 (default) - 3]"
    )

    options = parser.parse_args()

    if options.debug:
        options.debug = DebugLevel(options.debug_level)
    else:
        options.debug = DebugLevel.DISABLED

    if options.es_ask_pass:
        try:
            options.es_pass = getpass.getpass("Enter ElasticSearch Password: ")
        except Exception:
            # TODO FIXME add better handling
            print("Unable to get password", file=sys.stderr)
            sys.exit(1)

    if options.exclude != "":
        options.exclude = options.exclude.split(',')
    else:
        options.exclude = None

    if options.include != "":
        options.include = options.include.split(',')
    else:
        options.include = None

    if options.ingest_day is not None:
        ingest_parts = options.ingest_day.strip().rstrip().split('-')
        if len(ingest_parts) != 3:
            print("D/ingest_day format is 'YYYY-MM-dd'", file=sys.stderr)
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
            print("Unable to verify date provided", file=sys.stderr)
            sys.exit(1)

    elastic_arguments = {
        'hosts': options.es_uri,
        'username': options.es_user,
        'password': options.es_pass,
        'cacert': options.es_cacert,
        'disable_sniffing': options.es_disable_sniffing,
        'indexPrefix': options.index_prefix,
        'rollover_size': options.rollover_docs
    }

    # Setup Logging
    root_debug_level = logging.WARNING
    root_default_level = logging.WARNING

    try:
        logHandler = StreamHandler(sys.stdout)
    except Exception as e:
        print(f"Unable to setup logger to stdout\nError Message: {str(e)}\n")
        sys.exit(1)

    if options.debug:
        log_format = (
            "%(levelname) -10s %(asctime)s %(funcName) "
            "-20s %(lineno) -5d: %(message)s"
        )
    else:
        log_format = "%(message)s"

    logFormatter = logging.Formatter(log_format)

    # Set defaults for all loggers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    logHandler.setFormatter(logFormatter)
    root_logger.addHandler(logHandler)

    if options.debug:
        root_logger.setLevel(root_debug_level)
    else:
        root_logger.setLevel(root_default_level)

    dataPopulator = DataPopulator(
        elastic_args=elastic_arguments,
        include_fields=options.include,
        exclude_fields=options.exclude,
        ingest_day=options.ingest_day,
        ignore_field_prefixes=options.ignore_field_prefixes,
        pipelines=options.procs,
        ingest_directory=options.directory,
        ingest_file=options.file,
        extension=options.extension,
        comment=options.comment,
        bulk_fetch_size=options.bulk_fetch_size,
        bulk_ship_size=options.bulk_size,
        verbose=options.verbose,
        debug=options.debug,
    )

    if options.config_template_only:
        dataPopulator.configTemplate()
        sys.exit(0)

    if options.clear_interrupted:
        dataPopulator.clearInterrupted()
        sys.exit(0)

    if (options.file is None and options.directory is None):
        print("A File or Directory source is required", file=sys.stderr)
        parser.parse_args(["-h"])

    if not options.redo:
        dataPopulator.ingest()
    else:
        dataPopulator.reingest()

    if options.stats:
        stats = dataPopulator.stats
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
