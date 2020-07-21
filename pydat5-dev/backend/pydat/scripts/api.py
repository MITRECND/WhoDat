from flask import Flask

from pydat.api import create_app

def main():
    app = create_app()
    app.run()
