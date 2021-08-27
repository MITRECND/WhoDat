import os
import pytest
from unittest import mock
from pydat.core.elastic.ingest.file_reader import FileReader


def fake_idsir(path):
    if path in [
            '/tmp/fake/subdir',
    ]:
        return True
    else:
        return False


def fake_isfile(path):
    if path in [
            '/tmp/fake/file1.csv',
            '/tmp/fake/file2.csv',
            '/tmp/fake/file1.txt',
            '/tmp/fake/file3.txt'
    ]:
        return True
    else:
        return False


def test_file_reader_file(monkeypatch):
    fake_eventTracker = mock.MagicMock()
    fake_eventTracker.setFileReaderDone = mock.MagicMock()
    fake_queue = mock.MagicMock()

    file_reader = FileReader(
        fake_queue,
        fake_eventTracker,
        None,
        "test.csv",
        "csv"
    )

    file_reader.run()
    assert fake_queue.put.called
    assert fake_queue.join.called
    assert fake_eventTracker.setFileReaderDone.called


@pytest.mark.parametrize(
    "pathlist,call_count", [
        (
            ['file1.csv', 'file2.csv'],
            2
        ),
        (
            ['subdir'],
            0
        ),
        (
            ['file3.txt'],
            0
        )
    ]
)
def test_file_reader_directory(monkeypatch, pathlist, call_count):
    fake_eventTracker = mock.MagicMock()
    fake_eventTracker.setFileReaderDone = mock.MagicMock()
    fake_queue = mock.MagicMock()

    file_reader = FileReader(
        fake_queue,
        fake_eventTracker,
        "/tmp/fake",
        None,
        "csv"
    )

    monkeypatch.setattr(os.path, "isdir", fake_idsir)
    monkeypatch.setattr(os.path, "isfile", fake_isfile)

    fake_listdir = mock.MagicMock(return_value=pathlist)
    with monkeypatch.context() as monkey:
        monkey.setattr(os, "listdir", fake_listdir)
        file_reader.run()
        assert fake_queue.put.call_count == call_count


def test_file_reader_shutdown(monkeypatch):
    fake_eventTracker = mock.MagicMock()
    fake_eventTracker.setFileReaderDone = mock.MagicMock()
    fake_queue = mock.MagicMock()

    file_reader = FileReader(
        fake_queue,
        fake_eventTracker,
        "/tmp/fake",
        None,
        ""
    )

    file_reader.shutdown()
    assert file_reader._shutdown is True

    fake_listdir = mock.MagicMock(return_value=['file1.csv'])
    with monkeypatch.context() as monkey:
        monkey.setattr(os, "listdir", fake_listdir)
        file_reader.run()
        assert fake_queue.put.call_count == 0


def test_file_reader_noextension_check(monkeypatch):
    fake_eventTracker = mock.MagicMock()
    fake_eventTracker.setFileReaderDone = mock.MagicMock()
    fake_queue = mock.MagicMock()

    file_reader = FileReader(
        fake_queue,
        fake_eventTracker,
        "/tmp/fake",
        None,
        ""
    )

    monkeypatch.setattr(os.path, "isdir", fake_idsir)
    monkeypatch.setattr(os.path, "isfile", fake_isfile)
    fake_listdir = mock.MagicMock(return_value=['file1.txt'])
    with monkeypatch.context() as monkey:
        monkey.setattr(os, "listdir", fake_listdir)
        file_reader.run()
        assert fake_queue.put.call_count == 1
