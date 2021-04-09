from flask import Blueprint, current_app, request
from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api import elasticsearch_handler as es_handler
from pydat.api import flask_cache
from pydat.core.elastic.exceptions import (
    ESConnectionError,
    ESQueryError,
    ESNotFoundError,
)
from urllib import parse
from pydat.api.controller import whois_shared


whoisv1_bp = Blueprint("whoisv1", __name__)


def _adapt_v1(records):
    # Convert output to be compliant with old API
    for record in records:
        record['Version'] = record[es_handler.metadata_key_map.VERSION_KEY]
        record['UpdateVersion'] = 0


# Domains
@whoisv1_bp.route("/domains/<key>/<value>")
@whoisv1_bp.route("/domains/<key>/<value>/<low>")
@whoisv1_bp.route("/domains/<key>/<value>/<low>/<high>")
def domains(key, value, low=None, high=None):
    """Handle v1 domains specific searches

    Args:
        key (str): Search field to filter domain information on
        value (str): Search field value
        low (float, optional): Version of domain. Lower end of the range to
                               search on or specific version. Defaults to None.
        high (float, optional): Higher end of version range to search on.
                                Defaults to None.

    Raises:
        ClientError: Provided search key is not recognized
        ClientError: Low and high are invalid values
        ClientError: Parameters formed an invalid search
        ServerError: Unable to connect to search engine
        ServerError: Unexpected issue when requesting search
        ServerError: Failed to process results

    Returns:
        dict: All domain hits that matched search with their details
    """
    valid_key = False
    for search_config in current_app.config["SEARCHKEYS"]:
        if search_config[0] == key:
            valid_key = True
    if not valid_key:
        raise ClientError(f"Invalid key {key}")
    try:
        if low:
            low = float(low)
            if low < 0:
                raise ValueError("Low must be positive")
        if high:
            high = float(high)
            if low > high:
                raise ValueError("Low must be less than high")
    except ValueError:
        raise ClientError("Low/high must be integers and form a valid range")

    key = parse.unquote(key)
    value = parse.unquote(value)

    versionSort = False
    if key == "domainName":
        versionSort = True

    try:
        results = es_handler.search(
            key, value, filt=None, low=low, high=high, versionSort=versionSort
        )
    except ValueError:
        raise ClientError(f"Invalid search of {key}:{value}")
    except ESConnectionError:
        raise ServerError("Unable to connect to search engine")
    except ESQueryError:
        raise ServerError("Unexpected issue when requesting search")
    except RuntimeError:
        raise ServerError("Failed to process results")

    _adapt_v1(results['data'])

    results['avail'] = len(results['data'])
    results['success'] = True
    return results


@whoisv1_bp.route("/domains/<key>/<value>/latest")
def domains_latest(key, value):
    """Search for domains of only the latest version

    Args:
        key (str): Search field to filter domain information on
        value (str): Search field value

    Raises:
        ServerError: Unable to connect to search engine
        ServerError: Unexpected issue when requesting latest version
        ServerError: Failed to process results

    Returns:
        dict: All domain hits that matched search with their details
    """
    try:
        low = es_handler.last_version()
        results = domains(key, value, low)
    except ESConnectionError:
        raise ServerError("Unable to connect to search engine")
    except ESQueryError:
        raise ServerError("Unexpected issue when requesting latest version")
    except RuntimeError:
        raise ServerError("Failed to process results")

    return results


# Domain
@whoisv1_bp.route("/domain/<domainName>")
@whoisv1_bp.route("/domain/<domainName>/<low>")
@whoisv1_bp.route("/domain/<domainName>/<low>/<high>")
def domain(domainName, low=None, high=None):
    """Search based on a specific domain name

    Args:
        domainName (str): Specific domain name to search
        low (float, optional): Version of domain. Lower end of the range to
                               search on or specific version. Defaults to None.
        high (float, optional): Higher end of version range to search on.
                                Defaults to None.

    Returns:
        dict: Details for all domains that match the specific domain name
    """
    return domains("domainName", domainName, low, high)


@whoisv1_bp.route("/domain/<domainName>/latest")
def domain_latest(domainName):
    """Search for the latest version of a specific domain.
        Equivalent to domains_latest when searching on the domainName field

    Args:
        domainName (str): Specific domain name to search on

    Returns:
        dict: Details for the latest version of the domain
    """
    return domains_latest("domainName", domainName)


@whoisv1_bp.route("/domain/<domainName>/diff/<v1>/<v2>")
def domain_diff(domainName, v1, v2):
    """Compares the keys and values between the two versions

    Args:
        domainName (str): Specific domain name to search
        v1 (float): A valid version of domainName
        v2 (float): Another valid version to compare v1 to

    Returns:
        dict: Diff results from comparing keys and values of v1 and v2
    """
    data = whois_shared.diff(domainName, v1, v2)
    return {"success": True, "data": data}


# Metadata
@whoisv1_bp.route("/metadata")
@whoisv1_bp.route("/metadata/<version>")
@flask_cache.cached()
def metadata(version=None):
    """Retrieves metadata for all or a specific versions

    Args:
        version (float, optional): Specific version to find metadata for.
                                    Defaults to None.

    Returns:
        dict: Details for application metadata
    """
    try:
        results = whois_shared.metadata(version)
    except RuntimeError as e:
        raise ServerError(e)
    except ESQueryError:
        raise ServerError("Unable to query Elasticsearch backend")
    except ESNotFoundError:
        raise ClientError(
            "Unable to find metadata with that version", status_code=404
        )

    return {"success": True, "data": results}


# Query Advanced Search
@whoisv1_bp.route("/query")
def query():
    """Advanced search allowing for flexible domain searches

    Raises:
        ClientError: Query required
        ClientError: Input parameter size is not an integer
        ClientError: Input parameter page is not an integer
        ClientError: Out of range page or size
        ClientError: Invalid search query
        ServerError: Unable to connect to search engine
        ServerError: Unexpected issue when requesting results
        ServerError: Failed to process results
        ClientError: Provided page is too high

    Returns:
        dict: All details for every domain hit that matches query
    """

    query = request.args.get("query", default=None, type=str)
    if query is None:
        raise ClientError("Query required")
    try:
        page_size = int(request.args.get("size", default=20))
    except ValueError:
        raise ClientError("Input parameter size is not an integer")
    try:
        page_num = int(request.args.get("page", default=1))
    except ValueError:
        raise ClientError("Input parameter page is not an integer")
    unique = request.args.get("unique", default=False)
    if str(unique).lower() == "true":
        unique = True
    else:
        unique = False

    error = None
    if page_size < 1:
        error = f"Invalid page size {page_size} provided"
    elif page_num < 1:
        error = f"Invalid page number {page_num}"
    if error is not None:
        raise ClientError(error)

    skip = (page_num - 1) * page_size
    try:
        results = es_handler.advanced_search(query, skip, page_size, unique)
    except ValueError:
        raise ClientError(f"Invalid search query {query}")
    except ESConnectionError:
        raise ServerError("Unable to connect to search engine")
    except ESQueryError:
        raise ServerError("Unexpected issue when requesting search")
    except RuntimeError:
        raise ServerError("Failed to process results")

    if skip > 0 and skip >= results["total"]:
        raise ClientError(f"Page number {page_num} is too high")

    _adapt_v1(results['data'])

    return results
