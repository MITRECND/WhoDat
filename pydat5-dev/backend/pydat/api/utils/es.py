# Failed to connect to ES (500)
class ESConnectionError(Exception):
    pass


# ES query failed (500)
class ESQueryError(Exception):
    pass


def lastVersion():
    pass


def metadata(version=None):
    return {"success": True, "data": []}


def createAdvancedQuery(query, skip, size, unique, sort=None):
    pass


def search(key, value, filt=None, low=None, high=None, versionSort=False):
    return {"success": True, "data": [], "total": 100, "avail": 0}


def advanced_search(query, skip=0, size=50, unique=False, sort=None):
    return {
        "success": True,
        "total": 100,
        "data": [{}],
        "skip": 0,
        "page_size": 20,
        "avail": 20,
    }
