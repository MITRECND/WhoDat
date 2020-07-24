from flask import (
    Blueprint,
    request,
    session,
    make_response,
    jsonify
)
from pydat.api.utils import es as elastic
from pydat.api.controller.exceptions import ClientError, ServerError

metadata_bp = Blueprint("metadata", __name__)


@metadata_bp.route("/metadata")
@metadata_bp.route("/metadata/<int:version>")
def metadata(version=None):
    try:
        results = elastic.metadata(version)
    except ElasticsearchError:
        raise ServerError("Search failed to connect")

    return results
