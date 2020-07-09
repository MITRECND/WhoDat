from flask import (
    Blueprint,
    request,
    session,
    make_response,
    jsonify
)
from pydat.api.controller.exceptions import InvalidUsage
from pydat.core.plugins import USER_PREF

bp = Blueprint("session", __name__)
USER_PREF["global"] = {"pi": int, "name": str, "development": bool}


# helper method for get_valid_parameters
# checks if param and param value is valid
def is_valid(param, new_pref, curr_pref):
    if param in curr_pref.keys():
        val_type = curr_pref[param]
        new_val = new_pref[param]
        if isinstance(new_val, val_type):
            return None
        return f"Type mismatch of {type(new_val)} and {val_type} for {param}"
    return f"Nonexistant parameter {param}"


# returns list specifying invalid parameters/values or None
# returns dictionary of valid param-value pairs
def get_valid_parameters(new_pref, curr_pref):
    error = []
    valid = {}
    for param in new_pref.keys():
        temp_error = is_valid(param, new_pref, curr_pref)
        if temp_error:
            error.append(temp_error)
        else:
            valid[param] = new_pref[param]

    if error == []:
        return None, valid
    return error, valid


@bp.route("/<path:path>", methods=("PUT", "PATCH", "GET",))
def preference(path):
    # check if path has preferences
    if path not in USER_PREF.keys():
        raise InvalidUsage(f"Nonexistant preferences for {path}", 404)
    # define session[path]
    if session.get(path) is None:
        session[path] = {}
        for param in USER_PREF[path]:
            session[path][param] = None

    if request.method == "GET":
        return session[path]

    error = None
    curr_pref = USER_PREF[path]
    new_pref = request.get_json()

    if request.method == "PUT":
        if len(new_pref) != len(curr_pref):
            error = f"Expected {len(curr_pref)} param, gave {len(new_pref)}"
        else:
            error, valid_param = get_valid_parameters(new_pref, curr_pref)
            if error is None:
                session[path] = valid_param

    elif request.method == "PATCH":
        error, valid_param = get_valid_parameters(new_pref, curr_pref)
        # only patch if all parameters are valid
        if error is None:
            for param in valid_param.keys():
                session[path][param] = valid_param[param]

    if error is not None:
        raise InvalidUsage(error)

    res = make_response(
        jsonify({"message": f"{path} preferences updated"}), 200
    )
    return res
