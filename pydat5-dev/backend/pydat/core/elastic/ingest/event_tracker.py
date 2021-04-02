import multiprocessing


class EventTracker:
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
