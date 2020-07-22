from flask import (
    Blueprint,
    request,
    session,
    make_response,
    jsonify
)
from pydat.api.controller.exceptions import ClientError
from pydat.core.preferences import add_user_pref, get_user_pref

session_bp = Blueprint("session", __name__)
# Add global preferences
# add_user_pref("global", {"pi": int, "name": str, "development": bool})


def is_valid(param, new_pref, curr_pref):
    """Helper method for get_valid_parameters.

    Checks if param exists in curr_pref and the value associated with param is
    the correct type.

    Args:
        param: String of preference paramater to test if valid.
        new_pref: Dict of parameter keys and values of new preferences
        curr_pref: Dict of valid parameter keys and values of preference type

    Returns:
        None if the parameter is valid. Error string detailing either a type
        mismatch or param being a nonexistant parameter.
    """
    if param in curr_pref.keys():
        val_type = curr_pref[param]
        new_val = new_pref[param]
        if isinstance(new_val, val_type):
            return None
        return f"Type mismatch of {type(new_val)} and {val_type} for {param}"
    return f"Nonexistant parameter {param}"


def get_valid_parameters(new_pref, curr_pref):
    """Determines valid parameter-value pairs.

    Args:
        new_pref: Dict mappping parameters to potential new preferences
        curr_pref: Dict mapping valid parameters to preference type

    Returns:
        Returns a tuple of a list of errors and a dictionary of valid
        parameter-preferences pairs. If there are no errors, will
        return None instead of a list.
    """
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


@session_bp.route("/session/<path:path>", methods=("PUT", "PATCH", "GET",))
def preference(path):
    # check if path has preferences
    curr_pref = None
    try:
        curr_pref = get_user_pref(path)
        # define session[path]
        if session.get(path) is None:
            session[path] = {}
            for param in curr_pref:
                session[path][param] = None
    except KeyError:
        raise ClientError(f"Nonexistant preferences for {path}", 404)

    if request.method == "GET":
        return session[path]

    error = None
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
        raise ClientError(error)

    res = make_response(
        jsonify({"message": f"{path} preferences updated"}), 200
    )
    return res
