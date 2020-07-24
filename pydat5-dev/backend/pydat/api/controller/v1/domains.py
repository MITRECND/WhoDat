from flask import (
    Blueprint,
    current_app
)
from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api.utils import es as elastic
from urllib import parse

domains_bp = Blueprint('domains', __name__)


@domains_bp.route("/domains/<string:key>/<string:value>",
                  defaults={'low': None, 'high': None})
@domains_bp.route("/domains/<string:key>/<string:value>/<int:low>",
                  defaults={'high': None})
@domains_bp.route("/domains/<string:key>/<string:value>/<int:low>/<int:high>")
def domains(key, value, low=None, high=None):
    if key not in current_app.config["SEARCH_KEYS"]:
        raise ClientError(f"Invalid key {key}")
    key = parse.unquote(key)
    value = parse.unquote(value)

    versionSort = False
    if key == 'domainName':
        versionSort = True

    try:
        results = elastic.search(
            key, value, limit=current_app.config["LIMIT"], filt=None, low=low, high=high, versionSort=versionSort)
    except elastic.ElasticsearchError:
        raise ServerError("Search failed to connect")

    return results


@domains_bp.route("/domains/<string:key>/<string:value>/latest")
def domains_latest(key, value):
    try:
        low = elastic.lastVersion()
    except elastic.ElasticsearchError:
        raise ServerError("Failed to retrieve latest version")
    return domains(key, value, low)
