import os

from flask import Flask
from app.database import db
from app.routes import bp


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_prefixed_env()
    db.init_app(app)
    app.register_blueprint(bp)
    with app.app_context():
        db.create_all()

    @app.route("/")
    def hello():
        return "Hello World!"

    return app
