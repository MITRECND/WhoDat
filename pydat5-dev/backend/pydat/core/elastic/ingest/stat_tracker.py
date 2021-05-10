#!/usr/bin/env python

from threading import Thread
from multiprocessing import Queue as mpQueue
import queue


class _StatTracker:
    MAX_CHUNK_SIZE = 100

    def __init__(self, queue):
        self._queue = queue
        self.chunk = []

    def __del__(self):
        try:
            self.flush()
        except Exception:
            pass

    def flush(self):
        self._queue.put(self.chunk)
        self.chunk = []

    def addChanged(self, field):
        self.chunk.append(('chn', field))
        if len(self.chunk) >= self.MAX_CHUNK_SIZE:
            self.flush()

    def incr(self, field):
        self.chunk.append(('stat', field))
        if len(self.chunk) >= self.MAX_CHUNK_SIZE:
            self.flush()


class StatTracker(Thread):
    """Multi-processing safe stat tracking class

    This class can be provided to all pipelines to keep track of different
    stats about the domains being ingested
    """

    def __init__(self, logger=None, **kwargs):
        super().__init__(**kwargs)
        self.daemon = True
        self._stats = {'total': 0,
                       'new': 0,
                       'updated': 0,
                       'unchanged': 0,
                       'duplicates': 0}
        self._stat_queue = mpQueue()
        self._shutdown = False
        self._changed = dict()
        if logger is None:
            import logging
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def get_tracker(self):
        return _StatTracker(self._stat_queue)

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
    def stats(self):
        return self._stats

    @property
    def changed_stats(self):
        return self._changed

    def seed(self, stats):
        self._stats.update(stats)

    def seedChanged(self, changed):
        for (name, value) in changed.items():
            self._changed[name] = int(value)

    def shutdown(self):
        self._shutdown = True

    def run(self):
        while 1:
            try:
                chunk = self._stat_queue.get(True, 0.2)
            except queue.Empty:
                if self._shutdown:
                    break
                continue

            for (typ, field) in chunk:
                if typ == 'stat':
                    if field not in self._stats:
                        self.logger.error("Unknown field %s" % field)
                    else:
                        self._stats[field] += 1
                elif typ == 'chn':
                    if field not in self._changed:
                        self._changed[field] = 0
                    self._changed[field] += 1
                else:
                    self.logger.error("Unknown stat type")

        self._stat_queue.close()

    def addChanged(self, field):
        self._stat_queue.put(('chn', field))

    def incr(self, field):
        self._stat_queue.put(('stat', field))
