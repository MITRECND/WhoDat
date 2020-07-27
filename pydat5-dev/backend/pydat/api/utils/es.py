from flask import (
    current_app
)


class ElasticsearchError(Exception):
    pass


def lastVersion():
    pass


def metadata(version=None):
    return {'success': True, 'data': []}


def createAdvancedQuery(query, skip, size, unique, sort=None):
    pass


def search(key, value, limit, filt=None, low=None, high=None, versionSort=False):
    return {'success': True, 'data': [], 'total': 0, 'avail': 0}


def advanced_search(query, skip=0, size=20, unique=False):
    return {'success': True, 'total': 0, 'data': []}
