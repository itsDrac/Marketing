from app.errors import LoginFunctionUndefined
from app.models import LexAcc as LexAccModel, Customer as CustomerModel
from app.database import db
from flask import session, current_app, redirect, url_for, flash
from functools import wraps
import requests as rq


def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not session['currentAgency']:
            if 'LOGIN_FUNCTION' in current_app.config:
                return redirect(url_for(current_app.config['LOGIN_FUNCTION']))
            raise LoginFunctionUndefined
        return func(*args, **kwargs)
    return decorated_view


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not session.get("currentAgency").get("isAdmin"):
            return redirect(url_for("main.lex_main"))
        return func(*args, **kwargs)
    return decorated_view


def is_admin(email: str):
    adminList = current_app.config['ADMIN_LIST'].split(',')
    return email in adminList


def subscribe_to_invoice_event(lexaccID):
    currentLexacc = db.get_or_404(LexAccModel, lexaccID)
    key = "Bearer " + currentLexacc.key.strip()
    headers = {
            "Authorization": key,
            "Accept": "application/json",
            "Content-Type": "application/json"
            }
    jsonData = {
            "eventType": "invoice.created",
            "callbackUrl": "https://d3a6-2401-4900-1c68-b58c-eca1-6637-1588-e292.ngrok-free.app"+"/invoice-event-callback"
            # "callbackUrl": url_for("main.invoice_event_callback", _external=True)
            }
    res = rq.post(
            "https://api.lexoffice.io/v1/event-subscriptions",
            headers=headers,
            json=jsonData
            )

    if res.json().get("id"):
        print("invoice event subscribed")
        print(res.json().get("resourceUri"))
        flash(f"{currentLexacc.name} is subscribed to invoice created", "success")
        return
    else:
        print(res.json())
        print(res.status_code)
        print("invoice event did not subscribed")
        flash(f"{currentLexacc.name} is not subscribed to invoice created", "warning")


def add_invoice(invoice_data):
    currentLexacc = db.session.execute(
            db.select(LexAccModel).filter_by(orgID=invoice_data.get("organizationId"))
            ).scalar_one_or_none()
    if not currentLexacc:
        return None
    customerID = invoice_data.get("address").get("contactId")
    if not customerID:
        return None
    currentCustomer = db.session.execute(
            db.select(CustomerModel).filter_by(lexID=customerID)
            ).scalar_one_or_none()
    if not currentCustomer:
        return None
    # Add Invoice gross and net amount and link it with current customer.
    currentCustomer.add_invoice_amounts(
            invoice_data.get("totalPrice").get("totalGrossAmount"),
            invoice_data.get("totalPrice").get("totalNetAmount"),
            )
    db.session.commit()


def fetch_sev_invoice(key, invoiceId):
    headers = {"Authorization": key, "Accept": "application/json"}
    payloads = {"embed": "contact"}
    url = "https://my.sevdesk.de/api/v1/Invoice/"+invoiceId
    res = rq.get(url, headers=headers, params=payloads)
    return res
