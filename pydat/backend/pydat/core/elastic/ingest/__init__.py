import os
import time
import datetime
from multiprocessing import (
    JoinableQueue as jmpQueue
)
import json

import queue

from pydat.core.logger import mpLogger, getLogger
from pydat.core.elastic.ingest.event_tracker import EventTracker
from pydat.core.elastic.ingest.stat_tracker import StatTracker
from pydat.core.elastic.ingest.ingest_handler import (
    IngestHandler,
    RolloverRequired
)
from pydat.core.elastic.ingest.process_wrapper import (
    DataProcessorPool,
    PopulatorOptions
)
from pydat.core.elastic.ingest.file_reader import FileReader
from pydat.core.elastic.ingest.debug_levels import DebugLevel


class InterruptedImportError(Exception):
    """Custom excpetion that represents an import was previously interrupted
    and must be handled before more data can be ingested
    """
    pass


class NoDataError(Exception):
    """Custom exception that represents that data was not present in the
    cluster when it was expected to be so
    """
    pass


class MetadataError(Exception):
    """Custom exception that indicates there was an issue processing a
    metadata records
    """
    pass


class DataPopulator:
    def __init__(
        self,
        elastic_args,
        include_fields,
        exclude_fields,
        ingest_day,
        ignore_field_prefixes,
        pipelines=2,
        template_path=None,
        ingest_directory=None,
        ingest_file=None,
        extension="csv",
        comment="",
        bulk_fetch_size=50,
        bulk_ship_size=1000,
        num_shipper_threads=2,
        num_fetcher_threads=2,
        verbose=False,
        debug=False,
    ):

        self.firstImport = False
        self.rolledOver = False
        self.ingest_now = datetime.datetime.now().strftime("%Y-%m-%d")
        self.version = -1

        self.pipelines = pipelines
        if template_path is not None:
            self.template_path = template_path
        else:
            # Template location
            base_path = os.path.dirname(os.path.realpath(__file__))
            self.template_path = os.path.join(
                base_path,
                "../templates"
            )

        self.elastic_args = elastic_args
        self.include_fields = include_fields
        self.exclude_fields = exclude_fields
        self.comment = comment
        self.verbose = verbose
        self.debug = debug
        self.ignore_field_prefixes = ignore_field_prefixes
        self.bulk_fetch_size = bulk_fetch_size
        self.bulk_ship_size = bulk_ship_size
        self.ingest_directory = ingest_directory
        self.ingest_file = ingest_file
        self.extension = extension
        self.ingest_day = ingest_day
        self.num_fetcher_threads = num_fetcher_threads
        self.num_shipper_threads = num_shipper_threads
        self.file_queue = jmpQueue(maxsize=10000)

        self.mplogger = mpLogger(debug=debug)
        self.mplogger.start()

        self.logger = getLogger(
            "DataPopulator",
            debug=self.debug,
            mpSafe=False
        )

        self.elastic_handler = IngestHandler(**self.elastic_args)

        self.eventTracker = EventTracker()
        self.statTracker = StatTracker()

        self.readerThread = FileReader(
            self.file_queue,
            self.eventTracker,
            self.ingest_directory,
            self.ingest_file,
            self.extension
        )

        self.dataProcessorPool = None

    def _getTemplate(self):
        es = self.elastic_handler

        es_version = es.getVersion()

        # Read template
        template_path = os.path.join(
            self.template_path, f"es{es_version}.data.template")

        if not os.path.exists(template_path):
            raise ValueError(f"Unable to find template at {template_path}")

        with open(template_path, 'r') as dtemplate:
            try:
                data_template = json.loads(dtemplate.read())
            except Exception:
                raise RuntimeError("Unable to read template file")

        return data_template

    def configTemplate(self):
        template = self._getTemplate()
        # TODO FIXME add confirmation output information
        self.elastic_handler.configTemplate(template)

    def clearInterrupted(self):
        self.elastic_handler.clearInterrupted()

    def _handleShutdown(self):
        try:
            # Since this is the shutdown section, ignore Keyboard Interrupts
            # especially since the interrupt code (below) does effectively
            # the same thing

            if self.debug >= DebugLevel.VERBOSE:
                self.logger.debug("Cleaning up StatTracker")
            self.statTracker.shutdown()
            self.statTracker.join()

            if self.debug >= DebugLevel.VERBOSE:
                self.logger.debug("Updating Stats")
            # Update the stats
            try:
                self.elastic_handler.updateMetadata(
                    version=self.version,
                    body={'doc': {
                            'total': self.statTracker.total,
                            'new': self.statTracker.new,
                            'updated': self.statTracker.updated,
                            'unchanged': self.statTracker.unchanged,
                            'duplicates': self.statTracker.duplicates,
                            'changed_stats': self.statTracker.changed_stats
                        }
                    }
                )

                # Clear importing on finish
                self.elastic_handler.updateMetadata(
                    version=0,
                    body={
                        'doc': {
                            'importing': 0
                        }
                    }
                )
            except Exception:
                self.logger.exception("Error attempting to update stats")
        except KeyboardInterrupt:
            self.logger.info("Please wait for processing to complete ...")

        if self.debug >= DebugLevel.VERBOSE:
            self.logger.debug("Closing file queue")
        try:
            self.file_queue.close()
        except Exception:
            self.logger.debug("Exception closing queues", exc_info=True)

        if self.debug >= DebugLevel.VERBOSE:
            self.logger.debug("Refreshing Elastic Indices")
        try:
            self.elastic_handler.refreshIndices()
        except Exception:
            self.logger.exception("Unable to refresh indices")

        if self.verbose:
            self.logger.info("Done ...")

    def _handleCancel(self):
        # Tell the reader to halt activites
        self.readerThread.shutdown()

        # Flush the queue if the reader is alive so it can see the
        # shutdown event in case it's blocked on a put
        self.logger.info("Shutting down input reader threads ...")
        while self.readerThread.is_alive():
            try:
                self.file_queue.get_nowait()
                self.file_queue.task_done()
            except queue.Empty:
                break

        self.logger.debug("Draining data queue")
        # Drain the data file queue
        while not self.file_queue.empty():
            try:
                self.file_queue.get_nowait()
                self.file_queue.task_done()
            except queue.Empty:
                break

        self.logger.debug("Joining Reader Thread")
        self.readerThread.join()

        # Signal the pipeline procs to shutdown
        self.eventTracker.setShutdown()

        self.logger.info("Shutting down processing pipelines...")
        self.dataProcessorPool.join()

        self.logger.debug("Pipelines shutdown, cleaning up state")
        # Send the finished message to the stats queue to shut it down
        self.statTracker.shutdown()
        self.statTracker.join()

        try:
            self.elastic_handler.refreshIndices()
        except Exception:
            self.logger.exception("Unable to refresh indices")

        # Attempt to update the stats
        try:
            self.logger.info("Finalizing metadata")
            self.elastic_handler.updateMetadata(
                version=self.version,
                body={
                    'doc': {
                        'total': self.statTracker.total,
                        'new': self.statTracker.new,
                        'updated': self.statTracker.updated,
                        'unchanged': self.statTracker.unchanged,
                        'duplicates': self.statTracker.duplicates,
                        'changed_stats': self.statTracker.changed_stats
                    }
                }
            )
        except Exception:
            self.logger.warning((
                "Unable to finalize stats, data may be out of sync"),
                exc_info=True
            )

        self.logger.info("Finalizing settings")
        try:
            self.file_queue.close()
        except Exception:
            self.logger.debug("Exception closing queues", exc_info=True)

        self.logger.info("... Done")

    def _handleIngest(
        self,
        first_import=False,
        reingest=False,
        statsSeed=None
    ):
        # Start the stats tracker thread
        self.statTracker.start()

        if statsSeed is not None:
            self.statTracker.seed(statsSeed['stats'])
            self.statTracker.seedChanged(statsSeed['changed'])

        # Start up Reader Thread
        self.readerThread.start()

        self.process_options = PopulatorOptions(
            first_import=first_import,
            reingest=reingest,
            version=self.version,
            ingest_day=self.ingest_day,
            ingest_now=self.ingest_now,
            ignore_field_prefixes=self.ignore_field_prefixes,
            include_fields=self.include_fields,
            exclude_fields=self.exclude_fields,
            elastic_args=self.elastic_args,
            bulk_fetch_size=self.bulk_fetch_size,
            bulk_ship_size=self.bulk_ship_size,
            num_fetcher_threads=self.num_fetcher_threads,
            num_shipper_threads=self.num_shipper_threads,
            verbose=self.verbose,
            debug=self.debug,
        )

        # Start processing
        self.dataProcessorPool = DataProcessorPool(
            procs=self.pipelines,
            file_queue=self.file_queue,
            statTracker=self.statTracker,
            eventTracker=self.eventTracker,
            process_options=self.process_options,
        )

        self.dataProcessorPool.start()

        try:
            timer = time.time()
            while True:
                try:
                    timer = self.elastic_handler.rolloverTimer(timer)
                except RolloverRequired as rollOver:
                    timer = time.time()
                    self.dataProcessorPool.handleRollover(
                        write_alias=rollOver.write_alias,
                        search_alias=rollOver.search_alias
                    )

                # If bulkError occurs stop processing
                if self.eventTracker.bulkError:
                    self.logger.critical(
                        "Bulk API error -- forcing program shutdown")
                    raise KeyboardInterrupt(("Error response from ES worker, "
                                            "stopping processing"))

                # Wait for the pipelines to clear out the datafile queue
                # This means all files are currently being looked at or have
                # been processed
                if (not self.readerThread.is_alive()
                        and self.file_queue.empty()):
                    if self.verbose:
                        self.logger.info((
                            "All files processed ... please wait for "
                            "processing to complete ..."))
                    break

                time.sleep(.1)

            # Wait on pipelines to finish up
            self.dataProcessorPool.join()
            if self.debug >= DebugLevel.VERBOSE:
                self.logger.debug("Beginning Shutdown sequence")
            self._handleShutdown()
        except KeyboardInterrupt:
            self._handleCancel()

        self.mplogger.join()

    def ingest(self):
        first_import = False
        if not self.elastic_handler.metaExists:
            template = self._getTemplate()
            self.elastic_handler.initialize(template)
            self.version = 1
            first_import = True

        metadata = self.elastic_handler.metaRecord
        if metadata is None:
            raise MetadataError("Unable to get metadata from cluster")

        if not first_import:
            self.version = int(metadata['lastVersion']) + 1

        importing = int(metadata['importing'])
        import_interrupted = importing > 0

        if import_interrupted:
            raise InterruptedImportError(
                "Previous Import was interupted, please resolve")

        updateDoc = {
            'doc': {
                'importing': self.version,
                'lastVersion': self.version
            }
        }

        if metadata['lastVersion'] == 0:
            updateDoc['doc']['firstVersion'] = 1

        try:
            self.elastic_handler.updateMetadata(0, updateDoc)
        except Exception:
            raise MetadataError("Unable to update metadata record")

        # Create the entry for this import
        meta_struct = {'metadata': self.version,
                       'comment': self.comment,
                       'dateProcessed': self.ingest_now,
                       'dateIngest': self.ingest_day,
                       'total': 0,
                       'new': 0,
                       'updated': 0,
                       'unchanged': 0,
                       'duplicates': 0,
                       'changed_stats': {}}

        if self.exclude_fields is not None:
            meta_struct['excluded_keys'] = self.exclude_fields
        elif self.include_fields is not None:
            meta_struct['included_keys'] = self.include_fields

        try:
            self.elastic_handler.createMetadata(self.version, meta_struct)
        except Exception:
            raise MetadataError("Unable to create metadata record")

        self._handleIngest(first_import=first_import)

    def reingest(self):
        if not self.elastic_handler.metaExists:
            raise NoDataError(
                "Cannot reingest when no data exists in cluster")

        try:
            metadata = self.elastic_handler.metaRecord
        except Exception:
            raise MetadataError("Unable to retreive metadata record")

        importing = int(metadata['importing'])
        import_interrupted = importing > 0

        if import_interrupted:
            self.version = importing
        else:
            self.version = int(metadata['lastVersion'])

        try:
            previous_metadata = self.elastic_handler.getMetadata(
                metadata['lastVersion']
            )
        except Exception:
            raise MetadataError("Unable to get metadata record")

        if 'included_keys' in previous_metadata:
            self.include_fields = previous_metadata['included_keys']
        if 'excluded_keys' in previous_metadata:
            self.exclude_fields = previous_metadata['excluded_keys']

        self._handleIngest(
            reingest=True,
            statsSeed={
                'stats': {
                    'total': previous_metadata['total'],
                    'new': previous_metadata['new'],
                    'updated': previous_metadata['updated'],
                    'unchanged': previous_metadata['unchanged'],
                    'duplicates': previous_metadata['duplicates'],

                },
                'changed': previous_metadata['changed_stats']
            }
        )

    @property
    def stats(self):
        return self.statTracker
