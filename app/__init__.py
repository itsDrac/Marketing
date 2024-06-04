import os

from flask import Flask, render_template, url_for
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
    def home():
        print(url_for("main.invoice_event_callback", _external=True))
        return render_template("home.html")

    return app
