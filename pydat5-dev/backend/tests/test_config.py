from pydat.api import create_app
from pydat.core.config_parser import ConfigParser
import pytest
from unittest import mock


def test_config_parser():
    app = create_app()
    parser = ConfigParser(app)
    parser.parse()


def test_config_parser_env_invalid(monkeypatch):
    app = create_app()
    fake_environ = mock.MagicMock(return_value=[
        ('PYDAT_', 'test')
    ])

    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.items', fake_environ)
        with pytest.raises(ValueError):
            ConfigParser(app)


def test_config_parser_env_searchkeys(monkeypatch):
    app = create_app()
    search_keys = ['domainName', 'registrant_name']
    fake_environ = mock.MagicMock(return_value=[
        ('PYDAT_SEARCHKEYS', ','.join(search_keys))
    ])

    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.items', fake_environ)
        ConfigParser(app)
        assert app.config['SEARCHKEYS']
        assert app.config['SEARCHKEYS'] == search_keys


def test_config_parser_envvar(monkeypatch):
    app = create_app()
    fake_environ_keys = mock.MagicMock(return_value=[
        'PYDATCONFIG'
    ])
    fake_app_config = mock.MagicMock()

    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.keys', fake_environ_keys)
        monkey.setattr(app, 'config', fake_app_config)
        ConfigParser(app)
        fake_app_config.from_envvar.assert_called_with(
            ConfigParser.ENV_CONFIG_FILE)


def test_config_parser_env_boolean(monkeypatch):
    app = create_app()
    fake_environ = mock.MagicMock(return_value=[
        ('PYDAT_SSLVERIFY', 'test')
    ])

    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.items', fake_environ)
        with pytest.raises(ValueError):
            ConfigParser(app)

    app = create_app()
    fake_environ = mock.MagicMock(return_value=[
        ('PYDAT_DEBUG', 'test')
    ])
    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.items', fake_environ)
        with pytest.raises(ValueError):
            ConfigParser(app)

    app = create_app()
    fake_environ = mock.MagicMock(return_value=[
        ('PYDAT_DEBUG', 'false')
    ])
    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.items', fake_environ)
        ConfigParser(app)
        assert(not app.config['DEBUG'])

    app = create_app()
    fake_environ = mock.MagicMock(return_value=[
        ('PYDAT_DEBUG', 'true')
    ])
    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.items', fake_environ)
        ConfigParser(app)
        assert(app.config['DEBUG'])


def test_config_env_fields(monkeypatch):
    app = create_app()
    fake_environ = mock.MagicMock(return_value=[
        ('PYDAT_TEST', 'value')
    ])
    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.items', fake_environ)
        ConfigParser(app)
        assert(app.config['TEST'] == 'value')


def test_config_env_dicts(monkeypatch):
    app = create_app()
    fake_environ = mock.MagicMock(return_value=[
        ('PYDAT_TEST_FIELD', 'value')
    ])
    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.items', fake_environ)
        ConfigParser(app)
        assert(app.config['TEST']['FIELD'] == 'value')

    app = create_app()
    fake_environ = mock.MagicMock(return_value=[
        ('PYDAT_TEST_FIELD_NESTED', 'value')
    ])
    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.items', fake_environ)
        ConfigParser(app)
        assert(app.config['TEST']['FIELD']['NESTED'] == 'value')

    app = create_app()
    fake_environ = mock.MagicMock(return_value=[
        ('PYDAT_TEST_FIELD_NESTED', 'value'),
        ('PYDAT_TEST_FIELD_NESTED2', 'value')
    ])
    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.items', fake_environ)
        ConfigParser(app)
        assert(app.config['TEST']['FIELD']['NESTED2'] == 'value')

    app = create_app()
    fake_environ = mock.MagicMock(return_value=[
        ('PYDAT_ELASTICSEARCH_uri', 'localhost:9001')
    ])
    with monkeypatch.context() as monkey:
        monkey.setattr('os.environ.items', fake_environ)
        ConfigParser(app)
        assert(app.config['ELASTICSEARCH']['uri'] == 'localhost:9001')


def test_config_invalidated(monkeypatch, capsys):
    app = create_app()
    fake_app_config = mock.MagicMock()
    fake_app_config.items = mock.MagicMock(return_value=[('DEBUG', 'test')])

    with monkeypatch.context() as monkey:
        monkey.setattr(app, 'config', fake_app_config)
        parser = ConfigParser(app)
        with pytest.raises(ValueError):
            parser.parse()
