from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api import elasticsearch_handler as es_handler
from pydat.core.elastic.exceptions import (
    ESConnectionError,
    ESQueryError
)


def metadata(version=None):
    """Shared metadata functionality between v1 and v2

    Args:
        version (int, optional): Specific metadata version. Defaults to None.

    Raises:
        ClientError: Version is not a valid integer
        ClientError: Call caused an invalid query
        ServerError: Search failed to connect
        ServerError: Unexpected failure
        ClientError: Specific version or metadata does not exist

    Returns:
        dict: Found metadata for all or specific version
    """
    try:
        if version:
            version = int(version)
            if version < 0:
                raise ValueError
    except ValueError:
        raise ClientError(f"Version {version} must be a valid int")

    try:
        results = es_handler.metadata(version)
    except ESConnectionError:
        raise ServerError("Unable to connect to search engine")
    except ESQueryError:
        raise ServerError("Unexpected issue when requesting search")

    if len(results) == 0:
        raise ClientError("Cound not find metadata", 404)

    return results


def diff(domainName, v1, v2):
    """Shared diff functionality between whoisv1 and whoisv2

    Args:
        domainName (str): Name of the domain to diff versions between
        v1 (int): First version of the domainName
        v2 (int): Second version to compare the first to

    Raises:
        ClientError: Versions are not ints
        ServerError: Search failed to connect
        ClientError: Parameters created an invalid query
        ServerError: Unexpected exception
        ClientError: v1 and/or v2 does not exist

    Returns:
        dict: Contains data fields of v1 and v2 with the value specifying if
              the data is the same, different, or nonexistant between versions
    """
    try:
        v1 = int(v1)
        v2 = int(v2)
    except ValueError:
        raise ClientError("Input paramaters are of the wrong type")

    try:
        v1_result = es_handler.search(
            "domainName", domainName, filt=None, low=v1)
        v2_result = es_handler.search(
            "domainName", domainName, filt=None, low=v2)
    except ValueError:
        raise ClientError(f"Invalid search of {domainName} and {v1} or {v2}")
    except ESConnectionError:
        raise ServerError("Unable to connect to search engine")
    except ESQueryError:
        raise ServerError("Unexpected issue when requesting search")
    except RuntimeError:
        raise ServerError("Failed to process results")

    if not v1_result["data"] or not v2_result["data"]:
        raise ClientError(
            f"Provided domain {domainName} and version has no data", 404
        )
    v1_result = v1_result["data"][0]
    v2_result = v2_result["data"][0]

    blacklist = {"Version", "UpdateVersion", "domainName", "dataFirstSeen"}
    v1_keys = set(v1_result.keys())
    v2_keys = set(v2_result.keys())
    keys = (v1_keys | v2_keys) - blacklist
    results = {}

    for key in keys:
        if key in v1_keys and key in v2_keys:
            if v1_result[key] == v2_result[key]:
                results[key] = v1_result[key]
            else:
                results[key] = [v1_result[key], v2_result[key]]
        elif key in v1_keys:
            results[key] = [v1_result[key], ""]
        else:
            results[key] = ["", v2_result[key]]

    return results
