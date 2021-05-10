#!/usr/bin/env python

import sys
from threading import Thread
from multiprocessing import (
    JoinableQueue as jmpQueue
)
import logging
import logging.handlers
import queue

DEBUG_LEVEL = logging.DEBUG
DEFAULT_LEVEL = logging.INFO


def getLogger(name=None, debug=False, mpSafe=True, **kwargs):
    """Convenience function to get a logger with configured level

    Args:
        name (str, optional): Name to use for logger. Defaults to None.
        debug (bool, optional): Enable debug level. Defaults to False.

    Returns:
        Logger: Logger instance returned by logging
    """
    if mpSafe:
        # Remove existing handlers and use QueueHandler instead
        queue_handler = logging.handlers.QueueHandler(mpLogger.logQueue)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(queue_handler)

    logger = logging.getLogger(name, **kwargs)
    logger.setLevel(
        DEBUG_LEVEL if debug else DEFAULT_LEVEL
    )

    return logger


class mpLogger(Thread):
    """Multiprocessing 'safe' logger implementation/wrapper

    This class enabled a main thread to support a QueueHandler based logger
    created by the 'getLogger' class in this file. It should be started
    before starting child processes and then join'd after child processes
    are finished
    """

    logQueue = jmpQueue()

    def __init__(self, name=__name__, debug=False, **kwargs):
        Thread.__init__(self, **kwargs)
        self._debug = debug
        self.daemon = True
        self.name = name
        self._stop_processing = False

    def stop(self):
        self._stop_processing = True

    def join(self, **kwargs):
        self._stop_processing = True
        self.logQueue.join()

    def run(self):
        while 1:
            try:
                record = self.logQueue.get(True, 0.2)
                try:
                    logger = logging.getLogger(record.name)
                    logger.handle(record)
                except EOFError:
                    break
                except BrokenPipeError:
                    print(
                        "Broken Pipe -- unable to output further logs",
                        file=sys.stderr
                    )
                    break
                finally:
                    self.logQueue.task_done()
            except queue.Empty:
                if self._stop_processing:
                    break
