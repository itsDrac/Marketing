from app.admin import bp
from app.utils import login_required
from app.database import db
from app.models import (
        Agency as AgencyModel,
        Customer as CustomerModel,
        LexAcc as LexAccModel,
        )
from flask import render_template, redirect, session, url_for


@bp.get("/")
@login_required
def main():
    if not session.get("currentAgency").get("isAdmin"):
        return redirect(url_for("main.lex_main"))
    return render_template("main.html")
