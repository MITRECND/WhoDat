from flask import Blueprint, request, current_app
from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api import elasticsearch_handler as es_handler
from pydat.core.es import ESConnectionError, ESQueryError
from urllib import parse
import socket
from pydat.api.shared import whois

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
    if not isinstance(chunk_size, int):
        raise ClientError(f"Chunk size {chunk_size} is not an integer")
    if not isinstance(offset, int):
        raise ClientError(f"Offset {offset} is not an integer")

    error = None
    if chunk_size < 1:
        error = f"Invalid chunk size {chunk_size}"
    elif offset < 0:
        error = f"Invalid offset {offset}"
    if error is not None:
        raise ClientError(error)


@whoisv2_bp.route("/config")
def config():
    """Retrieves and returns configuration information about the server
    """

    results = {
        'plugins': current_app.config.get('PYDAT_PLUGINS', []),
        'active_resolution': not (
            current_app.config.get('DISABLERESOLVE', False))
    }

    return results


# Metadata
@whoisv2_bp.route("/metadata")
@whoisv2_bp.route("/metadata/<version>")
def metadata(version=None):
    """Retrieves metadata for all or a specific versions

    Args:
        version (float, optional): Specific version to find metadata for.
                                    Defaults to None.

    Returns:
        dict: Details for application metadata
    """
    results = whois.metadata(version)
    return {'metadata': results}


# Resolve
@whoisv2_bp.route("/resolve/<domain>")
def resolve(domain):
    """Attempts to resolve provided domain name

    Args:
        domain (str): Specific domain name to resolve

    Raises:
        ClientError: Domain name could not be resolved
        ServerError: Failed to communicate with socket

    Returns:
        dict: Hostnames and IPs for domain
    """
    domain = parse.unquote(domain)

    if current_app.config.get("DISABLERESOLVE", False):
        raise ClientError("Active resolution disabled", status_code=400)

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
    """Compares the keys and values between the two versions

    Args:
        domainName (str): Specific domain name to search
        v1 (float): A valid version of domainName
        v2 (float): Another valid version to compare v1 to

    Raises:
        ClientError: Input body must be JSON
        ClientError: Domain name must be provided
        ClientError: Two versions must be provided

    Returns:
        dict: Diff results from comparing keys and values of v1 and v2
    """
    if not request.is_json:
        raise ClientError("Wrong format, JSON required")

    json_data = request.get_json()
    try:
        domain = json_data["domain"]
    except KeyError:
        raise ClientError("A domain name must be provided")
    try:
        version1 = json_data["version1"]
        version2 = json_data["version2"]
    except KeyError:
        raise ClientError("Two versions must be provided")

    return whois.diff(domain, version1, version2)


@whoisv2_bp.route("/domains/<search_key>", methods=["POST"])
def domains(search_key):
    """Specific search on a valid search field. Requires a value

    Args:
        search_key (str): Valid search field

    Raises:
        ClientError: Search key is not a valid key
        ClientError: Input provided in not in JSOn format
        ClientError: Value must be provided
        ClientError: Version is not a float
        ClientError: Invalid search was provided
        ServerError: Unable to connect to search engine
        ServerError: Unexpected issue when requesting results
        ServerError: Failed to process results
        ClientError: Offset exceeded total results

    Returns:
        dict: Domain hits that match search following the offset and size
    """
    valid_key = False
    for search_config in current_app.config["SEARCHKEYS"]:
        if search_config[0] == search_key:
            valid_key = True
    if not valid_key:
        raise ClientError(f"Invalid key {search_key}")
    if not request.is_json:
        raise ClientError("Wrong format, JSON required")

    json_data = request.get_json()
    try:
        value = json_data["value"]
    except KeyError:
        raise ClientError("Value is required")

    version = json_data.get("version", None)
    try:
        if version:
            version = float(version)
    except ValueError:
        raise ClientError(f"Version {version} is not an integer")
    chunk_size = json_data.get("chunk_size", 50)
    offset = json_data.get("offset", 0)
    valid_size_offset(chunk_size, offset)

    search_key = parse.unquote(search_key)
    value = parse.unquote(value)

    versionSort = False
    if search_key == "domainName":
        versionSort = True

    search_key = parse.unquote(search_key)
    value = parse.unquote(value)

    try:
        search_results = es_handler.search(
            search_key, value, filt=None, low=version, versionSort=versionSort
        )
    except ValueError:
        raise ClientError(f"Invalid search of {search_key}:{value}")
    except ESConnectionError:
        raise ServerError("Unable to connect to search engine")
    except ESQueryError:
        raise ServerError("Unexpected issue when requesting search")
    except RuntimeError:
        raise ServerError("Failed to process results")

    # Return results based on chunk size and offset
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
    """Advanced search allowing for flexible domain searches.
        Allows sorting of data

    Raises:
        ClientError: Wrong format, JSON required
        ClientError: Query is required
        ClientError: Invalid sort key provided
        ClientError: Invalid sort direction provided
        ClientError: Invalid search query
        ServerError: Unable to connect to search engine
        ServerError: Unexpected issue when requesting results
        ServerError: Failed to process results
        ClientError: Offset exceeded total results

    Returns:
        [type]: [description]
    """
    if not request.is_json:
        raise ClientError("Wrong format, JSON required")

    json_data = request.get_json()
    try:
        query = json_data["query"]
    except KeyError:
        raise ClientError("Query is required")

    sort_map = {
        "domainName": "domainName",
        "registrant_name": "details.registrant_name",
        "contactEmail": "details.contactEmail",
        "standardRegCreatedDate": "details.standardRegCreatedDate",
        "registrant_telephone": "details.registrant_telephone",
        "Version": "dataVersion",
        "score": "_score",
    }

    chunk_size = json_data.get("chunk_size", 50)
    offset = json_data.get("offset", 0)
    valid_size_offset(chunk_size, offset)
    unique = json_data.get("unique", False)
    sort_keys = json_data.get("sort_keys", [])

    skip = offset * chunk_size
    # handle sort_key
    sort = []
    for sort_key in sort_keys:
        if 'name' not in sort_key:
            raise ClientError(
                "Unable to find required 'name' field in sort_key")
        elif sort_key['name'] not in sort_map.keys():
            raise ClientError(f"Invalid sort key {sort_key['name']} provided")

        if 'dir' not in sort_key:
            raise ClientError(
                "Unable to find required 'dir' field in sort_key")
        elif sort_key['dir'] not in ['asc', 'desc']:
            raise ClientError(
                "Sort key 'dir' field must be 'asc' or desc'")

        sort.append((sort_map[sort_key['name']], sort_key['dir']))
    if not sort:
        sort = None

    try:
        search_results = es_handler.advanced_search(
            query, skip, chunk_size, unique, sort=sort
        )
    except ValueError:
        raise ClientError(f"Invalid search query {query}")
    except ESConnectionError:
        current_app.logger.exception("ESConnectionError")
        raise ServerError("Unable to connect to search engine")
    except ESQueryError:
        current_app.logger.exception("ESQueryError")
        raise ServerError("Unexpected issue when requesting search")
    except RuntimeError:
        current_app.logger.exception("RuntimeError")
        raise ServerError("Failed to process results")
    except Exception:
        current_app.exception("Unhandled Exception")
        raise ServerError("Unexpected issue handling query")

    if skip > 0 and skip >= search_results["total"]:
        raise ClientError(f"Offset {offset} is too high")

    return {
        "total": search_results["total"],
        "results": search_results["data"],
        "chunk_size": chunk_size,
        "offset": offset,
    }


@whoisv2_bp.route("/stats", methods=["GET"])
def stats():
    """Get cluster stats
    """

    try:
        cstats = es_handler.cluster_stats()
    except ESConnectionError:
        raise ServerError("Unable to connect to search engine")
    except ESQueryError:
        raise ServerError("Unexpected issue when requesting search")

    return {
        "stats": cstats
    }


@whoisv2_bp.route('/info', methods=["GET"])
def info():
    """Get cluster info
    """

    cluster_info = {}

    try:
        cluster_info['records'] = es_handler.record_count()
        cluster_info['health'] = es_handler.cluster_health()
        cluster_info['last'] = es_handler.last_version()
    except ESConnectionError:
        raise ServerError("Unable to connect to search engine")
    except ESQueryError:
        raise ServerError("Unexpected issue when requesting search")
    except RuntimeError:
        raise ServerError("Failed to process results")

    return cluster_info
