import os

from flask import Flask
from app.database import db
from app.routes import bp
from app.admin import bp as admin_bp


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_prefixed_env()
    db.init_app(app)
    app.register_blueprint(bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    with app.app_context():
        db.create_all()

    @app.route("/")
    def hello():
        print(app.config['LEX_EVENT_CALLBACK_URL'])
        return "Hello World!"

    return app
