from pydat.core.elastic.ingest.stat_tracker import StatTracker


def test_stat_tracker():
    stat_tracker = StatTracker()
    assert stat_tracker

    assert stat_tracker.total == 0
    assert stat_tracker.new == 0
    assert stat_tracker.updated == 0
    assert stat_tracker.unchanged == 0
    assert stat_tracker.duplicates == 0

    assert stat_tracker.stats == {
        'total': 0,
        'new': 0,
        'updated': 0,
        'unchanged': 0,
        'duplicates': 0
    }

    stat_tracker.shutdown()
    assert stat_tracker._shutdown


def test_stat_tracker_seed():
    stat_tracker = StatTracker()

    stats = [
        'total',
        'new',
        'updated',
        'unchanged',
        'duplicates'
    ]

    stat_tracker.seed({
        'total': 10
    })

    for key in stats:
        assert key in stat_tracker.stats


def test_stat_tracker_changed():
    stat_tracker = StatTracker()

    assert stat_tracker.changed_stats == {}

    stat_tracker.seedChanged({
        'registrant_name': 10
    })

    assert 'registrant_name' in stat_tracker.changed_stats.keys()


def test_stat_tracker_run():
    stat_tracker = StatTracker()

    stat_tracker.incr('total')
    stat_tracker.addChanged('registrant_name')

    assert stat_tracker._stat_queue.qsize() == 2

    stat_tracker.start()
    stat_tracker.shutdown()


def test_stat_tracker_run_failure(caplog):
    stat_tracker = StatTracker()
    stat_tracker.incr('badkey')
    stat_tracker.shutdown()
    stat_tracker.run()

    assert "Unknown field" in caplog.record_tuples[0][2]
    stat_tracker._stat_queue.close()
    stat_tracker._stat_queue.join_thread()


def test_stat_tracker_run_failure2():
    stat_tracker = StatTracker()
    stat_tracker.addChanged('registrant_name')
    stat_tracker.addChanged('registrant_name')
    stat_tracker.shutdown()
    stat_tracker.run()

    assert 'registrant_name' in stat_tracker.changed_stats
    assert stat_tracker.changed_stats['registrant_name'] == 2
    stat_tracker._stat_queue.close()
    stat_tracker._stat_queue.join_thread()


def test_stat_tracker_client():
    stat_tracker = StatTracker()
    client = stat_tracker.get_tracker()

    client.addChanged('total')
    client.incr('registrant_name')

    assert len(client._chunk) == 2
    client.flush()
    assert stat_tracker._stat_queue.qsize() == 1
    stat_tracker.shutdown()
    stat_tracker.run()
    stat_tracker._stat_queue.close()
    stat_tracker._stat_queue.join_thread()
