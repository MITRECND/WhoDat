import yaml
from flask import (
    Blueprint,
    request,
    session,
)
from api.controller.exceptions import InvalidUsage
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


# look for global settings
@bp.route("/global", methods=("PUT", "PATCH", "GET",))
def global_pref():
    g_pref = None
    try:
        with open("global.yaml") as file:
            g_pref = yaml.load(file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        pass

    if g_pref is None:
        g_pref = {}

    g_params = session["global"]
    if request.method == "GET":
        return g_params

    error = ""
    if request.method == "PATCH":
        for param in request.form.keys():
            temp_error = is_valid(param, g_pref.keys())
            if temp_error is None:
                g_params[param] = request.form[param]
            else:
                error += temp_error + "\n"
        session["global"] = g_params

    elif request.method == "PUT":
        if len(g_params) != len(request.form):
            error = (
                f"Expected {len(g_params)} params, gave {len(request.form)}"
            )
        else:
            for param in request.form.keys():
                temp_error = is_valid(param, g_pref.keys())
                if temp_error:
                    error += temp_error + "\n"

        if error is None:
            session["global"] = request.form

    if error != "":
        raise InvalidUsage(error)


@bp.route('/<path:path>')
def preference(path):
    if path not in USER_PREF.keys():
        raise InvalidUsage(f"Nonexistant preferences for {path}", 404)

    if request.method == "PUT":
        pass
