from flask import (
    current_app,
    Blueprint,
    request,
    session,
)
from pydat.api.controller.exceptions import ClientError


settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET"])
def get_settings():

    settings = {
        'enable_active_resolution': not current_app.config.get("DISABLERESOLVE", False)
    }

    for plugin in current_app.config.get('PYDAT_PLUGINS', []):
        settings[f"enable_plugin_{plugin}"] = True

    return settings