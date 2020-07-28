from flask import (
    Blueprint,
    current_app,
    request
)
from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api.utils import es as elastic
from math import ceil
from urllib import parse

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
    except elastic.ConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.NotFoundError:
        raise ClientError(f'Cannot find specified value {value}', 404)
    except elastic.ElasticsearchError:
        raise ServerError("Unexpected exception")

    return results


@whoisv1_bp.route("/domains/<key>/<value>/latest")
def domains_latest(key, value):
    try:
        low = elastic.lastVersion()
    except elastic.ElasticsearchError:
        raise ServerError("Failed to retrieve latest version")
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
    try:
        v1 = float(v1)
        v2 = float(v2)
    except ValueError:
        raise ClientError("Input paramaters are of the wrong type")

    try:
        v1_result = elastic.search('domainName', domainName, filt=None, low=v1)
        v2_result = elastic.search('domainName', domainName, filt=None, low=v2)
    except elastic.ConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.NotFoundError:
        raise ClientError(f'Cannot find domain name {domainName}', 404)
    except elastic.ElasticsearchError:
        raise ServerError('Unexpected exception')

    if not v1_result['data'] or not v2_result['data']:
        raise ClientError('Provided version has no data', 404)
    v1_result = v1_result['data'][0]
    v2_result = v2_result['data'][0]

    blacklist = {'Version', 'UpdateVersion', 'domainName', 'dataFirstSeen'}
    v1_key = set(v1_result.keys())-blacklist
    v2_key = set(v2_result.keys())-blacklist
    result = {}
    data = {}

    for key in v1_key-v2_key:
        data[key] = [v1_result[key], '']
    for key in v2_key-v1_key:
        data[key] = ['', v2_result[key]]
    for key in v1_key & v2_key:
        if v1_result[key] == v2_result[key]:
            data[key] = v1_result[key]
        else:
            data[key] = [v1_result[key], v2_result[key]]

    result['data'] = data
    result['success'] = True
    return result


# Metadata
@whoisv1_bp.route("/metadata")
@whoisv1_bp.route("/metadata/<version>")
def metadata(version=None):
    try:
        if version:
            version = int(version)
            if version < 0:
                raise ValueError
    except ValueError:
        raise ClientError(f'Version {version} must be a valid integer')

    try:
        results = elastic.metadata(version)
    except elastic.NotFoundError:
        raise ClientError(f'Version {version} does not exist', 404)
    except elastic.ConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.ElasticsearchError:
        raise ServerError('Unexpected exception')

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
    except elastic.ConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.ElasticsearchError:
        raise ServerError('Unexpected exception')

    if page_num > ceil(results['total']/page_size):
        raise ClientError(f"Page number {page_num} is too high")

    return results
