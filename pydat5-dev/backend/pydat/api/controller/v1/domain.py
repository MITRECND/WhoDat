from flask import Blueprint
from pydat.api.controller.v1.domains import domains, domains_latest

domain_bp = Blueprint('domain', __name__)


@domain_bp.route("/domain/<string:domainName>", defaults={'low': None, 'high': None})
@domain_bp.route("/domain/<string:domainName>/<int:low>", defaults={'high': None})
@domain_bp.route("/domain/<string:domainName>/<int:low>/<int:high>")
def domain(domainName, low=None, high=None):
    return domains("domainName", domainName, low, high)


@domain_bp.route("/domain/<string:domainName>/latest")
def domain_latest(domainName):
    return domains_latest("domainName", domainName)


@domain_bp.route("/domain/<string:domainName>/diff/<int:v1>/<int:v2>")
def domain_diff(domainName, v1, v2):
    pass
