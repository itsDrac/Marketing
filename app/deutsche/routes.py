import os
import secrets
import hashlib
import base64
import requests
from urllib import parse
from app.deutsche import bp
from flask import (
    request,
    redirect,
    flash,
    url_for,
    session,
    )


@bp.route('/login-to-bank')
def login_to_bank():
    sessionDeutsche = {}
    codeVerifier = secrets.token_hex(45)
    codeChallenge = hashlib.sha256(codeVerifier.encode("utf-8")).digest()
    codeChallenge = base64.urlsafe_b64encode(codeChallenge)
    codeChallenge = codeChallenge.decode("utf-8").replace("=", "")
    sessionDeutsche["codeVerifier"] = codeVerifier
    session['deutsche'] = sessionDeutsche
    requestParams = {
        "client_id": os.getenv("DEUTSCHE_CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": "https://4e6c-110-235-238-86.ngrok-free.app/deutsche/deutsche-auth",  # noqa: E501
        # TODO: Need to have scheme as "https"
        # "redirect_uri": url_for("deutsche.deutsche_auth",
        #                         _scheme="https", _external=True),
        "code_challenge_method": "S256",
        "code_challenge": codeChallenge,
        }
    qs = parse.urlencode(requestParams)
    return redirect('https://simulator-api.db.com/gw/oidc/authorize'+'?'+qs)


@bp.route('/deutsche-auth')
def deutsche_auth():
    authCode = request.args.get('code')
    codeVerifier = session.get("deutsche").get("codeVerifier")
    if not authCode:
        flash("Login Error with deutsche bank, Please try in some time", "danger")
        return redirect(url_for("home"))

    requestData = {
        "grant_type": "authorization_code",
        "code": authCode,
        # "redirect_uri": url_for("deutsche.deutsche_auth",
        #                         _scheme="https", _external=True),
        "redirect_uri": "https://4e6c-110-235-238-86.ngrok-free.app/deutsche/deutsche-auth",  # noqa: E501
        "code_verifier": codeVerifier
        }
    authHeader = base64.urlsafe_b64encode(
        (os.getenv("DEUTSCHE_CLIENT_ID")+":"+os.getenv("DEUTSCHE_CLIENT_KEY")).encode()  # noqa: E501
        )
    requestHeaders = {
        "Authorization": "Basic "+authHeader.decode("utf-8")
        }
    res = requests.post('https://simulator-api.db.com/gw/oidc/token', data=requestData, headers=requestHeaders)  # noqa: E501
    if not res.status_code == requests.codes.ok:
        flash("Login Error with deutsche bank, Please try in some time", "danger")
        return redirect(url_for("home"))
    resultData = res.json()
    sessionDeutsche = {}
    sessionDeutsche["accessToken"] = resultData.get("access_token")
    sessionDeutsche["refershToken"] = resultData.get("refresh_token")
    session['deutsche'] = sessionDeutsche
    # TODO: Create a HTML file with 1 input and 2 date field Input for IBAN and Dates for From and To date. # noqa E501 
    # TODO: Create a new route which will take above values as input and return html with Transactions data init.  # noqa E501
    return res.text
