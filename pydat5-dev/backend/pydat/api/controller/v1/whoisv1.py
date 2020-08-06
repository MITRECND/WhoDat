from flask import (
    Blueprint,
    current_app,
    request
)
from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api.utils import es as elastic
from math import ceil
from urllib import parse
from pydat.api.shared import whois

whoisv1_bp = Blueprint('whoisv1', __name__)


# Domains
@whoisv1_bp.route("/domains/<key>/<value>")
@whoisv1_bp.route("/domains/<key>/<value>/<low>")
@whoisv1_bp.route("/domains/<key>/<value>/<low>/<high>")
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
    except elastic.ESConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.ESQueryError:
        raise ClientError(f'Invalid search of {key}:{value}')
    except Exception as e:
        raise ServerError(f'Unexpected exception {str(e)}')

    return results


@whoisv1_bp.route("/domains/<key>/<value>/latest")
def domains_latest(key, value):
    try:
        low = elastic.lastVersion()
    except elastic.ESConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.ESQueryError:
        raise ServerError("Failed to retrieve latest version")
    except Exception as e:
        raise ServerError(f'Unexpected exception {str(e)}')
    return domains(key, value, low)


# Domain
@whoisv1_bp.route("/domain/<domainName>")
@whoisv1_bp.route("/domain/<domainName>/<low>")
@whoisv1_bp.route("/domain/<domainName>/<low>/<high>")
def domain(domainName, low=None, high=None):
    return domains("domainName", domainName, low, high)


@whoisv1_bp.route("/domain/<domainName>/latest")
def domain_latest(domainName):
    return domains_latest("domainName", domainName)


@whoisv1_bp.route("/domain/<domainName>/diff/<v1>/<v2>")
def domain_diff(domainName, v1, v2):
    data = whois.diff(domainName, v1, v2)
    return {'success': True, 'data': data}


# Metadata
@whoisv1_bp.route("/metadata")
@whoisv1_bp.route("/metadata/<version>")
def metadata(version=None):
    results = whois.metadata(version)
    return results


# Query Advanced Search
@whoisv1_bp.route('/query')
def query():
    try:
        query = request.args.get("query", default=None, type=str)
        page_size = int(request.args.get("size", default=20))
        page_num = int(request.args.get("page", default=1))
        unique = request.args.get("unique", default=False)
        if str(unique).lower() == 'true':
            unique = True
        else:
            unique = False
    except ValueError:
        raise ClientError("Input paramaters are of the wrong type")

    if query is None:
        raise ClientError("Query required")

    error = None
    if page_size < 1:
        error = f"Invalid page size {page_size} provided"
    elif page_num < 1:
        error = f"Invalid page number {page_num}"
    if error is not None:
        raise ClientError(error)

    skip = (page_num-1)*page_size
    try:
        results = elastic.advanced_search(query, skip, page_size, unique)
    except elastic.ESConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.ESQueryError:
        raise ClientError(f"Invalid search query {query}")
    except Exception as e:
        raise ServerError(f'Unexpected exception {str(e)}')

    if page_num > ceil(results['total']/page_size):
        raise ClientError(f"Page number {page_num} is too high")

    return results
