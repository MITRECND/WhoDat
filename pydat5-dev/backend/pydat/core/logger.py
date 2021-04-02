#!/usr/bin/env python

import sys
from threading import Thread
from multiprocessing import (
    JoinableQueue as jmpQueue
)
import traceback
import logging
from logging import StreamHandler

import queue


class _mpLoggerClient:
    """class returned by mpLogger.getLogger

    This class mimics how logger should act by providing the same/similar
    facilities
    """

    def __init__(self, name, logQueue, debug):
        self.name = name
        self.logQueue = logQueue
        self._logger = logging.getLogger()
        self._debug = debug
        self._prefix = None

    @property
    def prefix(self):
        return self._prefix

    @prefix.setter
    def prefix(self, value):
        if not isinstance(value, str):
            raise TypeError("Expected a string type")
        self._prefix = value

    def log(self, lvl, msg, *args, **kwargs):
        if self.prefix is not None and self._debug:
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

        (name, line, func, _) = self._logger.findCaller()
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

    This logger implementation should probably not be used by a main
    thread since it relies on a queue for its data processing. So if things
    need to be printed immediately, i.e,. on error, it should be done via
    the regular logging instance
    """

    def __init__(self, name=__name__, debug=False, **kwargs):
        Thread.__init__(self, **kwargs)
        self._debug = debug
        self.daemon = True
        self.name = name
        self.logQueue = jmpQueue()
        self._logger = None
        self._stop_processing = False

    @property
    def logger(self):
        if self._logger is None:
            self._logger = logging.getLogger(self.name)
        return self._logger

    def getLogger(self, name=__name__):
        return _mpLoggerClient(name=name,
                               logQueue=self.logQueue,
                               debug=self._debug)

    def stop(self):
        self._stop_processing = True

    def join(self, **kwargs):
        self.logQueue.join()

    def run(self):
        default_level = logging.INFO
        root_debug_level = logging.WARNING
        debug_level = logging.DEBUG
        root_default_level = logging.WARNING

        try:
            logHandler = StreamHandler(sys.stdout)
        except Exception as e:
            raise Exception(("Unable to setup logger to stdout\n"
                             "Error Message: %s\n") % str(e))

        if self._debug:
            log_format = ("%(levelname) -10s %(asctime)s %(funcName) "
                          "-20s %(lineno) -5d: %(message)s")
        else:
            log_format = "%(message)s"

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
                raw_record = self.logQueue.get(True, 0.2)
                try:
                    if logger.isEnabledFor(raw_record[1]):
                        logger.handle(logger.makeRecord(*raw_record))
                finally:
                    self.logQueue.task_done()
            except EOFError:
                break
            except queue.Empty:
                if self._stop_processing:
                    break
