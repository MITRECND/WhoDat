from pydat.api import create_app
import argparse


def _get_argparser():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--debug",
        action="store",
        dest="debug",
        default=False,
        help="debug mode for flask"
    )

    parser.add_argument(
        "--host",
        action="store",
        dest="host",
        default="127.0.0.1",
        help="host for running app"
    )

    parser.add_argument(
        "--port",
        action="store",
        dest="port",
        default=5000,
        help="port for running app"
    )

    return parser


def main():
    parser = _get_argparser()
    options = vars(parser.parse_args())

    app = create_app()
    app.run(debug=options["debug"], host=options["host"], port=options["port"])
