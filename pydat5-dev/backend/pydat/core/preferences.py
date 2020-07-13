# dictionary of plugin user preferences
USER_PREF = {}


def add_user_pref(name, parameters):
    if name not in USER_PREF:
        USER_PREF[name] = parameters


def get_user_pref(name):
    if name in USER_PREF:
        return USER_PREF[name]
    raise KeyError
