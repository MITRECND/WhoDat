import yaml
from flask import (
    Blueprint,
    request,
    session,
)
from pydat.api.controller.exceptions import InvalidUsage
from pydat.core.plugins import USER_PREF

bp = Blueprint("session", __name__)


def is_valid(param, g_params):
    if param in g_params:
        val_type = type(g_params[param])
        new_val = request.form[param]
        if isinstance(new_val, val_type):
            return None
        return f"Type mismatch of {type(new_val)} and {val_type} for {param}"
    return f"Nonexistant parameter {param}"


def put_pref(curr_pref, new_pref):
    error = ""
    if len(curr_pref) != len(new_pref):
        error = f"Expected {len(curr_pref)} params, gave {len(new_pref)}"
    else:
        for param in new_pref.keys():
            temp_error = is_valid(param, curr_pref.keys())
            if temp_error:
                error += temp_error + "\n"

    if error == "":
        return None
    return error


def patch_pref(curr_pref, new_pref):
    error = ""
    for param in new_pref.keys():
        temp_error = is_valid(param, new_pref.keys())
        if temp_error is None:
            curr_pref[param] = new_pref[param]
        else:
            error += temp_error + "\n"
    if error == "":
        return None
    return error


# look for global settings
@bp.route("/global", methods=("PUT", "PATCH", "GET",))
def global_pref():
    # print(session)
    if "global" not in session:
        try:
            with open("global.yaml") as stream:
                session["global"] = yaml.safe_load(stream)
        except FileNotFoundError:
            session["global"] = None
        if session["global"] is None:
            session["global"] = {}

    if request.method == "GET":
        return session["global"]

    error = None
    g_pref = session["global"]

    if request.method == "PUT":
        error = put_pref(g_pref, request.form)
        if error is None:
            session["global"] = request.form

    elif request.method == "PATCH":
        error = patch_pref(g_pref, request.form)

    if error is not None:
        raise InvalidUsage(error)


@bp.route("/<path:path>", methods=("PUT", "PATCH", "GET",))
def preference(path):
    if path not in USER_PREF.keys():
        raise InvalidUsage(f"Nonexistant preferences for {path}", 404)
    if path not in session:
        session[path] = USER_PREF[path]

    if request.method == "GET":
        return session[path]

    error = None
    if request.method == "PUT":
        error = put_pref(session[path], request.form)
        if error is None:
            session[path] = request.form

    elif request.method == "PATCH":
        error = patch_pref(session[path], request.form)

    if error is not None:
        raise InvalidUsage(error)
