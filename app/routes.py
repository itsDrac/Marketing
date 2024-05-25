from app.models import (
        Agency as AgencyModel,
        LexAcc as LexAccModel,
        Customer as CustomerModel
        )
from app.errors import UserDoesntExist, UserAlreadyExist, CustomerAlreadyExist
from app.database import db
from app.utils import login_required
from flask import (
        Blueprint,
        request,
        render_template,
        redirect,
        flash,
        url_for,
        session,
        )
import requests as rq


bp = Blueprint('main',
               __name__,
               template_folder="templates",
               static_folder="static",
               )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get('currentAgency'):
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
        return redirect(url_for("main.lex_main"))

    return render_template("login.html", errors=formErrors)


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
            return redirect(url_for("main.login"))
        except UserAlreadyExist as e:
            formErrors['email'] = (e.msg, e.category)
        return render_template("register.html", errors=formErrors)

    return render_template("register.html", errors=formErrors)


@bp.route('/logout')
@login_required
def logout():
    session['currentAgency'] = None
    return redirect(url_for("hello"))


@bp.route('/lex-main', methods=["GET", "POST"])
@login_required
def lex_main():
    agency_id = session['currentAgency'].get("id")
    currentAgency = db.get_or_404(AgencyModel, agency_id)
    if request.method == "POST":
        apikey = request.form.get("key")
        orgname = request.form.get("orgname")
        orgid = request.form.get("orgid")
        print(f"in Lex-main function \n{apikey= }, {orgname= }, {orgid= }")
        existingLex = db.session.execute(
                db.select(LexAccModel).filter_by(key=apikey)
                ).scalar_one_or_none()
        if existingLex:
            flash("This account is already added for this agency", "danger")
            return redirect(url_for("main.lex_main"))
        lexacc = LexAccModel(
                key=apikey,
                orgID=orgid,
                agency_id=agency_id,
                agency=currentAgency,
                name=orgname)
        db.session.add(lexacc)
        db.session.commit()
        subscribe_to_invoice_event(lexacc.id)
        return redirect(url_for("main.lex_main"))

    lexaccs = db.session.execute(
            db.select(LexAccModel).filter_by(agency_id=agency_id)
            ).scalars()

    return render_template("Lex_main.html", lexaccs=lexaccs)


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
            "callbackUrl": "https://7d3a-2409-40d0-8-b664-9964-78d4-915d-d45b.ngrok-free.app"+"/invoice-event-callback"
            }
    res = rq.post(
            "https://api.lexoffice.io/v1/event-subscriptions",
            headers=headers,
            json=jsonData
            )

    print(res.status_code)

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


@bp.route('/lex-get-org')
@login_required
def lex_get_org():
    key = request.args.get("key")
    if not key:
        return "No key found"
    key = "Bearer " + key.strip()
    headers = {"Authorization": key, "Accept": "application/json"}
    res = rq.get("https://api.lexoffice.io/v1/profile", headers=headers)
    if res.status_code != 200:
        return render_template("htmx/lex_org_name.html", orgname=None)
    return render_template(
            "htmx/lex_org_name.html",
            orgname=res.json().get("companyName"),
            orgid=res.json().get("organizationId")
            )


@bp.route('/lex-customer/<int:lexid>', methods=["GET", "POST"])
@login_required
def lex_customer(lexid: int):
    agency_id = session['currentAgency'].get("id")
    currentAgency = db.get_or_404(AgencyModel, agency_id)
    for lexacc in currentAgency.lex_acces:
        if lexacc.id == lexid:
            currentLexacc = lexacc
    if not currentLexacc:
        flash("Incorrect lex account id", "danger")
        return redirect(url_for("main.lex_main"))
    if request.method == "POST":
        customerId = request.form.get("customerId")
        customerName = request.form.get("customerName")
        print(f"{customerId= }, {customerName= }, {currentLexacc.name= }")
        try:
            currentLexacc.add_customer(lexID=customerId, name=customerName)
            db.session.commit()
        except CustomerAlreadyExist as e:
            flash(e.msg, e.category)

    print("In lex main function--> ", currentLexacc.id)
    customers = db.session.execute(
            db.select(CustomerModel).filter_by(lexAccId=currentLexacc.id)
            ).scalars().fetchall()

    return render_template(
            "lex_customer.html",
            lexApiKey=currentLexacc.key,
            customers=customers
            )


@bp.route('/lex-get-customer')
@login_required
def lex_get_customer():
    customerId = request.args.get("customerId")
    key = request.args.get("lexApiKey")
    if not key:
        return "No key found"
    if not customerId:
        return "No customerId found"
    key = "Bearer " + key.strip()
    headers = {"Authorization": key, "Accept": "application/json"}
    url = "https://api.lexoffice.io/v1/contacts/"+customerId.strip()
    res = rq.get(url, headers=headers)
    print(res.json())
    if res.status_code != 200:
        return render_template("htmx/lex_customer_name.html", customerName=None)
    return render_template(
            "htmx/lex_customer_name.html",
            customerName=res.json().get("company").get("name")
            )


@bp.route("/invoice-event-callback", methods=["POST"])
def invoice_event_callback():
    print("Inside invoice_event_callback")
    requestData = request.get_json()
    print("In function invoice_event_callback \n", requestData)
    if requestData.get("eventType") == "invoice.created":
        resID = requestData.get("resourceId")
        orgID = requestData.get("organizationId")
        fetch_invoice_data(resID, orgID)

    return "Thanks"


# need to make a function which will fetch the invoice data.
def fetch_invoice_data(invoiceID, orgID):
    # agency_id = session['currentAgency'].get("id")
    # currentAgency = db.get_or_404(AgencyModel, agency_id)
    currentLexacc = db.session.execute(
            db.select(LexAccModel).filter_by(orgID=orgID)
            ).scalar_one_or_none()
    if not currentLexacc:
        return None
    key = "Bearer " + currentLexacc.key.strip()
    headers = {"Authorization": key, "Accept": "application/json"}
    url = "https://api.lexoffice.io/v1/invoices/"+invoiceID.strip()
    res = rq.get(url, headers=headers)
    add_invoice(res.json())


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
# TODO: Add a webhook callback url for invoice
# TODO: Need to check whenever that webhook callback URL is requested.
# TODO: With the given data I'll fetch the lex office and check of the user would
# have added the customer I'll have to add the invoice in database.
# TODO: Need to create a table for Invoice. with net and gross amount for customer.
