from pydat.core.elastic.ingest.event_tracker import EventTracker


def test_event_tracker():
    event_tracker = EventTracker()

    assert not event_tracker.shutdown
    assert not event_tracker.fileReaderDone

    event_tracker.setShutdown()
    assert event_tracker.shutdown

    event_tracker.setFileReaderDone()
    assert event_tracker.fileReaderDone


def test_event_tracker_bulk():
    event_tracker = EventTracker()

    assert not event_tracker.shipError
    assert not event_tracker.fetchError
    assert not event_tracker.bulkError

    event_tracker.setShipError()
    assert event_tracker.shipError
    assert event_tracker.bulkError
    assert not event_tracker.fetchError

    event_tracker._bulkShipEvent.clear()

    event_tracker.setFetchError()
    assert event_tracker.fetchError
    assert event_tracker.bulkError
    assert not event_tracker.shipError
