from app.database import db
from app.auth import bp
from app.auth.models import Agency as AgencyModel
from app.auth.errors import UserAlreadyExist, UserDoesntExist
from app.auth.utils import login_required
from flask import render_template, request, flash, redirect, url_for, session


@bp.route("/login", methods=["GET", "POST"])
def login():
    formErrors = {}
    sessionAgency = {}
    if request.method == "POST":
        try:
            existingAgency = AgencyModel.get_agency_from_email(request.form['email'])
        except UserDoesntExist as e:
            formErrors['email'] = (e.msg, e.category)
            return render_template("login.html", errors=formErrors)

        sessionAgency['id'] = existingAgency.id
        sessionAgency['email'] = existingAgency.email
        session['currentAgency'] = sessionAgency

        flash("Agency is Loggedin", "success")
        return redirect(url_for("hello"))

    return render_template("login.html", errors=formErrors)


@bp.route("/register", methods=["GET", "POST"])
def register():
    formErrors = {}
    if request.method == "POST":
        print(request.form['email'])
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


@bp.route('/logout')
@login_required
def logout():
    session['currentAgency'] = None
    return redirect(url_for("hello"))
