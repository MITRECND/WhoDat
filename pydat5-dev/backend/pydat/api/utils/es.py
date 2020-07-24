from flask import (
    current_app
)


class ElasticsearchError(Exception):
    pass


def lastVersion():
    pass


def metadata(version=None):
    pass


def createAdvancedQuery(query, skip, size, unique, sort=None):
    pass


def search(key, value, limit, filt=None, low=None, high=None, versionSort=False):
    return {'success': True, 'aaData': [], 'iTotalRecords': 0, 'iTotalDisplayRecords': 0}


def advanced_search(query, skip=0, size=20, unique=False):
    pass
