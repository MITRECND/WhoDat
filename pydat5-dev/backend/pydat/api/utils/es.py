from flask import current_app


class ElasticsearchError(Exception):
    pass


class ConnectionError(ElasticsearchError):
    pass


class NotFoundError(ElasticsearchError):
    pass


def lastVersion():
    pass


def metadata(version=None):
    return {"success": True, "data": []}


def createAdvancedQuery(query, skip, size, unique, sort=None):
    pass


def search(key, value, filt=None, low=None, high=None, versionSort=False):
    limit = current_app.config["LIMIT"]
    return {"success": True, "data": [], "total": 100, "avail": 0}


def advanced_search(query, skip=0, size=20, unique=False):
    return {
        "success": True,
        "total": 100,
        "data": [{}],
        "skip": 0,
        "page_size": 20,
        "avail": 20,
    }
