<<<<<<< HEAD
from flask import Blueprint
=======
from flask import (
    Blueprint,
)
>>>>>>> 6395ab95517dd329f23bd4b17bf0256c45d1a2f4
from pydat.api.utils import es as elastic
from pydat.api.controller.exceptions import ClientError, ServerError

metadata_bp = Blueprint("metadata", __name__)


@metadata_bp.route("/metadata")
<<<<<<< HEAD
@metadata_bp.route("/metadata/<version>")
=======
@metadata_bp.route("/metadata/<float:version>")
>>>>>>> 6395ab95517dd329f23bd4b17bf0256c45d1a2f4
def metadata(version=None):
    try:
        if version:
            version = int(version)
            if version < 0:
                raise ValueError
    except ValueError:
        raise ClientError(f'Version {version} must be a valid integer')

    try:
        results = elastic.metadata(version)
    except elastic.NotFoundError:
        raise ClientError(f'Version {version} does not exist', 404)
    except elastic.ElasticsearchError:
        raise ServerError("Search failed to connect")

    return results
