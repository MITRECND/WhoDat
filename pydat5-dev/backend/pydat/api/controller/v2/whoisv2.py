from flask import Blueprint, request, current_app
from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api.utils import es as elastic
from urllib import parse
import socket
from pydat.api.shared import whois
import sys

whoisv2_bp = Blueprint("whoisv2", __name__)


def valid_size_offset(chunk_size, offset):
    """Validates chunk size and offset

    Args:
        chunk_size (int): Size of data chunk to split total data into
        offset (int): Number of chunks to offset start by

    Raises:
        ClientError: chunk_size and/or offset are not integers
        ClientError: chunk_size and/or offset are not valid integers
    """
    if not (isinstance(chunk_size, int) and isinstance(offset, int)):
        raise ClientError(
            f"Offset {offset} and/or chunk size {chunk_size} are not integers"
        )

    error = None
    if chunk_size < 1:
        error = f"Invalid chunk size {chunk_size}"
    elif offset < 0:
        error = f"Invalid offset {offset}"
    if error is not None:
        raise ClientError(error)


# Metadata
@whoisv2_bp.route("/metadata")
@whoisv2_bp.route("/metadata/<version>")
def metadata(version=None):
    results = whois.metadata(version)
    return results


# Resolve
@whoisv2_bp.route("/resolve/<domain>")
def resolve(domain):
    domain = parse.unquote(domain)

    try:
        hostname, aliaslist, iplist = socket.gethostbyname_ex(domain)
    except (socket.herror, socket.gaierror):
        raise ClientError(f"Domain name {domain} couldn't be resolved")
    except OSError as e:
        raise ServerError(str(e), 504)

    hostnames = [hostname]
    for alias in aliaslist:
        hostnames.append(alias)

    return {"hostnames": hostnames, "ips": iplist}


# Domains
@whoisv2_bp.route("/domains/diff", methods=["POST"])
def domains_diff():
    if not request.is_json:
        raise ClientError("Wrong format, JSON required")

    json_data = request.get_json()
    try:
        domain = str(json_data["domain"])
        version1 = json_data["version1"]
        version2 = json_data["version2"]
    except KeyError:
        raise ClientError("All required parameters must be provided")

    return whois.diff(domain, version1, version2)


@whoisv2_bp.route("/domains/<search_key>", methods=["POST"])
def domains(search_key):
    if search_key not in current_app.config["SEARCH_KEYS"]:
        raise ClientError(f"Invalid key {search_key}")
    if not request.is_json:
        raise ClientError("Wrong format, JSON required")

    json_data = request.get_json()
    try:
        value = str(json_data["value"])
    except KeyError:
        raise ClientError("Value is required")

    version = json_data.get("version", None)
    try:
        if version:
            version = float(version)
    except ValueError:
        raise ClientError(f"Version {version} is not an integer")
    chunk_size = json_data.get("chunk_size", sys.maxsize)
    offset = json_data.get("offset", 0)
    valid_size_offset(chunk_size, offset)
    if chunk_size == sys.maxsize:
        offset = 0

    search_key = parse.unquote(search_key)
    value = parse.unquote(value)

    versionSort = False
    if search_key == "domainName":
        versionSort = True

    search_key = parse.unquote(search_key)
    value = parse.unquote(value)

    try:
        search_results = elastic.search(
            search_key, value, filt=None, low=version, versionSort=versionSort
        )
    except elastic.ESConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.ESQueryError:
        raise ClientError(f"Invalid search of {search_key}:{value}")
    except Exception as e:
        raise ServerError(f"Unexpected exception {str(e)}")

    # Return results based on chunk size and offset
    if chunk_size == sys.maxsize:
        chunk_size = search_results["total"]
    start = offset * chunk_size
    if start > 0 and start >= search_results["total"]:
        raise ClientError(
            f"Offset {offset} is too high for {search_results['total']} hits"
        )
    end = start + chunk_size
    if end > search_results["total"]:
        end = search_results["total"]
    return {
        "total": search_results["total"],
        "chunk_size": chunk_size,
        "offset": offset,
        "results": search_results["data"][start:end],
    }


@whoisv2_bp.route("/query", methods=["POST"])
def query():
    if not request.is_json:
        raise ClientError("Wrong format, JSON required")

    json_data = request.get_json()
    try:
        query = str(json_data["query"])
    except KeyError:
        raise ClientError("Query is required")

    chunk_size = json_data.get("chunk_size", 50)
    offset = json_data.get("offset", 0)
    valid_size_offset(chunk_size, offset)
    unique = json_data.get("unique", False)
    sort_keys = json_data.get("sort_keys", {})

    skip = offset * chunk_size
    # handle sort_key
    sort = []
    for sort_key in sort_keys:
        if sort_key not in current_app.config["SORT_KEYS"]:
            raise ClientError(f"Invalid sort key {sort_key} provided")
        if not (sort_keys[sort_key] == "asc" or sort_keys[sort_key] == "desc"):
            raise ClientError(f"Invalid sort direction {sort_keys[sort_key]}")
        sort.append((sort_key, sort_keys[sort_key]))
    if not sort:
        sort = None

    try:
        search_results = elastic.advanced_search(
            query, skip, chunk_size, unique, sort=sort
        )
    except elastic.ESConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.ESQueryError:
        raise ClientError(f"Invalid query {query} received")
    except Exception as e:
        raise ServerError(f"Unexpected exception {str(e)}")

    if skip > 0 and skip > search_results["total"]:
        raise ClientError(f"Offset {offset} is too high")

    return {
        "total": search_results["total"],
        "results": search_results["data"],
        "chunk_size": chunk_size,
        "offset": offset,
    }
