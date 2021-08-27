from flask import jsonify, current_app


class BaseError(Exception):
    """Exception class for signaling response errors

    Attributes:
        message: Optional customizable error message
        status_code: Error code
        payload: Optional dict payload
    """

    def __init__(self, message, status_code=None, payload=None, nolog=False):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        self.nolog = nolog

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["status"] = self.status_code
        rv["error"] = self.message
        return rv


class ClientError(BaseError):
    """Exception class for signaling client errors. Child of BaseError

    Attributes:
        status_code: Default error code 400.
    """
    status_code = 400


class ServerError(BaseError):
    """Exception class for signaling server errors. Child of BaseError

    Attributes:
        status_code: Default error code 500.
    """
    status_code = 500


def handle_error(error):
    if isinstance(error, ServerError) and not error.nolog:
        current_app.logger.exception(error.message)
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def register_errors(app):
    app.register_error_handler(BaseError, handle_error)
