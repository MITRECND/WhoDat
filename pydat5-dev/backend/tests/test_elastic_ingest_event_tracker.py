from pydat.core.elastic.ingest.event_tracker import EventTracker


def test_event_tracker():
    event_tracker = EventTracker()

    assert not event_tracker.shutdown
    assert not event_tracker.bulkError
    assert not event_tracker.fileReaderDone

    event_tracker.setShutdown()
    assert event_tracker.shutdown

    event_tracker.setBulkError()
    assert event_tracker.bulkError

    event_tracker.setFileReaderDone()
    assert event_tracker.fileReaderDone
