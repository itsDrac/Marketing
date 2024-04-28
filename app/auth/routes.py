from app.auth import bp
from flask import render_template, request


@bp.route("/login", methods=["GET", "POST"])
def login():
    return render_template("login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        return "Post request"
    return render_template("register.html")
