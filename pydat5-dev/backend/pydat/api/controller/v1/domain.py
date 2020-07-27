from flask import Blueprint
from pydat.api.controller.v1.domains import domains, domains_latest

domain_bp = Blueprint('domain', __name__)


@domain_bp.route("/domain/<domainName>")
@domain_bp.route("/domain/<domainName>/<low>")
@domain_bp.route("/domain/<domainName>/<low>/<high>")
def domain(domainName, low=None, high=None):
    return domains("domainName", domainName, low, high)


@domain_bp.route("/domain/<domainName>/latest")
def domain_latest(domainName):
    return domains_latest("domainName", domainName)


@domain_bp.route("/domain/<string:domainName>/diff/<float:v1>/<float:v2>")
def domain_diff(domainName, v1, v2):
    pass
