import os
import secrets
import hashlib
import base64
import requests
from urllib import parse
from app.deutsche import bp
from app.deutsche.utils import get_access_token
from flask import (
    request,
    render_template,
    redirect,
    flash,
    url_for,
    session,
    )

# Make a seprate function which'll check if session has refresh token then get the access token and return the html file with form. If not then redirect to login_to_bank function.  # noqa: E501


@bp.route('/', methods=["GET", "POST"])
def deutsche_bank():
    if not session.get('deutsche'):
        return redirect(url_for('deutsche.login_to_bank'))
    transactions = {}
    if request.method == "POST":
        if not session.get('deutsche').get("accessToken"):
            return redirect(url_for('deutsche.login_to_bank'))
        transactions = get_history(request.form)
        print("here came?\t l:30")
        print(transactions)
    return render_template("deut_main.html", transactions=transactions)


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
        "redirect_uri": os.getenv("HOST_URL")+"deutsche/deutsche-auth",  # noqa: E501
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
        "redirect_uri": os.getenv("HOST_URL")+"deutsche/deutsche-auth",  # noqa: E501
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
    return redirect(url_for('deutsche.deutsche_bank'))


def get_history(formData):
    sessionDeutsche = {}
    # Get form data. (IBAN, from and to date).
    print("This is form data\n", formData)
    # Get access token from session.
    accessToken = "Bearer " + session.get('deutsche').get("accessToken")
    # Make request to deutsche bank to get Transactions history.
    requestHeaders = {
        "Authorization": accessToken
        }
    requestParams = {
        "iban": formData.get("iban"),
        "limit": 15,
        }
    if formData.get("form_date"):
        requestParams["bookingDateFrom"] = formData.get("form_date")
    if formData.get("to_date"):
        requestParams["bookingDateTo"] = formData.get("to_date")
    res = requests.get('https://simulator-api.db.com:443/gw/dbapi/banking/transactions/v2', headers=requestHeaders, params=requestParams)  # noqa: E501
    print(res.status_code)
    if res.status_code == 400:
        flash("Unable to fetch transactions, enter valid dates", "danger")
        return {}
    # check response if access token expired then call get_access_token
    if res.status_code == 401:
        refershToken = session.get('deutsche').get("refershToken")
        sessionDeutsche["accessToken"] = get_access_token(refershToken)
        session['deutsche'] = sessionDeutsche
        flash("Re-loggedin to bank, Please try again", "warning")
        return {}
    # Parse and send selected Data.
    print(res.json())
    # Make HTML file and Table with given data.
    # Return data.
    return res.json().get("transactions")
