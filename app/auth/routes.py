from app.database import db
from app.auth import bp
from app.auth.models import Agency as AgencyModel
from app.auth.errors import UserAlreadyExist
from flask import render_template, request, flash, redirect, url_for


@bp.route("/login", methods=["GET", "POST"])
def login():
    return render_template("login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    formErrors = {}
    if request.method == "POST":
        try:
            AgencyModel.create_agency(
                    request.form['email'], password=request.form['password']
                    )
            db.session.commit()
            flash("Agency is registed, Please login.", "success")
            return redirect(url_for("auth.login"))
        except UserAlreadyExist as e:
            formErrors['email'] = (e.msg, e.category)
        return render_template("register.html", errors=formErrors)

    return render_template("register.html", errors=formErrors)
