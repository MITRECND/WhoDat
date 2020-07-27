from flask import (
    Blueprint,
    request,
)
from pydat.api.controller.exceptions import ClientError, ServerError
from pydat.api.utils import es as elastic

query_bp = Blueprint("query", __name__)


@query_bp.route('/query')
def query():
    try:
        query = request.args.get("query", default=None, type=str)
        page_size = int(request.args.get("size", default=20))
        page_num = int(request.args.get("page", default=1))
        unique = request.args.get("unique", default=False)
        if unique.lower() == 'true':
            unique = True
        else:
            unique = False
    except ValueError:
        raise ClientError("Input paramaters are of the wrong type")

    if query is None:
        raise ClientError("Query required")

    error = None
    if page_size < 1:
        error = f"Invalid page size {page_size} provided"
    elif page_num < 1:
        error = f"Invalid page number {page_num}"
    if error is not None:
        raise ClientError(error)

    skip = (page_num-1)*page_size
    try:
        results = elastic.advanced_search(query, skip, page_size, unique)
    except elastic.ElasticsearchError:
        raise ServerError("Search failed to connect")
    except IndexError:
        raise ClientError(f"Page number {page_num} is too high")

    return results
