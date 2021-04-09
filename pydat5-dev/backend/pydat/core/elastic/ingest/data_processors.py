#!/usr/bin/env python

import os
import csv
import time
import hashlib
import logging
from threading import Thread

from html.parser import HTMLParser
import queue

from elasticsearch import helpers

from pydat.core.elastic.ingest.debug_levels import DebugLevel


# Notes
# 'track_total_hits' required on search to get accurate total hits
# routing less helpful in low shard-count setups


def _generateDocId(domainName):
    try:
        (domain, tld) = domainName.rsplit('.', 1)
    except Exception:
        raise RuntimeError(f"Unable to parse domain '{domainName}'")

    if len(domain) > 200:
        dhash = hashlib.sha1(bytes(domain, 'utf-8')).hexdigest()
        domain = f"h.{dhash}"
    return f"{tld}.{domain}"


class DataReader(Thread):
    """CSV Parsing Class

    This class focuses on reading in and parsing a given CSV file as
    provided by the FileReader class. After creating its output it
    places it on a queue for processing by the fetcher
    """

    def __init__(
        self,
        pipelineid,
        file_queue,
        data_queue,
        eventTracker,
        process_options,
        logger=None
    ):
        super().__init__()
        self.myid = pipelineid

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger(f'dataReader.{self.myid}')

        self.file_queue = file_queue
        self.data_queue = data_queue
        self.eventTracker = eventTracker
        self.verbose = process_options.verbose
        self.debug = process_options.debug
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
                datafile = self.file_queue.get(True, 0.2)
                try:
                    self.parse_csv(datafile)
                finally:
                    self.file_queue.task_done()
            except queue.Empty:
                if self.eventTracker.fileReaderDone:
                    self.logger.debug("FileReaderDone Event seen")
                    break
            except Exception:
                self.logger.exception("Unhandled Exception")
        self.logger.debug("Reader exiting")

    def check_header(self, header):
        for field in header:
            if field == "domainName":
                return True

        return False

    def parse_csv(self, filename):
        if self._shutdown:
            return

        try:
            csvfile = open(filename, newline='')
            s = os.stat(filename)
            if s.st_size == 0:
                self.logger.warning("File %s empty" % filename)
                return
        except Exception:
            self.logger.warning("Unable to stat file %s, skiping" % filename)
            return

        if self.verbose:
            self.logger.info("Processing file: %s" % filename)

        try:
            dnsreader = csv.reader(csvfile, strict=True, skipinitialspace=True)
        except Exception:
            self.logger.exception(
                f"Unable to setup csv reader for file {filename}")
            return

        try:
            header = next(dnsreader)
        except Exception:
            self.logger.exception(
                f"Unable to iterate through csv file {filename}")
            return

        try:
            if not self.check_header(header):
                raise csv.Error('CSV header not found')

            for row in dnsreader:
                while self._pause:
                    if self._shutdown:
                        if self.debug >= DebugLevel.VERBOSE:
                            self.logger.debug("Shutdown received while paused")
                        break
                    time.sleep(.5)
                if self._shutdown:
                    if self.debug >= DebugLevel.VERBOSE:
                        self.logger.debug("Shutdown received")
                    break
                if row is None or not row:
                    self.logger.warning(
                        f"Skipping empty row in file {filename}"
                    )
                    continue
                self.data_queue.put({'header': header, 'row': row})
        except csv.Error:
            self.logger.exception(
                "CSV Parse Error in file %s - line %i\n" % (
                    os.path.basename(filename),
                    dnsreader.line_num)
            )
        except Exception:
            self.logger.exception(
                f"Unable to process file {filename}")


class DataFetcher(Thread):
    """Bulk Fetching of Records

    This class does a bulk fetch of records to make the comparison of
    records more efficient. It takes the response and bundles it up with
    the source to be sent to the worker
    """

    def __init__(
        self,
        pipelineid,
        fetcherid,
        data_queue,
        work_queue,
        eventTracker,
        es,
        index_list,
        skip_fetch,
        process_options,
        logger=None
    ):
        super().__init__()
        self.myid = f"{pipelineid}.{fetcherid}"

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger(f'fetcher.{self.myid}')

        self.data_queue = data_queue
        self.work_queue = work_queue
        self.es = es
        self.fetcher_threads = []
        self.eventTracker = eventTracker
        self.bulk_fetch_size = process_options.bulk_fetch_size
        self.skip_fetch = skip_fetch
        self.ignore_field_prefixes = process_options.ignore_field_prefixes
        self.verbose = process_options.verbose
        self.debug = process_options.debug
        self.version = process_options.version
        self.ingest_day = process_options.ingest_day
        self.ingest_now = process_options.ingest_now
        self.index_list = index_list
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
                except queue.Empty:
                    if self._finish:
                        if len(fetch) > 0:
                            data = self.handle_fetch(fetch)
                            for item in data:
                                self.work_queue.put(item)
                        break
                    time.sleep(.01)
                    continue
                except Exception:
                    self.logger.exception("Unhandled Exception")
                    continue

                try:
                    entry = self.parse_entry(work['row'], work['header'])
                    if entry is None:
                        self.logger.warning("Malformed Entry")
                        continue

                    # Pre-empt all of this processing when not necessary
                    if (self.skip_fetch):
                        self.work_queue.put((entry, None))
                        continue

                    doc_id = _generateDocId(entry['domainName'])
                    fetch.append((doc_id, entry))

                    if len(fetch) >= self.bulk_fetch_size:
                        data = self.handle_fetch(fetch)
                        for item in data:
                            self.work_queue.put(item)
                        fetch = list()
                except Exception:
                    self.logger.exception("Unhandled Exception")
                finally:
                    self.data_queue.task_done()

        except Exception:
            self.logger.exception("Unhandled Exception")

    def parse_entry(self, input_entry, header):
        if len(input_entry) == 0:
            return None

        htmlparser = HTMLParser()

        details = {}
        domainName = ''
        for (i, item) in enumerate(input_entry):
            if any(header[i].startswith(s)
                    for s in self.ignore_field_prefixes):
                continue
            if header[i] == 'domainName':
                if self.debug >= DebugLevel.NOISY:
                    self.logger.debug("Processing domain: %s" % item)
                domainName = item
                continue
            if item == "":
                details[header[i]] = None
            else:
                details[header[i]] = htmlparser.unescape(item)

        entry = {
            self.es.metadata_key_map.VERSION_KEY: self.version,
            self.es.metadata_key_map.FIRST_SEEN: self.version,
            self.es.metadata_key_map.DATE_FIRST_SEEN: self.ingest_day,
            self.es.metadata_key_map.DATE_LAST_SEEN: self.ingest_day,
            self.es.metadata_key_map.DATE_CREATED: self.ingest_now,
            self.es.metadata_key_map.DATE_UPDATED: self.ingest_now,
            self.es.metadata_key_map.HISTORICAL: False,
            'tld': parse_domain(domainName)[1],
            'details': details,
            'domainName': domainName}

        return entry

    def handle_fetch(self, fetch_list):
        results = list()
        try:
            docs = list()
            for (doc_id, entry) in fetch_list:
                for index_name in self.index_list:
                    getdoc = {
                        '_index': index_name,
                        '_id': doc_id,
                    }
                    docs.append(getdoc)
        except Exception:
            self.logger.exception("Unable to generate doc list")
            return results

        try:
            result = self.es.connect().mget(body={"docs": docs})
        except Exception:
            self.logger.exception("Unable to create mget request")
            return results

        try:
            for (doc_count, index) in \
                    enumerate(range(0, len(result['docs']),
                              len(self.index_list))):
                found = None
                doc_results = \
                    result['docs'][index:index + len(self.index_list)]

                for res in doc_results:
                    if res['found']:
                        found = res
                        break

                if found is not None:
                    results.append((fetch_list[doc_count][1], found))
                else:
                    results.append((fetch_list[doc_count][1], None))

            return results
        except Exception:
            self.logger.exception("Unhandled Exception")


class DataWorker(Thread):
    """Class to focus on entry comparison and instruction creation

    This class takes the input entry and latest entry as found by the fetcher
    and creates one or more elasticsearch update requests to be sent by the
    shipper
    """

    def __init__(
        self,
        pipelineid,
        work_queue,
        insert_queue,
        statTracker,
        eventTracker,
        es,
        process_options,
        logger=None,
    ):
        super().__init__()
        self.myid = pipelineid

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger(f'worker.{self.myid}')

        self.es = es
        self.work_queue = work_queue
        self.insert_queue = insert_queue
        self.statTracker = statTracker
        self.eventTracker = eventTracker
        self._shutdown = False
        self._finish = False
        self.version = process_options.version
        self.reingest = process_options.reingest
        self.include_fields = process_options.include_fields
        self.exclude_fields = process_options.exclude_fields
        self.ingest_day = process_options.ingest_day
        self.ingest_now = process_options.ingest_now
        self.verbose = process_options.verbose
        self.debug = process_options.debug

    def shutdown(self):
        self._shutdown = True

    def finish(self):
        self._finish = True

    def run(self):
        try:
            while not self._shutdown:
                try:
                    (entry, current_entry_raw) = self.work_queue.get_nowait()
                except queue.Empty:
                    if self._finish:
                        break
                    time.sleep(.0001)
                    continue
                except Exception:
                    self.logger.exception("Unhandled Exception")

                try:
                    if entry is None:
                        self.logger.warning("Malformed Entry")
                        continue

                    if (not self.reingest or
                            self.update_required(current_entry_raw)):
                        self.statTracker.incr('total')
                        self.process_entry(entry, current_entry_raw)
                finally:
                    self.work_queue.task_done()

        except Exception:
            self.logger.exception("Unhandled Exception")

    def update_required(self, current_entry):
        if current_entry is None:
            return True

        if current_entry['_source'][
                self.es.metadata_key_map.VERSION_KEY] == self.version:
            # This record already up to date
            return False
        else:
            return True

    def _process_update(self, entry, current_entry_raw):
        api_commands = []
        domainName = entry['domainName']
        details = entry['details']

        current_index = current_entry_raw['_index']
        current_id = current_entry_raw['_id']
        current_entry = current_entry_raw['_source']

        if ((current_entry[
                self.es.metadata_key_map.VERSION_KEY] == self.version)):
            # Duplicate entry in source csv's?
            if self.debug >= DebugLevel.VERBOSE:
                self.logger.debug('%s: Duplicate' % domainName)
            self.statTracker.incr('duplicates')
            return api_commands

        if self.exclude_fields is not None:
            details_copy = details.copy()
            for exclude in self.exclude_fields:
                del details_copy[exclude]

            changed = (
                set(details_copy.items()) -
                set(current_entry['details'].items()))

        elif self.include_fields is not None:
            details_copy = {}
            for include in self.include_fields:
                try:  # TODO
                    details_copy[include] = details[include]
                except Exception:
                    pass

            changed = (
                set(details_copy.items()) -
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
            if self.debug >= DebugLevel.NOISY:
                self.logger.info("%s: Updated" % domainName)

            # Copy old entry into different document
            current_entry['historical'] = True
            doc_id = (
                f"{current_id}#"
                f"{current_entry[self.es.metadata_key_map.VERSION_KEY]}"
            )
            if self.debug >= DebugLevel.NOISY:
                self.logger.debug("doc_id: %s" % doc_id)
            api_commands.append(
                self.process_command(
                    'create',
                    self.es.indexNames.delta_write,
                    doc_id,
                    current_entry))

            # Update latest/orig entry
            entry[self.es.metadata_key_map.FIRST_SEEN] = current_entry[
                self.es.metadata_key_map.FIRST_SEEN]
            entry[self.es.metadata_key_map.DATE_FIRST_SEEN] = current_entry[
                self.es.metadata_key_map.DATE_FIRST_SEEN]
            entry[self.es.metadata_key_map.DATE_CREATED] = current_entry[
                self.es.metadata_key_map.DATE_CREATED]
            api_commands.append(self.process_command(
                'index',
                current_index,
                current_id,
                entry))
        else:
            self.statTracker.incr('unchanged')
            if self.debug >= DebugLevel.NOISY:
                self.logger.info("%s: Unchanged" % domainName)
            doc_diff = {'doc': {
                self.es.metadata_key_map.VERSION_KEY: self.version,
                self.es.metadata_key_map.DATE_LAST_SEEN: self.ingest_day,
                self.es.metadata_key_map.DATE_UPDATED: self.ingest_now,
                'details': details
                }
            }
            api_commands.append(
                self.process_command(
                    'update',
                    current_index,
                    current_id,
                    doc_diff))

        return api_commands

    def _process_new(self, entry):
        domainName = entry['domainName']
        api_commands = []

        self.statTracker.incr('new')
        if self.debug >= DebugLevel.NOISY:
            self.logger.debug("%s: New" % domainName)
        doc_id = _generateDocId(domainName)
        api_commands.append(
            self.process_command(
                'create',
                self.es.indexNames.orig_write,
                doc_id,
                entry))

        return api_commands

    def process_entry(self, entry, current_entry_raw):
        api_commands = []

        if current_entry_raw is not None:
            api_commands.extend(self._process_update(entry, current_entry_raw))
        else:
            api_commands.extend(self._process_new(entry))

        for command in api_commands:
            self.insert_queue.put(command)

    def process_command(self, request, index, _id, entry=None):
        if request == 'create':
            command = {
                       "_op_type": "create",
                       "_index": index,
                       "_id": _id,
                       "_source": entry
                      }
            return command
        elif request == 'update':
            command = {
                       "_op_type": "update",
                       "_index": index,
                       "_id": _id,
                      }
            command.update(entry)
            return command
        elif request == 'delete':
            command = {
                        "_op_type": "delete",
                        "_index": index,
                        "_id": _id,
                      }
            return command
        elif request == 'index':
            command = {
                        "_op_type": "index",
                        "_index": index,
                        "_source": entry
                      }
            if _id is not None:
                command["_id"] = _id
            return command
        else:
            self.logger.error("Unrecognized command")
            return None


class DataShipper(Thread):
    """Thread that ships commands to elasticsearch cluster_stats
    """

    def __init__(
        self,
        pipelineid,
        shipperid,
        es,
        insert_queue,
        eventTracker,
        process_options,
        logger=None
    ):
        super().__init__()
        self.myid = f"{pipelineid}.{shipperid}"

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger(f'shipper.{self.myid}')

        self.insert_queue = insert_queue
        self.bulk_ship_size = process_options.bulk_ship_size
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
                    helpers.streaming_bulk(self.es.connect(), bulkIter(),
                                           raise_on_error=False,
                                           chunk_size=self.bulk_ship_size):
                resp = response[list(response)[0]]
                if not ok and resp['status'] not in [404, 409]:
                    if not self.eventTracker.bulkError:
                        self.eventTracker.setBulkError()
                    self.logger.debug("Response: %s" % (str(resp)))
                    self.logger.error((
                        "Error making bulk request, received "
                        "error reason: %s")
                            % (resp['error']['reason']))
        except Exception:
            self.logger.exception("Unexpected error processing bulk commands")
            if not self.eventTracker.bulkError:
                self.eventTracker.setBulkError


def parse_domain(domainName):
    parts = domainName.rsplit('.', 1)
    try:
        return parts[0], parts[1]
    except IndexError:
        raise
