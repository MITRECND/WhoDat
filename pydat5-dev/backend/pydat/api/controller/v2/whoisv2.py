from flask import ( 
    Blueprint,
    request,
    current_app
)
from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api.utils import es as elastic
from urllib import parse
import socket
from pydat.api.shared import whois

whoisv2_bp = Blueprint('whoisv2', __name__)

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
        domain = json_data['domain']
        version1 = json_data['version1']
        version2 = json_data['version2']
    except KeyError:
        ClientError("All required parameters must be provided")

    return whois.diff(domain, version1, version2)


@whoisv2_bp.route('/domains/<search_key>', methods=("POST"))
def domains(search_key, version=None, chunk_size=50, offset=1):
    if search_key not in current_app.config["SEARCH_KEYS"]:
        raise ClientError(f"Invalid key {search_key}")
    if not request.is_json:
        raise ClientError("Wrong format, JSON required")

    json_data = request.get_json()
    try:
        value = json_data['value']
    except KeyError:
        raise ClientError("Value is required")

    if 'version' in json_data.keys():
        version = json_data['version']
        if not isinstance(version, float):
            raise ClientError(f"Version {version} is not an integer")
    if 'chunk_size' in json_data.keys():
        chunk_size = json_data['chunk_size']
        if not isinstance(chunk_size, int):
            raise ClientError(f"Chunk size {chunk_size} is not an integer")
    if 'offset' in json_data.keys():
        offset = json_data['offset']
        if not isinstance(offset, int):
            raise ClientError(f"Offset {offset} is not an integer")

    search_key = parse.unquote(search_key)
    value = parse.unquote(value)

    versionSort = False
    if search_key == 'domainName':
        versionSort = True

    key = parse.unquote(search_key)
    value = parse.unquote(value)

    try:
        results = elastic.search(
            key, value, filt=None, low=version, versionSort=versionSort)
    except elastic.ConnectionError:
        raise ServerError("Search failed to connect")
    except elastic.NotFoundError:
        raise ClientError(f'Cannot find specified value {value}', 404)
    except elastic.ElasticsearchError:
        raise ServerError("Unexpected exception")

    # TODO Return results based on chunk size and offset
