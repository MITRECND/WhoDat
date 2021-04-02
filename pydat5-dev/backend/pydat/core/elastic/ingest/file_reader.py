import os

import logging
from threading import Thread


class FileReader(Thread):
    """Simple data file organizer

    This class focuses on iterating through directories and putting
    found files into a queue for processing by pipelines
    """

    def __init__(
        self,
        file_queue,
        eventTracker,
        directory,
        _file,
        extension,
        logger=None,
    ):
        super().__init__()
        self.daemon = True

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger('fileReader')

        self.file_queue = file_queue
        self.eventTracker = eventTracker
        self.directory = directory
        self.file = _file
        self.extension = extension
        self._shutdown = False

    def shutdown(self):
        self._shutdown = True

    def run(self):
        try:
            if self.directory:
                self.scan_directory(self.directory)
            elif self.file:
                self.file_queue.put(self.file)
            else:
                self.logger.error("File or Directory required")
        except Exception:
            self.logger.exception("Unknown exception in File Reader")
        finally:
            self.file_queue.join()
            self.logger.debug("Setting FileReaderDone event")
            self.eventTracker.setFileReaderDone()

    def scan_directory(self, directory):
        for path in sorted(os.listdir(directory)):
            fp = os.path.join(directory, path)

            if os.path.isdir(fp):
                self.scan_directory(fp)
            elif os.path.isfile(fp):
                if self._shutdown:
                    return
                if self.extension != '':
                    fn, ext = os.path.splitext(path)
                    if ext == '' or not ext.endswith(self.extension):
                        continue
                self.file_queue.put(fp)
            else:
                self.logger.warning("%s is neither a file nor directory" % fp)
