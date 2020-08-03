from flask import Blueprint, request, current_app
from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api.utils import es as elastic
from urllib import parse
import socket
from pydat.api.shared import whois

whoisv2_bp = Blueprint("whoisv2", __name__)


def valid_size_offset(chunk_size, offset):
    try:
        chunk_size = int(chunk_size)
        offset = int(offset)
    except ValueError:
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

    return chunk_size, offset


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
    except socket.error:
        raise ClientError(f"Domain name {domain} couldn't be resolved")

    hostnames = [hostname]
    for alias in aliaslist:
        hostnames.append(alias)

    return {"hostnames": hostnames, "ips": iplist}


# Domains
@whoisv2_bp.route("/domains/diff", methods=("POST"))
def domains_diff():
    if not request.is_json:
        raise ClientError("Wrong format, JSON required")

    json_data = request.get_json()
    try:
        domain = json_data["domain"]
        version1 = json_data["version1"]
        version2 = json_data["version2"]
    except KeyError:
        ClientError("All required parameters must be provided")

    return whois.diff(domain, version1, version2)


@whoisv2_bp.route("/domains/<search_key>", methods=("POST"))
def domains(search_key, version=None, chunk_size=50, offset=0):
    if search_key not in current_app.config["SEARCH_KEYS"]:
        raise ClientError(f"Invalid key {search_key}")
    if not request.is_json:
        raise ClientError("Wrong format, JSON required")

    json_data = request.get_json()
    try:
        value = json_data["value"]
    except KeyError:
        raise ClientError("Value is required")

    if "version" in json_data.keys():
        try:
            version = float(json_data["version"])
        except ValueError:
            raise ClientError(f"Version {version} is not an integer")
    if "chunk_size" in json_data.keys():
        chunk_size = json_data["chunk_size"]
    if "offset" in json_data.keys():
        offset = json_data["offset"]
    chunk_size, offset = valid_size_offset(chunk_size, offset)

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
    except elastic.ConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.NotFoundError:
        raise ClientError(f"Cannot find specified value {value}", 404)
    except elastic.ElasticsearchError:
        raise ServerError("Unexpected exception")

    # Return results based on chunk size and offset
    start = offset * chunk_size
    if start >= search_results["total"]:
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
