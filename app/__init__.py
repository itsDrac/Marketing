from flask import Flask, render_template, url_for, request
from dotenv import load_dotenv
from app.database import db
from app.routes import bp
from app.admin import bp as admin_bp
from app.deutsche import bp as deut_bp
from app.finapi import bp as fin_bp


load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config.from_prefixed_env()
    db.init_app(app)
    app.register_blueprint(bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(deut_bp, url_prefix="/deutsche")
    app.register_blueprint(fin_bp, url_prefix="/finapi")
    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        print(url_for("main.invoice_event_callback", _external=True))
        return render_template("home.html")

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('page_not_found.html'), 404

    return app
