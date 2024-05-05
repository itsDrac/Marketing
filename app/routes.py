from flask import (
        Blueprint,
        request,
        render_template,
        redirect,
        flash,
        url_for,
        session,
        )
from app.models import Agency as AgencyModel
from app.errors import UserDoesntExist, UserAlreadyExist
from app.database import db
from app.utils import login_required

bp = Blueprint('main',
               __name__,
               template_folder="templates",
               static_folder="static",
               )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session['currentAgency']:
        return redirect(url_for("hello"))
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
