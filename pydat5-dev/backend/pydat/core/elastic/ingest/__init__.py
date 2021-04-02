import os
import time
import datetime
from multiprocessing import (
    JoinableQueue as jmpQueue
)
import json

import queue


from pydat.core.logger import mpLogger
from pydat.core.elastic.ingest.event_tracker import EventTracker
from pydat.core.elastic.ingest.stat_tracker import StatTracker
from pydat.core.elastic.ingest.ingest_handler import (
    IngestHandler,
    RolloverRequired
)
from pydat.core.elastic.ingest.process_wrapper import DataProcessorPool
from pydat.core.elastic.ingest.file_reader import FileReader


class DataPopulator:
    def __init__(
        self,
        elastic_args,
        include_fields,
        exclude_fields,
        ingest_day,
        template_path,
        ignore_field_prefixes,
        pipelines=2,
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
        self.template_path = template_path
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
        self.comment = comment
        self.extension = extension
        self.ingest_day = ingest_day
        self.num_fetcher_threads = num_fetcher_threads
        self.num_shipper_threads = num_shipper_threads
        self.file_queue = jmpQueue(maxsize=10000)

        # Setup logger
        self.root_logger = mpLogger(name="populater", debug=debug)
        self.root_logger.start()

        # Local Logger instance since myLogger relies on a queue
        # This can cause an issue if exiting since it doesn't give
        # it enough time to run through the queue
        self.logger = self.root_logger.logger

        self.elastic_handler = IngestHandler(
                logger=self.root_logger.getLogger("main_ingest_handler"),
                **self.elastic_args
            )

        self.eventTracker = EventTracker()
        self.statTracker = StatTracker(
            logger=self.root_logger.getLogger('statTracker')
        )

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

    def _handleShutdown(self):
        try:
            # Since this is the shutdown section, ignore Keyboard Interrupts
            # especially since the interrupt code (below) does effectively
            # the same thing

            self.statTracker.shutdown()
            self.statTracker.join()

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

        try:
            self.file_queue.close()
        except Exception:
            self.logger.debug("Exception closing queues", exc_info=True)

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
                id=self.version,
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

        # Ensure logger processes all messages
        self.root_logger.join()

    def _handleIngest(
        self,
        first_import=False,
        reingest=False,
        statsSeed=None
    ):
        # Start the stats tracker thread
        self.statTracker.start()

        # Start up Reader Thread
        self.readerThread.start()

        # Start processing
        self.dataProcessorPool = DataProcessorPool(
            procs=self.pipelines,
            version=self.version,
            file_queue=self.file_queue,
            statTracker=self.statTracker,
            eventTracker=self.eventTracker,
            root_logger=self.root_logger,
            elastic_args=self.elastic_args,
            first_import=first_import,
            reingest=reingest,
            ingest_day=self.ingest_day,
            ingest_now=self.ingest_now,
            ignore_field_prefixes=self.ignore_field_prefixes,
            include_fields=self.include_fields,
            exclude_fields=self.exclude_fields,
            bulk_fetch_size=self.bulk_fetch_size,
            bulk_ship_size=self.bulk_ship_size,
            num_fetcher_threads=self.num_fetcher_threads,
            num_shipper_threads=self.num_shipper_threads
        )

        # sys.exit(0)
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
            self._handleShutdown()
        except KeyboardInterrupt:
            self._handleCancel()

    def ingest(self):
        first_import = False
        if not self.elastic_handler.metaExists:
            template = self._getTemplate()
            self.elastic_handler.initialize(template)
            self.version = 1
            first_import = True

        metadata = self.elastic_handler.metaRecord
        if metadata is None:
            raise RuntimeError("Unable to get metadata from cluster")

        if not first_import:
            self.version = int(metadata['lastVersion']) + 1

        importing = int(metadata['importing'])
        import_interrupted = importing > 0

        if import_interrupted:
            raise RuntimeError(
                "Previous Import was interupted, please resolve")

        self.elastic_handler.updateMetadata(0, {
                'doc': {
                    'importing': self.version,
                    'lastVersion': self.version
                }
            }
        )

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

        self.elastic_handler.createMetadata(self.version, meta_struct)

        self._handleIngest(first_import=first_import)

    def reingest(self):
        if not self.elastic_handler.metaExists:
            raise RuntimeError(
                "Cannot reingest when no data exists in cluster")

        metadata = self.elastic_handler.metaRecord
        importing = int(metadata['importing'])
        import_interrupted = importing > 0

        if import_interrupted:
            self.version = importing
        else:
            self.version = int(metadata['lastVersion']) + 1

        try:
            previous_metadata = self.elastic_handler.getMetadata(
                metadata['lastVersion']
            )
        except Exception:
            raise

        if 'included_keys' in previous_metadata:
            self.include_fields = previous_metadata['included_keys']
        if 'excluded_keys' in previous_metadata:
            self.exclude_fields = previous_metadata['excluded_keys']

    @property
    def stats(self):
        return dict()
