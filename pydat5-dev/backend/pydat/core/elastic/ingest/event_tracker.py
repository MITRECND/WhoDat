import multiprocessing


class EventTracker:
    def __init__(self):
        self._shutdownEvent = multiprocessing.Event()
        self._bulkShipEvent = multiprocessing.Event()
        self._bulkFetchEvent = multiprocessing.Event()
        self._fileReaderDoneEvent = multiprocessing.Event()

    @property
    def shutdown(self):
        return self._shutdownEvent.is_set()

    def setShutdown(self):
        self._shutdownEvent.set()

    @property
    def shipError(self):
        return self._bulkShipEvent.is_set()

    def setShipError(self):
        self._bulkShipEvent.set()

    @property
    def fetchError(self):
        return self._bulkFetchEvent.is_set()

    def setFetchError(self):
        self._bulkFetchEvent.set()

    @property
    def bulkError(self):
        return self.shipError or self.fetchError

    @property
    def fileReaderDone(self):
        return self._fileReaderDoneEvent.is_set()

    def setFileReaderDone(self):
        self._fileReaderDoneEvent.set()
