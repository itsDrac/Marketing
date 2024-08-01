from app.finapi import bp
from app.models import BankUser as BankUserModel, Agency as AgencyModel
from app.database import db
from flask import render_template, request, abort, session, flash, redirect, url_for
import requests as rq
import os


@bp.route('/', methods=["GET", "POST"])
def main():
    currentAgency = session.get('currentAgency')
    if not session.get("BankCustomer"):
        session["BankCustomer"] = []
    customers = db.session.execute(db.select(BankUserModel).where(
        BankUserModel.agency_id == currentAgency.get("id")
        )).scalars()
    return render_template("fin_main.html", customers=customers)


# Make a function that returns access token of finapi client.
def get_client_access():
    accessToken = "Bearer "
    clientId = os.getenv("FINAPI_CLIENT_ID")
    clientSec = os.getenv("FINAPI_CLIENT_SECRET")
    formData = {
            "grant_type": "client_credentials",
            "client_id": clientId,
            "client_secret": clientSec
            }
    res = rq.post(os.getenv("FINAPI_URL")+"/api/v2/oauth/token", data=formData)
    if res.status_code != 200:
        print("in get client access function")
        abort(500)

    return accessToken+res.json().get("access_token")


@bp.route('/create-customer', methods=["POST"])
def create_customer():
    # check if email or phone number already exist in database.
    existingCustomer = db.session.execute(
            db.select(BankUserModel).where(BankUserModel.email == request.form.get("email") or BankUserModel.phone == request.form.get("phone"))  # noqa: E:501
            ).scalar_one_or_none()
    if existingCustomer:
        return '<p class="fs-3 text-danger">User with same email or phone already exist</p>'  # noqa: E:501
    currentAgency = session.get('currentAgency')
    agency = db.session.execute(db.select(AgencyModel).where(AgencyModel.id == currentAgency.get("id"))).scalar_one_or_none()  # noqa: E:501
    newCustomer = BankUserModel(
            email=request.form.get("email"),
            phone=request.form.get("phone"),
            password=request.form.get("password"),
            agency_id=agency.id,
            agency=agency
            )
    db.session.add(newCustomer)
    db.session.commit()

    clientAccessToken = get_client_access()
    # Make user in finapi.
    jsonData = {
        "id": newCustomer.id,
        "password": newCustomer.password,
        "email": newCustomer.email,
        "phone": newCustomer.phone,
        "isAutoUpdateEnabled": True
    }
    headers = {
            "authorization": clientAccessToken
            }
    res = rq.post(os.getenv("FINAPI_URL")+"/api/v2/users",
                  json=jsonData,
                  headers=headers
                  )
    if res.status_code != 201:
        abort(500)
    # customer is created.
    get_customer_token(newCustomer.id)
    customerinfo = get_customer_info(newCustomer.id)
    webFormData = get_web_form(customerinfo)

    newCustomer.webform_id = webFormData.get("id")
    db.session.commit()
    webFormUrl = webFormData.get("url")
    # send request to for bank connection and get the form link.
    # save the form id for user.
    # send back the form link in html file.
    return f'<a class="btn btn-primary" target="_blank" href="{webFormUrl}">Please fill this form</a>'  # noqa E:105


@bp.route("webform-status", methods=["POST"])
def webform_status():
    data = request.json
    if not data.get("status") == "COMPLETED":
        return {}
    existingCustomer = db.session.query(db.select(BankUserModel).where(
        BankUserModel.webform_id == data.get("webFormId")
        )).scalar_one_or_none()
    existingCustomer.is_connected = True
    db.session.commit()
    print(existingCustomer)
    return {}


@bp.route("/get-web-form")
def get_webForm():
    customerID = request.args.get("customer_id")
    if not customerID:
        return redirect(url_for("finapi.main"))
    customerinfo = get_customer_info(customerID)
    if not customerinfo:
        get_customer_token(customerID)
        customerinfo = get_customer_info(customerID)
    print(customerinfo)
    webFormData = get_web_form(customerinfo)
    print(customerID)

    existingCustomer = db.get_or_404(BankUserModel, customerID)
    existingCustomer.webform_id = webFormData.get("id")
    db.session.commit()
    webFormUrl = webFormData.get("url")
    return f'<a class="btn btn-primary" target="_blank" href="{webFormUrl}">Please fill this form</a>'  # noqa E:105


@bp.route("/fetch-transactions")
def fetch_transactions():
    customerID = request.args.get("customer_id")
    if not customerID:
        return redirect(url_for("finapi.main"))
    customerinfo = get_customer_info(customerID)
    if not customerinfo:
        get_customer_token(customerID)
        customerinfo = get_customer_info(customerID)
    print(customerinfo)
    params = {"view": "userView"}
    headers = {
            "authorization": customerinfo.get("access_token"),
            }
    res = rq.get(os.getenv("FINAPI_URL")+"/api/v2/transactions", params=params, headers=headers)  # noqa: E:501
    print(res.status_code)
    print(res.text)
    transactions = res.json().get("transactions")
    balance = res.json().get("balance")
    return render_template("transactions.html", balance=balance, transactions=transactions)  # noqa E:501


# pass session object of customer {id:1,"access_token":"1221212"}
# returns response from API in dict. Need to fetch id and url from form
def get_web_form(customerinfo):
    if not customerinfo:
        print("No customer info passed")
        abort(505)
    headers = {
            "authorization": customerinfo.get("access_token").strip(),
            "accept": "application/json",
            "content-type": "application/json"
            }
    jsonData = {
            "skipBalancesDownload": False,
            "skipPositionsDownload": False,
            "loadOwnerData": False,
            "maxDaysForDownload": 36,
            "accountTypes": [
                "CHECKING",
                "SAVINGS"
            ],
            "allowedInterfaces": [
                "XS2A"
            ],
            "callbacks": {
                "finalised": os.getenv("HOST_URL")+"/finapi/webForms-status"
            },
            "allowTestBank": True
    }
    res = rq.post(os.getenv("FINAPI_WEBFORM_URL")+"/api/webForms/bankConnectionImport",
                  json=jsonData,
                  headers=headers
                  )
    if res.status_code == 401:
        flash("Please try again the, connection is now setup", "warning")
        get_customer_token(customerinfo.get("id"))
        return redirect(url_for("finapi.main"))
        # redirect user to bank main page and let them try again to get the link.

    if not res.status_code == 201:
        print("get_web_form function abort")
        print(res.text)
        abort(505)

    return res.json()


# Takes customerID as input and fetchs the customer access and refresh token.
# store the access token in session and refresh token in database.
def get_customer_token(customerID):
    # get access and refresh token for user,
    customerAccessToken = "Bearer "
    existingCustomer = db.get_or_404(BankUserModel, customerID)
    clientId = os.getenv("FINAPI_CLIENT_ID")
    clientSec = os.getenv("FINAPI_CLIENT_SECRET")
    formData = {
            "grant_type": "password",
            "client_id": clientId,
            "client_secret": clientSec,
            "username": existingCustomer.id,
            "password": existingCustomer.password
            }
    res = rq.post(os.getenv("FINAPI_URL")+"/api/v2/oauth/token", data=formData)
    if res.status_code != 200:
        print("get_customer_token function abort")
        print(res.json())
        abort(500)

    sessionData = {
            "id": existingCustomer.id,
            "access_token": customerAccessToken+res.json().get("access_token")
            }
    existingCustomer.refresh_token = res.json().get("refresh_token")
    db.session.commit()
    session["BankCustomer"].append(sessionData)


# return the session data for passed customerID.
def get_customer_info(customerID):
    if not session.get("BankCustomer"):
        return
    for info in session.get("BankCustomer"):
        if info.get("id") == int(customerID):
            return info
