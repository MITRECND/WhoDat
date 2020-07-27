from flask import Blueprint
from pydat.api.controller.v1.domains import domains, domains_latest
from pydat.api.utils import es as elastic
from pydat.api.controller.exceptions import ClientError, ServerError
domain_bp = Blueprint('domain', __name__)


@domain_bp.route("/domain/<domainName>")
@domain_bp.route("/domain/<domainName>/<low>")
@domain_bp.route("/domain/<domainName>/<low>/<high>")
def domain(domainName, low=None, high=None):
    return domains("domainName", domainName, low, high)


@domain_bp.route("/domain/<domainName>/latest")
def domain_latest(domainName):
    return domains_latest("domainName", domainName)


@domain_bp.route("/domain/<domainName>/diff/<v1>/<v2>")
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

    if not v1_result['data'] or not v2_result['data']:
        raise ClientError('Version has no results', 404)

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
