from app.lex import bp
from app.lex.models import LexAcc
from flask import render_template


@bp.get("/")
def home():
    return render_template("home.html")
