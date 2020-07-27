from flask import (
    Blueprint,
)
from pydat.api.utils import es as elastic
from pydat.api.controller.exceptions import ClientError, ServerError

metadata_bp = Blueprint("metadata", __name__)


@metadata_bp.route("/metadata")
@metadata_bp.route("/metadata/<float:version>")
def metadata(version=None):
    try:
        results = elastic.metadata(version)
    except elastic.ElasticsearchError:
        raise ServerError("Search failed to connect")

    return results
