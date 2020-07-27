from flask import (
    Blueprint,
    current_app
)
from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api.utils import es as elastic
from urllib import parse

domains_bp = Blueprint('domains', __name__)


@domains_bp.route("/domains/<key>/<value>")
@domains_bp.route("/domains/<key>/<value>/<low>")
@domains_bp.route("/domains/<key>/<value>/<low>/<high>")
def domains(key, value, low=None, high=None):
    if key not in current_app.config["SEARCH_KEYS"]:
        raise ClientError(f"Invalid key {key}")
    try:
        if low:
            low = float(low)
            if low < 0:
                raise ValueError
        if high:
            high = float(high)
            if low > high:
                raise ValueError
    except ValueError:
        raise ClientError("Low/high must be integers and form a valid range")

    key = parse.unquote(key)
    value = parse.unquote(value)

    versionSort = False
    if key == 'domainName':
        versionSort = True

    try:
        results = elastic.search(
            key, value, filt=None, low=low,
            high=high, versionSort=versionSort)
    except elastic.ConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.NotFoundError:
        raise ClientError(f'Cannot find specified value {value}', 404)

    return results


@domains_bp.route("/domains/<key>/<value>/latest")
def domains_latest(key, value):
    try:
        low = elastic.lastVersion()
    except elastic.ElasticsearchError:
        raise ServerError("Failed to retrieve latest version")
    return domains(key, value, low)
