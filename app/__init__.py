import os

from flask import Flask
from app.extensions import db
from app.auth import bp as auth_bp


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_prefixed_env()
    db.init_app(app)
    app.register_blueprint(auth_bp)
    with app.app_context():
        db.create_all()

    @app.route("/")
    def hello():
        return "Hello World!"

    return app
