# dictionary of plugin user preferences
USER_PREF = {}


def add_user_pref(name, parameters):
    """Adds a user preference if it does not already exist

    Args:
        name (str): key value for what preferences belong to
        parameters (dict): maps parameter name to parameter type
    """
    if name not in USER_PREF:
        USER_PREF[name] = parameters


def get_user_pref(name):
    """Retrieves the preferences for module name if it exists.

    Args:
        name (str): identifier of whose preferences to retrieve

    Raises:
        KeyError: identifier does not have stored user preferences

    Returns:
        Dict of stored parameter-type pairs for module name
    """
    if name in USER_PREF:
        return USER_PREF[name]
    raise KeyError
