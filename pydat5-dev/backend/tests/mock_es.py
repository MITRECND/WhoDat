from pydat.api.utils import es as elastic


def search(key, value, filt=None, low=None, high=None, versionSort=False):
    return {"success": True, "data": [], "total": 100, "avail": 0}


def diff_search(key, value, filt=None, low=None, high=None, versionSort=False):
    if value != "greetings":
        raise elastic.NotFoundError
    data = []
    if low == 1:
        data = [{"hello": True, "hi": 1, "goodbye": -1.1, "Version": 1}]
    elif low == 2:
        data = [{"hello": 1, "hi": 1, "goodbye": False, "hola": "spanish"}]
    return {"success": True, "data": data, "total": len(data), "avail": 0}


def query(query, skip=0, size=20, unique=False):
    total = 1000
    avail = 0
    if skip < total:
        avail = (total-skip) % (size+1)
    return {
        "success": True,
        "total": total,
        "data": [{}],
        "skip": skip,
        "page_size": size,
        "avail": avail,
    }


def metadata(version=None):
    if not version or version == 1:
        return {
            "success": True,
            "data": {
                "comment": "",
                "updated": 0,
                "duplicates": 0,
                "unchanged": 0,
                "changed_stats": {},
                "updateVersion": 0,
                "new": 1000,
                "total": 1000,
                "metadata": 1,
            },
        }
    raise elastic.NotFoundError
