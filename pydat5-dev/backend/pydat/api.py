from flask import Flask

from api import create_app

if __name__ == '__main__':
    app = create_app()
    app.run()
