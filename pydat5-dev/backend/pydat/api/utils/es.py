from flask import (
    current_app
)


class ElasticsearchError(Exception):
    pass


class ConnectionError(ElasticsearchError):
    pass


class NotFoundError(ElasticsearchError):
    pass


def lastVersion():
    pass


def metadata(version=None):
    return {'success': True, 'data': []}


def createAdvancedQuery(query, skip, size, unique, sort=None):
    pass


<<<<<<< HEAD
def search(key, value, filt=None, low=None, high=None, versionSort=False):
    limit = current_app.config["LIMIT"]
    return {'success': True, 'data': [], 'total': 100, 'avail': 0}
=======
def search(key, value, limit, filt=None, low=None, high=None, versionSort=False):
    return {'success': True, 'data': [], 'total': 0, 'avail': 0}
>>>>>>> 6395ab95517dd329f23bd4b17bf0256c45d1a2f4


def advanced_search(query, skip=0, size=20, unique=False):
    return {'success': True, 'total': 100, 'data': []}
