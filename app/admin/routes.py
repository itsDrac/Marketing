from app.admin import bp
from app.utils import admin_required
from app.database import db
from app.models import (
        Agency as AgencyModel,
        Customer as CustomerModel,
        LexAcc as LexAccModel,
        )
from flask import render_template, redirect, session, url_for, request


@bp.get("/")
@admin_required
def main():
    if not session.get("currentAgency").get("isAdmin"):
        return redirect(url_for("main.lex_main"))
    return render_template("main.html")


@bp.route("/all-agency")
@admin_required
def all_agency():
    source = request.args.get("source")
    print(source)
    result = db.session.execute(
            db.select(AgencyModel, LexAccModel).join(LexAccModel).where(
               LexAccModel.source == source
               ).order_by(AgencyModel.id.desc())
            ).all()
    return render_template("htmx/all_agency.html", result=result)


@bp.route('/get-customer/<int:lexid>')
@admin_required
def get_customer(lexid: int):
    currentLexacc = db.get_or_404(LexAccModel, lexid)
    customers = db.session.execute(
            db.select(CustomerModel).filter_by(lexAccId=currentLexacc.id)
            ).scalars().fetchall()
    return render_template(
            "get_customer.html",
            customers=customers
            )
