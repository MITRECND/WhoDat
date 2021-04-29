import os
import time
import logging
import multiprocessing
from argparse import Namespace
from multiprocessing import (
    Process,
)
import queue

from pydat.core.elastic.ingest.ingest_handler import (
    IngestHandler,
    RolloverRequired
)

from pydat.core.elastic.ingest.data_processors import (
    DataReader,
    DataFetcher,
    DataWorker,
    DataShipper,
)

from pydat.core.elastic.ingest.debug_levels import DebugLevel


class PopulatorOptions(Namespace):
    def __init__(
        self,
        **kwargs
    ):
        validOptions = [
            'first_import',
            'reingest',
            'version',
            'ingest_day',
            'ingest_now',
            'ignore_field_prefixes',
            'include_fields',
            'exclude_fields',
            'elastic_args',
            'bulk_fetch_size',
            'bulk_ship_size',
            'num_fetcher_threads',
            'num_shipper_threads',
            'verbose',
            'debug',
        ]
        unexpected_options = []

        for name in kwargs.keys():
            if name not in validOptions:
                unexpected_options.append(name)

        if len(unexpected_options) > 0:
            raise ValueError((
                "Unexpected arguments: "
                f"{','.join(list(unexpected_options.keys()))}"
            ))

        super().__init__(**kwargs)


class DataProcessor(Process):
    """Main pipeline process which manages individual threads
    """
    def __init__(
        self,
        pipeline_id,
        file_queue,
        statTracker,
        eventTracker,
        process_options,
        skip_fetch,
        logger=None,

    ):
        super().__init__()
        self.myid = pipeline_id

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger(f'processor.{self.myid}')

        self.file_queue = file_queue
        self.statTracker = statTracker
        self.eventTracker = eventTracker
        self.process_options = process_options

        self.fetcher_threads = []
        self.worker_thread = None
        self.shipper_threads = []
        self.reader_thread = None
        self.pause_request = multiprocessing.Value('b', False)
        self._paused = multiprocessing.Value('b', False)
        self._complete = multiprocessing.Value('b', False)
        self.es = IngestHandler(
            **self.process_options.elastic_args,
            logger=self.logger
        )
        self.skip_fetch = skip_fetch

        self.num_fetcher_threads = self.process_options.num_fetcher_threads
        self.num_shipper_threads = self.process_options.num_shipper_threads
        self.verbose = self.process_options.verbose
        self.debug = self.process_options.debug
        self.index_list = self.es.resolveAlias()

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
        self.index_list = self.es.resolveAlias()

    def _pause(self):
        if self.reader_thread.isAlive():
            try:
                self.reader_thread.pause()
                self.finish()
                self._paused.value = True
            except Exception:
                self.logger.exception("Unable to pause reader thread")
        else:
            self.logger.debug("Pause requested when reader thread not alive")

    def _unpause(self):
        if self.reader_thread.isAlive():
            try:
                self.reader_thread.unpause()
            except Exception:
                self.logger.exception("Unable to unpause reader thread")
            # Disable skipping fetch phase
            self.skip_fetch = False
            self.update_index_list()
            self.startup_rest()
            self._paused.value = False
        else:
            self.logger.debug("Pause requested when reader thread not alive")

    def shutdown(self):
        self.logger.debug("Shutting down reader")
        self.reader_thread.shutdown()
        while self.reader_thread.is_alive():
            try:
                self.file_queue.get_nowait()
                self.file_queue.task_done()
            except queue.Empty:
                break

        self.logger.debug("Shutting down fetchers")
        for fetcher in self.fetcher_threads:
            fetcher.shutdown()
            # Ensure put is not blocking shutdown
            while fetcher.is_alive():
                try:
                    self.work_queue.get_nowait()
                    self.work_queue.task_done()
                except queue.Empty:
                    break

        self.logger.debug("Draining work queue")
        # Drain the work queue
        while not self.work_queue.empty():
            try:
                self.work_queue.get_nowait()
                self.work_queue.task_done()
            except queue.Empty:
                break

        self.logger.debug("Shutting down worker thread")
        self.worker_thread.shutdown()
        while self.worker_thread.is_alive():
            try:
                self.insert_queue.get_nowait()
                self.insert_queue.task_done()
            except queue.Empty:
                break

        self.logger.debug("Draining insert queue")
        # Drain the insert queue
        while not self.insert_queue.empty():
            try:
                self.insert_queue.get_nowait()
                self.insert_queue.task_done()
            except queue.Empty:
                break

        self.logger.debug("Waiting for shippers to finish")
        # Shippers can't be forced to shutdown
        for shipper in self.shipper_threads:
            shipper.finish()
            shipper.join()

        self.logger.debug("Shutdown Complete")

    def finish(self):
        self.logger.debug("Waiting for fetchers to finish")
        for fetcher in self.fetcher_threads:
            fetcher.finish()
            fetcher.join()

        self.logger.debug("Waiting for worker to finish")
        self.worker_thread.finish()
        self.worker_thread.join()

        self.logger.debug("Waiting for shippers to finish")
        for shipper in self.shipper_threads:
            shipper.finish()
            shipper.join()

        self.logger.debug("Finish Complete")

    def startup_rest(self):
        self.logger.debug("Starting Worker")
        self.worker_thread = DataWorker(
            pipelineid=self.myid,
            work_queue=self.work_queue,
            insert_queue=self.insert_queue,
            statTracker=self.statTracker,
            eventTracker=self.eventTracker,
            es=self.es,
            process_options=self.process_options,
            logger=self.logger,
        )
        self.worker_thread.daemon = True
        self.worker_thread.start()

        self.logger.debug("starting Fetchers")
        for fetcherid in range(self.num_fetcher_threads):
            fetcher_thread = DataFetcher(
                pipelineid=self.myid,
                fetcherid=fetcherid,
                es=self.es,
                data_queue=self.data_queue,
                work_queue=self.work_queue,
                eventTracker=self.eventTracker,
                index_list=self.index_list,
                skip_fetch=self.skip_fetch,
                process_options=self.process_options,
                logger=self.logger,
            )
            fetcher_thread.start()
            self.fetcher_threads.append(fetcher_thread)

        self.logger.debug("Starting Shippers")
        for shipperid in range(self.num_shipper_threads):
            shipper_thread = DataShipper(
                pipelineid=self.myid,
                shipperid=shipperid,
                es=self.es,
                insert_queue=self.insert_queue,
                eventTracker=self.eventTracker,
                process_options=self.process_options,
            )
            shipper_thread.start()
            self.shipper_threads.append(shipper_thread)

    def run(self):
        os.setpgrp()
        # self.logger = self.root_logger.getLogger(f"Pipeline {self.myid}")
        # self.logger.prefix = "(Pipeline %d) " % self.myid

        # Queue for individual csv entries
        self.data_queue = queue.Queue(maxsize=10000)
        # Queue for current/new entry comparison
        self.work_queue = queue.Queue(maxsize=10000)
        # Queue for shippers to send data
        self.insert_queue = queue.Queue(maxsize=10000)

        self.startup_rest()

        self.logger.debug("Starting Reader")
        self.reader_thread = DataReader(
            pipelineid=self.myid,
            file_queue=self.file_queue,
            data_queue=self.data_queue,
            eventTracker=self.eventTracker,
            process_options=self.process_options,
            logger=self.logger,
        )
        self.reader_thread.start()

        # Wait to shutdown/finish
        while 1:
            if self.eventTracker.shutdown:
                self.logger.debug("Shutdown event received")
                self.shutdown()
                break

            if self.pause_request.value:
                self._pause()
                while self.pause_request.value:
                    time.sleep(.1)
                self._unpause()

            self.reader_thread.join(.1)
            if not self.reader_thread.isAlive():
                self.logger.debug("Reader thread exited, finishing up")
                self.finish()
                break

            time.sleep(.1)
        self.logger.debug("Pipeline Shutdown")
        self._complete.value = True


class DataProcessorPool:
    def __init__(
        self,
        procs,
        file_queue,
        statTracker,
        eventTracker,
        root_logger,
        process_options,
    ):

        self.proc_count = procs
        self.file_queue = file_queue
        self.statTracker = statTracker
        self.eventTracker = eventTracker
        self.root_logger = root_logger
        self.process_options = process_options

        self.verbose = process_options.verbose
        self.debug = process_options.debug

        self.logger = self.root_logger.getLogger("data_processor_pool")

        self.pipelines = []

        skip_fetch = False
        if (not self.process_options.reingest
                and self.process_options.first_import):
            skip_fetch = True

        self.elastic_handler = IngestHandler(
            logger=self.root_logger.getLogger("pool_ingest_handler"),
            **self.process_options.elastic_args)

        for pipeline_id in range(self.proc_count):
            p = DataProcessor(
                pipeline_id=pipeline_id,
                file_queue=self.file_queue,
                statTracker=self.statTracker.get_tracker(),
                eventTracker=self.eventTracker,
                logger=self.root_logger.getLogger(name=f'{pipeline_id}'),
                skip_fetch=skip_fetch,
                process_options=self.process_options
            )
            self.pipelines.append(p)

    def start(self):
        for pipeline in self.pipelines:
            pipeline.start()

    def join(self):
        timer = time.time()
        for proc in self.pipelines:
            while proc.is_alive():
                try:
                    timer = self.elastic_handler.rolloverTimer(timer)
                except RolloverRequired as rollOver:
                    # Reset Timer
                    timer = time.time()
                    self.handleRollover(
                        write_alias=rollOver.write_alias,
                        search_alias=rollOver.search_alias
                    )
                proc.join(.1)

                if self.eventTracker.bulkError:
                    self.logger.critical((
                        "Bulk API error -- forcing program shutdown"))
                    raise KeyboardInterrupt(("Error response from ES worker, "
                                             "stopping processing"))

    def handleRollover(self, write_alias, search_alias):
        if self.debug >= DebugLevel.VERBOSE:
            self.logger.debug("Rolling over ElasticSearch Index")

        # Pause the pipelines
        for proc in self.pipelines:
            proc.pause()

        self.logger.debug("Waiting for pipelines to pause")
        # Ensure procs are paused
        for proc in self.pipelines:
            while not proc.paused:
                if proc.complete:
                    break
                time.sleep(.1)
        self.logger.debug("Pipelines paused")

        try:
            self.elastic_handler.rolloverIndices(
                write_alias=write_alias,
                search_alias=search_alias
            )

            # Index rolled over, restart processing
            for proc in self.pipelines:
                if not proc.complete:  # Only if process has data to process
                    proc.unpause()

            if self.debug >= DebugLevel.VERBOSE:
                self.logger.debug("Roll over complete")

        except KeyboardInterrupt:
            self.logger.warning((
                "Keyboard Interrupt ignored while rolling over "
                "index, please wait a few seconds and try again"))
