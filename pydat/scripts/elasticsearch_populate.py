#!/usr/bin/env python

import sys
import os
import unicodecsv
import time
import argparse
from threading import Thread
import multiprocessing
from multiprocessing import (Process,
                             Queue as mpQueue,
                             JoinableQueue as jmpQueue)
import json
import traceback
import logging
from logging import StreamHandler
from logging.handlers import TimedRotatingFileHandler

from HTMLParser import HTMLParser
import Queue as queue

import elasticsearch
from elasticsearch import helpers

VERSION_KEY = 'dataVersion'
UPDATE_KEY = 'updateVersion'
FIRST_SEEN = 'dataFirstSeen'

DOC_TYPE = "doc"
META_DOC_TYPE = "doc"


def connectElastic(uri):
    es = elasticsearch.Elasticsearch(uri,
                                     sniff_on_start=True,
                                     max_retries=100,
                                     retry_on_timeout=True,
                                     sniff_on_connection_fail=True,
                                     sniff_timeout=1000,
                                     timeout=100)

    return es


class StatTracker(Thread):
    """Multi-processing safe stat tracking class

    This class can be provided to all pipelines to keep track of different
    stats about the domains being ingested
    """

    def __init__(self, **kwargs):
        Thread.__init__(self, **kwargs)
        self._stats = {'total': 0,
                       'new': 0,
                       'updated': 0,
                       'unchanged': 0,
                       'duplicates': 0}
        self._stat_queue = mpQueue()
        self._shutdown = False
        self._changed = dict()

    @property
    def total(self):
        return self._stats['total']

    @property
    def new(self):
        return self._stats['new']

    @property
    def updated(self):
        return self._stats['updated']

    @property
    def unchanged(self):
        return self._stats['unchanged']

    @property
    def duplicates(self):
        return self._stats['duplicates']

    @property
    def changed_stats(self):
        return self._changed

    def seed(self, stats):
        self._stats = stats

    def seedChanged(self, changed):
        for (name, value) in changed.items():
            self._changed[name] = int(value)

    def shutdown(self):
        self._shutdown = True

    def run(self):
        while 1:
            try:
                (typ, field) = self._stat_queue.get_nowait()
            except queue.Empty:
                if self._shutdown:
                    break
                time.sleep(.1)
                continue
            if typ == 'stat':
                if field not in self._stats:
                    LOGGER.error("Unknown field %s" % (field))

                self._stats[field] += 1
            elif typ == 'chn':
                if field not in self._changed:
                    self._changed[field] = 0
                self._changed[field] += 1
            else:
                LOGGER.error("Unknown stat type")

        self._stat_queue.close()

    def addChanged(self, field):
        self._stat_queue.put(('chn', field))

    def incr(self, field):
        self._stat_queue.put(('stat', field))


class EventTracker(object):
    def __init__(self):
        self._shutdownEvent = multiprocessing.Event()
        self._bulkErrorEvent = multiprocessing.Event()
        self._fileReaderDoneEvent = multiprocessing.Event()

    @property
    def shutdown(self):
        return self._shutdownEvent.is_set()

    def setShutdown(self):
        self._shutdownEvent.set()

    @property
    def bulkError(self):
        return self._bulkErrorEvent.is_set()

    def setBulkError(self):
        self._bulkErrorEvent.set()

    @property
    def fileReaderDone(self):
        return self._fileReaderDoneEvent.is_set()

    def setFileReaderDone(self):
        self._fileReaderDoneEvent.set()


class indexFormatter(object):
    """Convenience object to store formatted index names, based on the prefix
    """

    def __init__(self, prefix):
        self.prefix = prefix
        self.orig_write = "%s-write" % prefix
        self.delta_write = "%s-delta-write" % prefix
        self.orig_search = "%s-orig" % prefix
        self.delta_search = "%s-delta" % prefix
        self.search = "%s-search" % prefix
        self.meta = ".%s-meta" % prefix
        self.template_pattern = "%s-*" % prefix
        self.template_name = "%s-template" % prefix


class _mpLoggerClient(object):
    """class returned by mpLogger.getLogger

    This class mimics how logger should act by providing the same/similar
    facilities
    """

    def __init__(self, name, logQueue, **kwargs):
        self.name = name
        self.logQueue = logQueue
        self._logger = logging.getLogger()
        self._prefix = None

    @property
    def prefix(self):
        return self._prefix

    @prefix.setter
    def prefix(self, value):
        if not isinstance(value, basestring):
            raise TypeError("Expected a string type")
        self._prefix = value

    def log(self, lvl, msg, *args, **kwargs):
        if self.prefix is not None:
            msg = self.prefix + msg

        if kwargs.get('exc_info', False) is not False:
            if (not (isinstance(kwargs['exc_info'], tuple) and
                     len(kwargs['exc_info']) == 3)):
                kwargs['exc_info'] = sys.exc_info()
            (etype, eclass, tb) = kwargs['exc_info']
            exc_msg = ''.join(traceback.format_exception(etype,
                                                         eclass,
                                                         tb))
            kwargs['_exception_'] = exc_msg

        if kwargs.get('_exception_', None) is not None:
            msg += "\n%s" % (kwargs['_exception_'])

        (name, line, func) = self._logger.findCaller()
        log_data = (self.name, lvl, name, line, msg, args, None,
                    func, kwargs.get('extra', None))
        self.logQueue.put(log_data)

    def debug(self, msg, *args, **kwargs):
        self.log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.log(logging.CRITICAL, msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        kwargs['_exception_'] = traceback.format_exc()
        self.log(logging.ERROR, msg, *args, **kwargs)


class mpLogger(Thread):
    """Multiprocessing 'safe' logger implementation

    This logger implementation should probably not be used by the main
    thread since it relies on a queue for its data processing. So if things
    need to be printed immediately, i.e,. on error, it should be done via
    the regular logging instance
    """

    def __init__(self, name=__name__, debug=False, **kwargs):
        Thread.__init__(self, **kwargs)
        self._debug = debug
        self.daemon = True
        self.name = name
        self.logQueue = mpQueue()
        self._logger = None
        self._stop = False

    @property
    def logger(self):
        if self._logger is None:
            self._logger = logging.getLogger()
        return self._logger

    def getLogger(self, name=__name__):
        return _mpLoggerClient(name=name, logQueue=self.logQueue)

    def join(self):
        time.sleep(.1)
        while not self.logQueue.empty():
            time.sleep(.1)

    def run(self):
        default_level = logging.INFO
        root_debug_level = logging.WARNING
        debug_level = logging.DEBUG
        root_default_level = logging.WARNING

        try:
            logHandler = StreamHandler(sys.stdout)
        except Exception, e:
            raise Exception(("Unable to setup logger to stdout\n"
                             "Error Message: %s\n") % str(e))

        if self._debug:
            log_format = ("%(levelname) -10s %(asctime)s %(funcName) "
                          "-20s %(lineno) -5d: %(message)s")
        else:
            log_format = ("%(message)s")

        logFormatter = logging.Formatter(log_format)

        # Set defaults for all loggers
        root_logger = logging.getLogger()
        root_logger.handlers = []
        logHandler.setFormatter(logFormatter)
        root_logger.addHandler(logHandler)

        if self._debug:
            root_logger.setLevel(root_debug_level)
        else:
            root_logger.setLevel(root_default_level)

        logger = logging.getLogger(self.name)

        if self._debug:
            logger.setLevel(debug_level)
        else:
            logger.setLevel(default_level)

        while 1:
            try:
                raw_record = self.logQueue.get_nowait()
                if logger.isEnabledFor(raw_record[1]):
                    logger.handle(logger.makeRecord(*raw_record))
            except EOFError:
                break
            except queue.Empty:
                if self._stop:
                    break
                time.sleep(.1)


class FileReader(Thread):
    """Simple data file organizer

    This class focuses on iterating through directories and putting
    found files into a queue for processing by pipelines
    """

    def __init__(self, datafile_queue, eventTracker, options, **kwargs):
        Thread.__init__(self, **kwargs)
        self.datafile_queue = datafile_queue
        self.eventTracker = eventTracker
        self.options = options
        self._shutdown = False

    def shutdown(self):
        self._shutdown = True

    def run(self):
        try:
            if self.options.directory:
                self.scan_directory(self.options.directory)
            elif self.options.file:
                self.datafile_queue.put(self.options.file)
            else:
                LOGGER.error("File or Directory required")
        except Exception as e:
            LOGGER.error("Unknown exception in File Reader")
        finally:
            LOGGER.debug("Setting FileReaderDone event")
            self.eventTracker.setFileReaderDone()

    def scan_directory(self, directory):
        for path in sorted(os.listdir(directory)):
            fp = os.path.join(directory, path)

            if os.path.isdir(fp):
                    self.scan_directory(fp)
            elif os.path.isfile(fp):
                if self._shutdown:
                    return
                if self.options.extension != '':
                    fn, ext = os.path.splitext(path)
                    if ext and ext[1:] != self.options.extension:
                        continue
                self.datafile_queue.put(fp)
            else:
                LOGGER.warning("%s is neither a file nor directory" % (fp))


class DataReader(Thread):
    """CSV Parsing Class

    This class focuses on reading in and parsing a given CSV file as
    provided by the FileReader class. After creating its output it
    places it on a queue for processing by the fetcher
    """

    def __init__(self, datafile_queue, data_queue, eventTracker,
                 options, **kwargs):
        Thread.__init__(self, **kwargs)
        self.datafile_queue = datafile_queue
        self.data_queue = data_queue
        self.options = options
        self.eventTracker = eventTracker
        self._shutdown = False
        self._pause = False

    def shutdown(self):
        self._shutdown = True

    def pause(self):
        self._pause = True

    def unpause(self):
        self._pause = False

    def run(self):
        while not self._shutdown:
            try:
                datafile = self.datafile_queue.get_nowait()
                try:
                    self.parse_csv(datafile)
                finally:
                    self.datafile_queue.task_done()
            except queue.Empty as e:
                if self.eventTracker.fileReaderDone:
                    LOGGER.debug("FileReaderDone Event seen")
                    break
                time.sleep(.01)
                continue
            except Exception as e:
                LOGGER.exception("Unhandled Exception")
        LOGGER.debug("Reader exiting")

    def check_header(self, header):
        for field in header:
            if field == "domainName":
                return True

        return False

    def parse_csv(self, filename):
        if self._shutdown:
            return

        try:
            csvfile = open(filename, 'rb')
            s = os.stat(filename)
            if s.st_size == 0:
                LOGGER.warning("File %s empty" % (filename))
                return
        except Exception as e:
            LOGGER.warning("Unable to stat file %s, skiping" % (filename))
            return

        if self.options.verbose:
            LOGGER.info("Processing file: %s" % filename)

        try:
            dnsreader = unicodecsv.reader(csvfile, strict=True,
                                          skipinitialspace=True)
        except Exception as e:
            LOGGER.exception("Unable to setup csv reader for file %s"
                             % (filename))
            return

        try:
            header = next(dnsreader)
        except Exception as e:
            LOGGER.exception("Unable to iterate through csv file %s"
                             % (filename))
            return

        try:
            if not self.check_header(header):
                raise unicodecsv.Error('CSV header not found')

            for row in dnsreader:
                while self._pause:
                    if self._shutdown:
                        LOGGER.debug("Shutdown received while paused")
                        break
                    time.sleep(.5)
                if self._shutdown:
                    LOGGER.debug("Shutdown received")
                    break
                self.data_queue.put({'header': header, 'row': row})
        except unicodecsv.Error as e:
            LOGGER.exception("CSV Parse Error in file %s - line %i\n"
                             % (os.path.basename(filename),
                                dnsreader.line_num))
        except Exception as e:
            LOGGER.exception("Unable to process file %s" % (filename))


class DataFetcher(Thread):
    """Bulk Fetching of Records

    This class does a bulk fetch of records to make the comparison of
    records more efficient. It takes the response and bundles it up with
    the source to be sent to the worker
    """

    def __init__(self, es, data_queue, work_queue, eventTracker,
                 options, **kwargs):
        Thread.__init__(self, **kwargs)
        self.data_queue = data_queue
        self.work_queue = work_queue
        self.options = options
        self.es = es
        self.fetcher_threads = []
        self.eventTracker = eventTracker
        self._shutdown = False
        self._finish = False

    def shutdown(self):
        self._shutdown = True

    def finish(self):
        self._finish = True

    def run(self):
        try:
            fetch = list()
            while not self._shutdown:
                try:
                    work = self.data_queue.get_nowait()
                except queue.Empty as e:
                    if self._finish:
                        if len(fetch) > 0:
                            data = self.handle_fetch(fetch)
                            for item in data:
                                self.work_queue.put(item)
                        break
                    time.sleep(.01)
                    continue
                except Exception as e:
                    LOGGER.exception("Unhandled Exception")

                try:
                    entry = self.parse_entry(work['row'], work['header'])
                    if entry is None:
                        LOGGER.warning("Malformed Entry")
                        continue

                    # Pre-empt all of this processing when not necessary
                    if (self.options.firstImport and
                            not self.options.rolledOver):
                        self.work_queue.put((entry, None))
                        continue

                    (domainName, tld) = parse_domain(entry['domainName'])
                    doc_id = "%s.%s" % (tld, domainName)
                    fetch.append((doc_id, entry))

                    if len(fetch) >= self.options.bulk_fetch_size:
                        start = time.time()
                        data = self.handle_fetch(fetch)
                        for item in data:
                            self.work_queue.put(item)
                        fetch = list()
                except Exception as e:
                    LOGGER.exception("Unhandled Exception")
                finally:
                    self.data_queue.task_done()

        except Exception as e:
            LOGGER.exception("Unhandled Exception")

    def parse_entry(self, input_entry, header):
        if len(input_entry) == 0:
            return None

        htmlparser = HTMLParser()

        details = {}
        domainName = ''
        for (i, item) in enumerate(input_entry):
            if any(header[i].startswith(s)
                    for s in self.options.ignore_field_prefixes):
                continue
            if header[i] == 'domainName':
                if self.options.vverbose:
                    LOGGER.info("Processing domain: %s" % item)
                domainName = item
                continue
            if item == "":
                details[header[i]] = None
            else:
                details[header[i]] = htmlparser.unescape(item)

        entry = {VERSION_KEY: self.options.identifier,
                 FIRST_SEEN: self.options.identifier,
                 'tld': parse_domain(domainName)[1],
                 'details': details,
                 'domainName': domainName}

        if self.options.update:
            entry[UPDATE_KEY] = self.options.updateVersion

        return entry

    def handle_fetch(self, fetch_list):
        results = list()
        try:
            docs = list()
            for (doc_id, entry) in fetch_list:
                for index_name in self.options.INDEX_LIST:
                    getdoc = {'_index': index_name,
                              '_type': DOC_TYPE,
                              '_id': doc_id}
                    docs.append(getdoc)
        except Exception as e:
            LOGGER.exception("Unable to generate doc list")
            return results

        try:
            result = self.es.mget(body={"docs": docs})
        except Exception as e:
            LOGGER.exception("Unable to create mget request")
            return results

        try:
            for (doc_count, index) in \
                    enumerate(range(0, len(result['docs']),
                              len(self.options.INDEX_LIST))):
                found = None
                doc_results = \
                    result['docs'][index:index + len(self.options.INDEX_LIST)]

                for res in doc_results:
                    if res['found']:
                        found = res
                        break

                if found is not None:
                    results.append((fetch_list[doc_count][1], found))
                else:
                    results.append((fetch_list[doc_count][1], None))

            return results
        except Exception as e:
            LOGGER.exception("Unhandled Exception")


class DataWorker(Thread):
    """Class to focus on entry comparison and instruction creation

    This class takes the input entry and latest entry as found by the fetcher
    and creates one or more elasticsearch update requests to be sent by the
    shipper
    """

    def __init__(self, work_queue, insert_queue, statTracker,
                 eventTracker, options, **kwargs):
        Thread.__init__(self, **kwargs)
        self.work_queue = work_queue
        self.insert_queue = insert_queue
        self.statTracker = statTracker
        self.options = options
        self.eventTracker = eventTracker
        self._shutdown = False
        self._finish = False

    def shutdown(self):
        self._shutdown = True

    def finish(self):
        self._finish = True

    def run(self):
        try:
            while not self._shutdown:
                try:
                    (entry, current_entry_raw) = self.work_queue.get_nowait()
                except queue.Empty as e:
                    if self._finish:
                        break
                    time.sleep(.0001)
                    continue
                except Exception as e:
                    LOGGER.exception("Unhandled Exception")

                try:
                    if entry is None:
                        LOGGER.warning("Malformed Entry")
                        continue

                    if (not self.options.redo or
                            self.update_required(current_entry_raw)):
                        self.statTracker.incr('total')
                        self.process_entry(entry, current_entry_raw)
                finally:
                    self.work_queue.task_done()

        except Exception as e:
            LOGGER.exception("Unhandled Exception")

    def update_required(self, current_entry):
        if current_entry is None:
            return True

        if current_entry['_source'][VERSION_KEY] == self.options.identifier:
            # This record already up to date
            return False
        else:
            return True

    def process_entry(self, entry, current_entry_raw):
        domainName = entry['domainName']
        details = entry['details']
        api_commands = []

        if current_entry_raw is not None:
            current_index = current_entry_raw['_index']
            current_id = current_entry_raw['_id']
            current_type = current_entry_raw['_type']
            current_entry = current_entry_raw['_source']

            if (not self.options.update and
                    (current_entry[VERSION_KEY] == self.options.identifier)):
                # Duplicate entry in source csv's?
                if self.options.vverbose:
                    LOGGER.info('%s: Duplicate' % domainName)
                self.statTracker.incr('duplicates')
                return

            if self.options.exclude is not None:
                details_copy = details.copy()
                for exclude in self.options.exclude:
                    del details_copy[exclude]

                changed = (set(details_copy.items()) -
                           set(current_entry['details'].items()))

            elif self.options.include is not None:
                details_copy = {}
                for include in self.options.include:
                    try:  # TODO
                        details_copy[include] = details[include]
                    except Exception as e:
                        pass

                changed = (set(details_copy.items()) -
                           set(current_entry['details'].items()))

            else:
                changed = set(details.items()) \
                            - set(current_entry['details'].items())

                # The above diff doesn't consider keys that are only in the
                # latest in es, so if a key is just removed, this diff will
                # indicate there is no difference even though a key had been
                # removed. I don't forsee keys just being wholesale removed,
                # so this shouldn't be a problem

            for ch in changed:
                self.statTracker.addChanged(ch[0])

            if len(changed) > 0:
                self.statTracker.incr('updated')
                if self.options.vverbose:
                    if self.options.update:
                        LOGGER.info("%s: Re-Registered/Transferred"
                                    % domainName)
                    else:
                        LOGGER.info("%s: Updated" % domainName)

                # Copy old entry into different document
                doc_id = "%s#%d.%d" % (current_id, current_entry[VERSION_KEY],
                                       current_entry.get(UPDATE_KEY, 0))
                if self.options.vverbose:
                    LOGGER.info("doc_id: %s" % (doc_id))
                api_commands.append(
                    self.process_command('create',
                                         self.options.indexNames.delta_write,
                                         doc_id,
                                         current_type,
                                         current_entry))

                # Update latest/orig entry
                if not self.options.update:
                    entry[FIRST_SEEN] = current_entry[FIRST_SEEN]
                api_commands.append(self.process_command('index',
                                                         current_index,
                                                         current_id,
                                                         current_type,
                                                         entry))
            else:
                self.statTracker.incr('unchanged')
                if self.options.vverbose:
                    LOGGER.info("%s: Unchanged" % domainName)
                doc_diff = {'doc': {VERSION_KEY: self.options.identifier,
                                    'details': details}}
                api_commands.append(self.process_command(
                                                     'update',
                                                     current_index,
                                                     current_id,
                                                     current_type,
                                                     doc_diff))
        else:
            self.statTracker.incr('new')
            if self.options.vverbose:
                LOGGER.info("%s: New" % domainName)
            (domain_name_only, tld) = parse_domain(domainName)
            doc_id = "%s.%s" % (tld, domain_name_only)
            if self.options.update:
                api_commands.append(
                    self.process_command('index',
                                         self.options.indexNames.orig_write,
                                         doc_id,
                                         DOC_TYPE,
                                         entry))
            else:
                api_commands.append(
                    self.process_command('create',
                                         self.options.indexNames.orig_write,
                                         doc_id,
                                         DOC_TYPE,
                                         entry))
        for command in api_commands:
            self.insert_queue.put(command)

    def process_command(self, request, index, _id, _type, entry=None):
        if request == 'create':
            command = {
                       "_op_type": "create",
                       "_index": index,
                       "_type": _type,
                       "_id": _id,
                       "_source": entry
                      }
            return command
        elif request == 'update':
            command = {
                       "_op_type": "update",
                       "_index": index,
                       "_id": _id,
                       "_type": _type,
                      }
            command.update(entry)
            return command
        elif request == 'delete':
            command = {
                        "_op_type": "delete",
                        "_index": index,
                        "_id": _id,
                        "_type": _type,
                      }
            return command
        elif request == 'index':
            command = {
                        "_op_type": "index",
                        "_index": index,
                        "_type": _type,
                        "_source": entry
                      }
            if _id is not None:
                command["_id"] = _id
            return command
        else:
            LOGGER.error("Unrecognized command")
            return None


class DataShipper(Thread):
    """Thread that ships commands to elasticsearch cluster_stats
    """

    def __init__(self, es, insert_queue, eventTracker,
                 options, **kwargs):
        Thread.__init__(self, **kwargs)
        self.insert_queue = insert_queue
        self.options = options
        self.eventTracker = eventTracker
        self.es = es
        self._finish = False

    def finish(self):
        self._finish = True

    def run(self):
        def bulkIter():
            while not (self._finish and self.insert_queue.empty()):
                try:
                    req = self.insert_queue.get_nowait()
                except queue.Empty:
                    time.sleep(.1)
                    continue

                try:
                    yield req
                finally:
                    self.insert_queue.task_done()

        try:
            for (ok, response) in \
                    helpers.streaming_bulk(self.es, bulkIter(),
                                           raise_on_error=False,
                                           chunk_size=self.options.bulk_size):
                resp = response[response.keys()[0]]
                if not ok and resp['status'] not in [404, 409]:
                        if not self.eventTracker.bulkError:
                            self.eventTracker.setBulkError()
                        LOGGER.debug("Response: %s" % (str(resp)))
                        LOGGER.error(("Error making bulk request, received "
                                      "error reason: %s")
                                     % (resp['error']['reason']))
        except Exception as e:
            LOGGER.exception("Unexpected error processing bulk commands")
            if not self.eventTracker.bulkError:
                self.eventTracker.setBulkError


class DataProcessor(Process):
    """Main pipeline process which manages individual threads
    """
    def __init__(self, pipeline_id, datafile_queue, statTracker, logger,
                 eventTracker, options, **kwargs):
        Process.__init__(self, **kwargs)
        self.datafile_queue = datafile_queue
        self.statTracker = statTracker
        self.options = options
        self.fetcher_threads = []
        self.worker_thread = None
        self.shipper_threads = []
        self.reader_thread = None
        self.pause_request = multiprocessing.Value('b', False)
        self._paused = multiprocessing.Value('b', False)
        self._complete = multiprocessing.Value('b', False)
        self.eventTracker = eventTracker
        self.es = None
        self.myid = pipeline_id
        self.logger = logger

        # These are created when the process starts up
        self.data_queue = None
        self.work_queue = None
        self.insert_queue = None

    @property
    def paused(self):
        return self._paused.value

    @property
    def complete(self):
        return self._complete.value

    def pause(self):
        self.pause_request.value = True

    def unpause(self):
        self.pause_request.value = False

    def update_index_list(self):
        index_list = \
            self.es.indices.get_alias(name=self.options.indexNames.orig_search)
        self.options.INDEX_LIST = sorted(index_list.keys(), reverse=True)
        self.options.rolledOver = True

    def _pause(self):
        if self.reader_thread.isAlive():
            try:
                self.reader_thread.pause()
                self.finish()
                self._paused.value = True
            except Exception as e:
                LOGGER.exception("Unable to pause reader thread")
        else:
            LOGGER.debug("Pause requested when reader thread not alive")

    def _unpause(self):
        if self.reader_thread.isAlive():
            try:
                self.reader_thread.unpause()
            except Exception as e:
                LOGGER.exception("Unable to unpause reader thread")
            self.update_index_list()
            self.startup_rest()
            self._paused.value = False
        else:
            LOGGER.debug("Pause requested when reader thread not alive")

    def shutdown(self):
        LOGGER.debug("Shutting down reader")
        self.reader_thread.shutdown()
        while self.reader_thread.is_alive():
            try:
                self.datafile_queue.get_nowait()
                self.datafile_queue.task_done()
            except queue.Empty:
                break

        LOGGER.debug("Shutting down fetchers")
        for fetcher in self.fetcher_threads:
            fetcher.shutdown()
            # Ensure put is not blocking shutdown
            while fetcher.is_alive():
                try:
                    self.work_queue.get_nowait()
                    self.work_queue.task_done()
                except queue.Empty:
                    break

        LOGGER.debug("Draining work queue")
        # Drain the work queue
        while not self.work_queue.empty():
            try:
                self.work_queue.get_nowait()
                self.work_queue.task_done()
            except queue.Empty:
                break

        LOGGER.debug("Shutting down worker thread")
        self.worker_thread.shutdown()
        while self.worker_thread.is_alive():
            try:
                self.insert_queue.get_nowait()
                self.insert_queue.task_done()
            except queue.Empty:
                break

        LOGGER.debug("Draining insert queue")
        # Drain the insert queue
        while not self.insert_queue.empty():
            try:
                self.insert_queue.get_nowait()
                self.insert_queue.task_done()
            except queue.Empty:
                break

        LOGGER.debug("Waiting for shippers to finish")
        # Shippers can't be forced to shutdown
        for shipper in self.shipper_threads:
            shipper.finish()
            shipper.join()

        LOGGER.debug("Shutdown Complete")

    def finish(self):
        LOGGER.debug("Waiting for fetchers to finish")
        for fetcher in self.fetcher_threads:
            fetcher.finish()
            fetcher.join()

        LOGGER.debug("Waiting for worker to finish")
        self.worker_thread.finish()
        self.worker_thread.join()

        LOGGER.debug("Waiting for shippers to finish")
        for shipper in self.shipper_threads:
            shipper.finish()
            shipper.join()

        LOGGER.debug("Finish Complete")

    def startup_rest(self):
        LOGGER.debug("Starting Worker")
        self.worker_thread = DataWorker(self.work_queue,
                                        self.insert_queue,
                                        self.statTracker,
                                        self.eventTracker,
                                        self.options)
        self.worker_thread.daemon = True
        self.worker_thread.start()

        LOGGER.debug("starting Fetchers")
        for _ in range(self.options.fetcher_threads):
            fetcher_thread = DataFetcher(self.es,
                                         self.data_queue,
                                         self.work_queue,
                                         self.eventTracker,
                                         self.options)
            fetcher_thread.start()
            self.fetcher_threads.append(fetcher_thread)

        LOGGER.debug("Starting Shippers")
        for _ in range(self.options.shipper_threads):
            shipper_thread = DataShipper(self.es,
                                         self.insert_queue,
                                         self.eventTracker,
                                         self.options)
            shipper_thread.start()
            self.shipper_threads.append(shipper_thread)

    def run(self):
        os.setpgrp()
        global LOGGER
        LOGGER = self.logger.getLogger()
        LOGGER.prefix = "(Pipeline %d) " % (self.myid)

        # Queue for individual csv entries
        self.data_queue = queue.Queue(maxsize=10000)
        # Queue for current/new entry comparison
        self.work_queue = queue.Queue(maxsize=10000)
        # Queue for shippers to send data
        self.insert_queue = queue.Queue(maxsize=10000)

        try:
            self.es = connectElastic(self.options.es_uri)
        except elasticsearch.exceptions.TransportError as e:
            LOGGER.critical("Unable to establish elastic connection")
            return

        self.startup_rest()

        LOGGER.debug("Starting Reader")
        self.reader_thread = DataReader(self.datafile_queue,
                                        self.data_queue,
                                        self.eventTracker,
                                        self.options)
        self.reader_thread.start()

        # Wait to shutdown/finish
        while 1:
            if self.eventTracker.shutdown:
                LOGGER.debug("Shutdown event received")
                self.shutdown()
                break

            if self.pause_request.value:
                self._pause()
                while self.pause_request.value:
                    time.sleep(.1)
                self._unpause()

            self.reader_thread.join(.1)
            if not self.reader_thread.isAlive():
                LOGGER.debug("Reader thread exited, finishing up")
                self.finish()
                break

            time.sleep(.1)
        LOGGER.debug("Pipeline Shutdown")
        self._complete.value = True


def parse_domain(domainName):
    parts = domainName.rsplit('.', 1)
    return (parts[0], parts[1])


def configTemplate(es, major, data_template, options):
    if data_template is not None:
        # Process version specific template info
        if major == 5:
            # ES5 Templates use the "template" field
            data_template["template"] = options.indexNames.template_pattern
            # Disable "_all" field since it is handled customly, instead
            data_template["mappings"]["doc"]["_all"] = {
                "enabled": False
            }
        else:
            data_template["index_patterns"] = \
                [options.indexNames.template_pattern]

        # Shared template info
        data_template["aliases"][options.indexNames.search] = {}

        # Actually configure template
        es.indices.put_template(name=options.indexNames.template_name,
                                body=data_template)


def rolloverRequired(es, options):
    LOGGER.debug("Checking if rollover required")
    try:
        doc_count = int(es.cat.count(index=options.indexNames.orig_write,
                                     h="count"))
    except elasticsearch.exceptions.NotFoundError as e:
        LOGGER.warning("Unable to find required index\n")
    except Exception as e:
        LOGGER.exception("Unexpected exception\n")

    if doc_count > options.rollover_docs:
        return 1

    try:
        doc_count = int(es.cat.count(index=options.indexNames.delta_write,
                                     h="count"))
    except elasticsearch.exceptions.NotFoundError as e:
        LOGGER.warning("Unable to find required index\n")
    except Exception as e:
        LOGGER.exception("Unexpected exception\n")

    if doc_count > options.rollover_docs:
        return 2

    return 0


def rolloverIndex(roll, es, options, pipelines):

    if options.verbose:
        LOGGER.info("Rolling over ElasticSearch Index")

    # Pause the pipelines
    for proc in pipelines:
        proc.pause()

    LOGGER.debug("Waiting for pipelines to pause")
    # Ensure procs are paused
    for proc in pipelines:
        while not proc.paused:
            if proc.complete:
                break
            time.sleep(.1)
    LOGGER.debug("Pipelines paused")

    try:
        # Processing should have finished
        # Rollover the large index
        if roll == 1:
            write_alias = options.indexNames.orig_write
            search_alias = options.indexNames.orig_search
        elif roll == 2:
            write_alias = options.indexNames.delta_write
            search_alias = options.indexNames.delta_search

        try:
            orig_name = es.indices.get_alias(name=write_alias).keys()[0]
        except Exception as e:
            LOGGER.error("Unable to get/resolve index alias")

        try:
            result = es.indices.rollover(alias=write_alias,
                                         body={"aliases": {
                                                    search_alias: {}}})
        except Exception as e:
            LOGGER.exception("Unable to issue rollover command: %s")

        try:
            es.indices.refresh(index=orig_name)
        except Exception as e:
            LOGGER.exception("Unable to refresh rolled over index")

        # Index rolled over, restart processing
        for proc in pipelines:
            if not proc.complete:  # Only if process has data to process
                proc.unpause()

        if options.verbose:
            LOGGER.info("Roll over complete")

    except KeyboardInterrupt:
        LOGGER.warning(("Keyboard Interrupt ignored while rolling over "
                        "index, please wait a few seconds and try again"))


def main():
    eventTracker = EventTracker()
    parser = argparse.ArgumentParser()

    dataSource = parser.add_mutually_exclusive_group()
    dataSource.add_argument("-f", "--file", action="store", dest="file",
                            default=None, help="Input CSV file")
    dataSource.add_argument("-d", "--directory", action="store",
                            dest="directory", default=None,
                            help=("Directory to recursively search for CSV "
                                  "files -- mutually exclusive to '-f' "
                                  "option"))

    parser.add_argument("-e", "--extension", action="store", dest="extension",
                        default='csv',
                        help=("When scanning for CSV files only parse "
                              "files with given extension (default: 'csv')"))

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("-i", "--identifier", action="store", dest="identifier",
                      type=int, default=None,
                      help=("Numerical identifier to use in update to "
                            "signify version (e.g., '8' or '20140120')"))
    mode.add_argument("-r", "--redo", action="store_true", dest="redo",
                      default=False,
                      help=("Attempt to re-import a failed import or import "
                            "more data, uses stored metadata from previous "
                            "import (-o, -n, and -x not required and will "
                            "be ignored!!)"))
    mode.add_argument("-z", "--update", action="store_true", dest="update",
                      default=False,
                      help=("Run the script in update mode. Intended for "
                            "taking daily whois data and adding new domains "
                            "to the current existing index in ES."))
    mode.add_argument("--config-template-only", action="store_true",
                      default=False, dest="config_template_only",
                      help=("Configure the ElasticSearch template and "
                            "then exit"))

    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose",
                        default=False, help="Be verbose")
    parser.add_argument("--vverbose", action="store_true", dest="vverbose",
                        default=False,
                        help=("Be very verbose (Prints status of every "
                              "domain parsed, very noisy)"))
    parser.add_argument("-s", "--stats", action="store_true", dest="stats",
                        default=False, help="Print out Stats after running")

    updateMethod = parser.add_mutually_exclusive_group()
    updateMethod.add_argument("-x", "--exclude", action="store",
                              dest="exclude", default="",
                              help=("Comma separated list of keys to exclude "
                                    "if updating entry"))
    updateMethod.add_argument("-n", "--include", action="store",
                              dest="include", default="",
                              help=("Comma separated list of keys to include "
                                    "if updating entry (mutually exclusive to "
                                    "-x)"))

    parser.add_argument("-o", "--comment", action="store", dest="comment",
                        default="", help="Comment to store with metadata")

    parser.add_argument("-u", "--es-uri", nargs="*", dest="es_uri",
                        default=['localhost:9200'],
                        help=("Location(s) of ElasticSearch Server (e.g., "
                              "foo.server.com:9200) Can take multiple "
                              "endpoints"))
    parser.add_argument("-p", "--index-prefix", action="store",
                        dest="index_prefix", default='pydat',
                        help=("Index prefix to use in ElasticSearch "
                              "(default: pydat)"))
    parser.add_argument("-B", "--bulk-size", action="store", dest="bulk_size",
                        type=int, default=1000,
                        help="Size of Bulk Elasticsearch Requests")
    parser.add_argument("-b", "--bulk-fetch-size", action="store",
                        dest="bulk_fetch_size", type=int, default=50,
                        help=("Number of documents to search for at a time "
                              "(default 50), note that this will be "
                              "multiplied by the number of indices you "
                              "have, e.g., if you have 10 pydat-<number> "
                              "indices it results in a request for 500 "
                              "documents"))
    parser.add_argument("--rollover-size", action="store", type=int,
                        dest="rollover_docs", default=50000000,
                        help=("Set the number of documents after which point "
                              "a new index should be created, defaults to "
                              "50 milllion, note that this is fuzzy since "
                              "the index count isn't continuously updated, "
                              "so should be reasonably below 2 billion per "
                              "ES shard and should take your ES "
                              "configuration into consideration"))

    parser.add_argument("--pipelines", action="store", dest="procs", type=int,
                        metavar="PIPELINES",
                        default=2, help="Number of pipelines, defaults to 2")
    parser.add_argument("--shipper-threads", action="store",
                        dest="shipper_threads", type=int, default=1,
                        help=("How many threads per pipeline to spawn to send "
                              "bulk ES messages. The larger your cluster, "
                              "the more you can increase this, defaults to 1"))
    parser.add_argument("--fetcher-threads", action="store",
                        dest="fetcher_threads", type=int, default=2,
                        help=("How many threads to spawn to search ES. The "
                              "larger your cluster, the more you can "
                              "increase this, defaults to 2"))
    parser.add_argument("--ignore-field-prefixes", nargs='*',
                        dest="ignore_field_prefixes", type=str,
                        default=['zoneContact',
                                 'billingContact',
                                 'technicalContact'],
                        help=("list of fields (in whois data) to ignore when "
                              "extracting and inserting into ElasticSearch"))

    parser.add_argument("--debug", action="store_true", default=False,
                        help="Enables debug logging")

    options = parser.parse_args()

    if options.vverbose:
        options.verbose = True

    options.firstImport = False
    options.rolledOver = False

    # As these are crafted as optional args, but are really a required
    # mutually exclusive group, must check that one is specified
    if (not options.config_template_only and
            (options.file is None and options.directory is None)):
        print("A File or Directory source is required")
        parser.parse_args(["-h"])

    # Setup logger
    logger = mpLogger(name="populater", debug=options.debug)
    logger.start()

    global LOGGER
    LOGGER = logger.getLogger()
    LOGGER.prefix = "(Main) "

    # Local Logger instance since myLogger relies on a queue
    # This can cause an issue if exiting since it doesn't give
    # it enough time to run through the queue
    myLogger = logger.logger

    # Resolve index names based on prefix information
    indexNames = indexFormatter(options.index_prefix)
    # Shove it into options
    options.indexNames = indexNames

    # Setup Data Queue
    datafile_queue = jmpQueue(maxsize=10000)

    # Grab elasticsearch python library version
    major = elasticsearch.VERSION[0]

    # Verify connectivity and version(s) of cluster
    try:
        es = connectElastic(options.es_uri)
    except elasticsearch.exceptions.TransportError as e:
        myLogger.exception("Unable to connect to ElasticSearch")
        sys.exit(1)

    try:
        es_versions = []
        for version in es.cat.nodes(h='version').strip().split('\n'):
            es_versions.append([int(i) for i in version.split('.')])
    except Exception as e:
        myLogger.exception(("Unable to retrieve destination ElasticSearch "
                            "version"))
        sys.exit(1)

    es_major = 0
    for version in es_versions:
        if version[0] > es_major:
            es_major = version[0]
        if version[0] < 5 or (version[0] >= 5 and version[1] < 2):
            myLogger.error(("Destination ElasticSearch version must be "
                            "5.2 or greater"))
            sys.exit(1)

    if es_major != major:
        myLogger.error(("Python library installed does not "
                       "match with greatest (major) version in cluster"))
        sys.exit(1)

    # Setup template
    data_template = None
    base_path = os.path.dirname(os.path.realpath(__file__))
    template_path = os.path.join(base_path, "es_templates", "data.template")

    if not os.path.exists(template_path):
        myLogger.error("Unable to find template at %s" % (template_path))
        sys.exit(1)

    with open(template_path, 'r') as dtemplate:
        try:
            data_template = json.loads(dtemplate.read())
        except Exception as e:
            myLogger.exception("Unable to read template file")
            sys.exit(1)

    if options.config_template_only:
        configTemplate(es, major, data_template, options)
        sys.exit(0)

    metadata = None
    version_identifier = 0
    previousVersion = 0

    # Create the stats tracker thread
    statTracker = StatTracker()
    statTracker.daemon = True
    statTracker.start()

    # Create the metadata index if it doesn't exist
    if not es.indices.exists(indexNames.meta):
        if options.redo or options.update:
            myLogger.error(("Script cannot conduct a redo or update when no "
                            "initial data exists"))
            sys.exit(1)

        if options.identifier <= 0:
            myLogger.error("Identifier must be greater than 0")
            sys.exit(1)

        version_identifier = options.identifier

        # Setup the template
        configTemplate(es, major, data_template, options)

        # Create the metadata index with only 1 shard, even with
        # thousands of imports this index shouldn't warrant multiple shards
        # Also use the keyword analyzer since string analysis is not important
        meta_body = {"settings":
                     {"index":
                      {"number_of_shards": 1,
                       "analysis":
                       {"analyzer":
                        {"default":
                         {"type": "keyword"}}}}}}
        es.indices.create(index=indexNames.meta,
                          body=meta_body)

        # Create the 0th metadata entry
        metadata = {"metadata": 0,
                    "firstVersion": options.identifier,
                    "lastVersion": options.identifier}

        es.create(index=indexNames.meta,
                  doc_type=META_DOC_TYPE,
                  id=0,
                  body=metadata)

        # Create the first whois rollover index
        index_name = "%s-000001" % (options.index_prefix)
        es.indices.create(index=index_name,
                          body={"aliases": {indexNames.orig_write: {},
                                            indexNames.orig_search: {}}})

        # Create the first whois delta rollover index
        delta_name = "%s-delta-000001" % (options.index_prefix)
        es.indices.create(index=delta_name,
                          body={"aliases": {indexNames.delta_write: {},
                                            indexNames.delta_search: {}}})

        options.firstImport = True
    else:  # Data exists in the cluster
        try:
            result = es.get(index=indexNames.meta, doc_type=DOC_TYPE, id=0)
            if result['found']:
                metadata = result['_source']
            else:
                myLogger.error("Metadata index found but contains no data!!")
                sys.exit(1)
        except Exception as e:
            myLogger.exception("Error fetching metadata from index")
            sys.exit(1)

        if options.identifier is not None:
            if options.identifier < 1:
                myLogger.error("Identifier must be greater than 0")
                sys.exit(1)
            if metadata['lastVersion'] >= options.identifier:
                myLogger.error(("Identifier must be 'greater than' "
                                "previous identifier"))
                sys.exit(1)

            version_identifier = options.identifier
            previousVersion = metadata['lastVersion']
        else:  # redo or update
            result = es.search(index=indexNames.meta,
                               body={"query": {"match_all": {}},
                                     "sort": [{"metadata":
                                              {"order": "asc"}}],
                                     "size": 9999})

            if result['hits']['total'] == 0:
                myLogger.error("Unable to fetch entries from metadata index\n")
                sys.exit(1)

            lastEntry = result['hits']['hits'][-1]['_source']
            previousVersion = int(result['hits']['hits'][-2]['_id'])
            version_identifier = int(metadata['lastVersion'])
            if options.redo and (lastEntry.get('updateVersion', 0) > 0):
                myLogger.error(("A Redo is only valid on recovering from a "
                                "failed import via the -i flag.\nAfter "
                                "ingesting a daily update, it is no longer "
                                "available"))
                sys.exit(1)

    options.previousVersion = previousVersion
    options.updateVersion = 0

    if options.exclude != "":
        options.exclude = options.exclude.split(',')
    else:
        options.exclude = None

    if options.include != "":
        options.include = options.include.split(',')
    else:
        options.include = None

    # Redo or Update Mode
    if options.redo or options.update:
        # Get the record for the attempted import
        version_identifier = int(metadata['lastVersion'])
        options.identifier = version_identifier
        try:
            previous_record = es.get(index=indexNames.meta,
                                     doc_type=DOC_TYPE,
                                     id=version_identifier)['_source']
        except Exception as e:
            myLogger.exception(("Unable to retrieve information "
                                "for last import"))
            sys.exit(1)

        if 'excluded_keys' in previous_record:
            options.exclude = previous_record['excluded_keys']
        elif options.redo:
            options.exclude = None

        if 'included_keys' in previous_record:
            options.include = previous_record['included_keys']
        elif options.redo:
            options.include = None

        options.comment = previous_record['comment']

        statTracker.seed({'total': int(previous_record['total']),
                          'new': int(previous_record['new']),
                          'updated': int(previous_record['updated']),
                          'unchanged': int(previous_record['unchanged']),
                          'duplicates': int(previous_record['duplicates'])})

        if options.update:
            options.updateVersion = \
                int(previous_record.get('updateVersion', 0)) + 1

        statTracker.seedChanged(previous_record['changed_stats'])

        if options.verbose:
            if options.redo:
                myLogger.info(("Re-importing for: \n\tIdentifier: "
                               "%s\n\tComment: %s")
                              % (version_identifier, options.comment))
            else:
                myLogger.info(("Updating for: \n\tIdentifier: %s\n\t"
                               "Comment: %s")
                              % (version_identifier, options.comment))

        # No need to update lastVersion or create metadata entry
    # Insert(normal) Mode
    else:
        # Update the lastVersion in the metadata
        es.update(index=indexNames.meta, id=0,
                  doc_type=META_DOC_TYPE,
                  body={'doc': {'lastVersion': options.identifier}})

        # Create the entry for this import
        meta_struct = {'metadata': options.identifier,
                       'updateVersion': 0,
                       'comment': options.comment,
                       'total': 0,
                       'new': 0,
                       'updated': 0,
                       'unchanged': 0,
                       'duplicates': 0,
                       'changed_stats': {}}

        if options.exclude is not None:
            meta_struct['excluded_keys'] = options.exclude
        elif options.include is not None:
            meta_struct['included_keys'] = options.include

        es.create(index=indexNames.meta, id=options.identifier,
                  doc_type=META_DOC_TYPE,  body=meta_struct)

        # Resolve the alias to get the raw index names
    index_list = es.indices.get_alias(name=indexNames.orig_search)
    options.INDEX_LIST = sorted(index_list.keys(), reverse=True)

    pipelines = []
    # Check if rollover is required before starting any pipelines
    roll = rolloverRequired(es, options)
    if roll:
        rolloverIndex(roll, es, options, pipelines)

    # Everything configured -- start it up
    # Start up Reader Thread
    reader_thread = FileReader(datafile_queue, eventTracker, options)
    reader_thread.daemon = True
    reader_thread.start()

    for pipeline_id in range(options.procs):
        p = DataProcessor(pipeline_id, datafile_queue, statTracker, logger,
                          eventTracker, options)
        p.start()
        pipelines.append(p)

    # Everything should be running at this point

    try:
        # Rollover check sequence
        def rolloverTimer(timer):
            now = time.time()
            # Check every 30 seconds
            if now - timer >= 30:
                timer = now
                roll = rolloverRequired(es, options)
                if roll:
                    rolloverIndex(roll, es, options, pipelines)

            return timer

        timer = time.time()
        while True:
            timer = rolloverTimer(timer)

            # If bulkError occurs stop processing
            if eventTracker.bulkError:
                myLogger.critical("Bulk API error -- forcing program shutdown")
                raise KeyboardInterrupt(("Error response from ES worker, "
                                         "stopping processing"))

            # Wait for the pipelines to clear out the datafile queue
            # This means all files are currently being looked at or have
            # been processed
            if not reader_thread.isAlive() and datafile_queue.empty():
                if options.verbose:
                    myLogger.info(("All files processed ... please wait for "
                                   "processing to complete ..."))
                break

            time.sleep(.1)

        # Wait on pipelines to finish up
        for proc in pipelines:
            while proc.is_alive():
                timer = rolloverTimer(timer)
                proc.join(.1)

                if eventTracker.bulkError:
                    myLogger.critical(("Bulk API error -- forcing program "
                                       "shutdown"))
                    raise KeyboardInterrupt(("Error response from ES worker, "
                                             "stopping processing"))

        try:
            # Since this is the shutdown section, ignore Keyboard Interrupts
            # especially since the interrupt code (below) does effectively
            # the same thing

            statTracker.shutdown()
            statTracker.join()

            # Update the stats
            try:
                es.update(index=indexNames.meta,
                          id=version_identifier,
                          doc_type=META_DOC_TYPE,
                          body={'doc': {'updateVersion': options.updateVersion,
                                        'total': statTracker.total,
                                        'new': statTracker.new,
                                        'updated': statTracker.updated,
                                        'unchanged': statTracker.unchanged,
                                        'duplicates': statTracker.duplicates,
                                        'changed_stats':
                                        statTracker.changed_stats}})
            except Exception as e:
                myLogger.exception("Error attempting to update stats")
        except KeyboardInterrupt:
            myLogger.info("Please wait for processing to complete ...")

        try:
            datafile_queue.close()
        except Exception as e:
            myLogger.debug("Exception closing queues", exc_info=True)

        if options.verbose:
            myLogger.info("Done ...")

        if options.stats:
            myLogger.info("\nStats:\n"
                          + "Total Entries:\t\t %d\n" % statTracker.total
                          + "New Entries:\t\t %d\n" % statTracker.new
                          + "Updated Entries:\t %d\n" % statTracker.updated
                          + "Duplicate Entries\t %d\n" % statTracker.duplicates
                          + "Unchanged Entries:\t %d\n"
                            % statTracker.unchanged)

        # Ensure logger processes all messages
        logger.join()
    except KeyboardInterrupt as e:
        myLogger.warning(("Cleaning Up ... Please Wait ...\nWarning!! "
                          "Forcefully killing this might leave Elasticsearch "
                          "in an inconsistent state!"))
        # Tell the reader to halt activites
        reader_thread.shutdown()

        # Flush the queue if the reader is alive so it can see the
        # shutdown event in case it's blocked on a put
        myLogger.info("Shutting down input reader threads ...")
        while reader_thread.is_alive():
            try:
                datafile_queue.get_nowait()
                datafile_queue.task_done()
            except queue.Empty:
                break

        myLogger.debug("Draining data queue")
        # Drain the data file queue
        while not datafile_queue.empty():
            try:
                datafile_queue.get_nowait()
                datafile_queue.task_done()
            except queue.Empty:
                break

        reader_thread.join()

        # Signal the pipeline procs to shutdown
        eventTracker.setShutdown()

        myLogger.info("Shutting down processing pipelines...")
        for proc in pipelines:
            while proc.is_alive():
                proc.join(.1)

        myLogger.debug("Pipelines shutdown, cleaning up state")
        # Send the finished message to the stats queue to shut it down
        statTracker.shutdown()
        statTracker.join()

        # Attempt to update the stats
        try:
            myLogger.info("Finalizing metadata")
            es.update(index=indexNames.meta,
                      id=options.identifier,
                      doc_type=META_DOC_TYPE,
                      body={'doc': {'total': statTracker.total,
                                    'new': statTracker.new,
                                    'updated': statTracker.updated,
                                    'unchanged': statTracker.unchanged,
                                    'duplicates': statTracker.duplicates,
                                    'changed_stats':
                                    statTracker.changed_stats}})
        except Exception as e:
            myLogger.warning(("Unable to finalize stats, data may be out of "
                              "sync"), exc_info=True)

        myLogger.info("Finalizing settings")
        try:
            datafile_queue.close()
        except Exception as e:
            myLogger.debug("Exception closing queues", exc_info=True)

        myLogger.info("... Done")

        # Ensure logger processes all messages
        logger.join()
        sys.exit(0)


if __name__ == "__main__":
    main()
