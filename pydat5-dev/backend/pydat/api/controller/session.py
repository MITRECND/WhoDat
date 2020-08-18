from flask import (
    Blueprint,
    request,
    session,
)
from pydat.api.controller.exceptions import ClientError
from pydat.api import preferences_manager


session_bp = Blueprint("session", __name__)


def setup_session(path):
    preferences = None
    try:
        preferences = preferences_manager.get_preferences(path)
        # define session[path]
        if session.get(path) is None:
            session[path] = {}
            for (name, _type) in preferences.items():
                session[path][name] = None
    except KeyError:
        raise ClientError(f"Nonexistant preferences for {path}", 404)


@session_bp.route("/session/<path:path>", methods=["GET"])
def get_preference(path):
    setup_session(path)
    return session[path]


@session_bp.route("/session/<path:path>", methods=["PATCH"])
def patch_preference(path):
    setup_session(path)

    if not request.is_json:
        raise ClientError("Expected JSON body")

    new_params = request.json

    for (name, value) in new_params.items():
        try:
            preferences_manager.validate_param(path, name, value)
        except (ValueError, TypeError):
            raise ClientError(f"Invalid param '{name}' in namespace {path}")

        session[path][name] = value

    return session[path]
