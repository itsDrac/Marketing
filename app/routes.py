from app.models import (
        Agency as AgencyModel,
        LexAcc as LexAccModel,
        Customer as CustomerModel
        )
from app.errors import UserDoesntExist, UserAlreadyExist, CustomerAlreadyExist
from app.database import db
from app.utils import (
        login_required,
        subscribe_to_invoice_event,
        add_invoice, is_admin,
        fetch_sev_invoice
        )
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
        sessionAgency['isAdmin'] = is_admin(existingAgency.email)
        print(sessionAgency)
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
        # TODO: update different agency to add same lex account.
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
                name=orgname,
                source="Lex"
                )
        db.session.add(lexacc)
        db.session.commit()
        subscribe_to_invoice_event(lexacc.id)
        return redirect(url_for("main.lex_main"))

    lexaccs = db.session.execute(
        db.select(LexAccModel).filter_by(agency_id=agency_id).filter_by(source="Lex")
        ).scalars()

    return render_template("Lex_main.html", lexaccs=lexaccs)


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
    # currentAgency = db.get_or_404(AgencyModel, agency_id)
    currentLexacc = db.get_or_404(LexAccModel, lexid)
    # for lexacc in currentAgency.lex_acces:
    #     if lexacc.id == lexid:
    #         currentLexacc = lexacc
    if currentLexacc.agency_id != agency_id:
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


@bp.route("/sev-main", methods=["GET", "POST"])
@login_required
def sev_main():
    agency_id = session['currentAgency'].get("id")
    currentAgency = db.get_or_404(AgencyModel, agency_id)
    if request.method == "POST":
        apikey = request.form.get("key")
        orgname = request.form.get("orgname")
        orgid = request.form.get("orgid")
        print(f"in Sev Desk function \n{apikey= }, {orgname= }, {orgid= }")
        existingLex = db.session.execute(
                db.select(LexAccModel).filter_by(key=apikey)
                ).scalar_one_or_none()
        if existingLex:
            flash("This account is already added for this agency", "danger")
            return redirect(url_for("main.sev_main"))
        sevacc = LexAccModel(
                key=apikey,
                orgID=orgid,
                agency_id=agency_id,
                agency=currentAgency,
                name=orgname,
                source="Sev"
                )
        db.session.add(sevacc)
        db.session.commit()

    sevaccs = db.session.execute(
        db.select(LexAccModel).filter_by(agency_id=agency_id).filter_by(source="Sev")
        ).scalars()

    return render_template("sev_main.html", sevaccs=sevaccs)


@bp.route("/sev-get-org")
def sev_get_org():
    key = request.args.get("key")
    if not key:
        return "No key found"
    headers = {"Authorization": key, "Accept": "application/json"}
    payloads = {"embed": "sevClient"}
    url = "https://my.sevdesk.de/api/v1/CheckAccount"
    res = rq.get(url, headers=headers, params=payloads)
    if res.status_code != 200:
        return render_template("htmx/sev_org_name.html", orgname=None)
    orgname = res.json().get("objects")[0].get("sevClient").get("name")
    orgid = res.json().get("objects")[0].get("sevClient").get("id")
    return render_template("htmx/sev_org_name.html", orgname=orgname, orgid=orgid)


# Make Invoice page for Sevdesk account.
@bp.route("/sev-invoice/<int:sevid>", methods=["GET", "POST"])
def sev_invoice(sevid: int):
    agency_id = session['currentAgency'].get("id")
    currentSevacc = db.get_or_404(LexAccModel, sevid)
    sevApiKey = currentSevacc.key
    if currentSevacc.agency_id != agency_id:
        flash("Incorrect lex account id", "danger")
        return redirect(url_for("main.lex_main"))
    if request.method == "POST":
        invoiceId = request.form.get("invoiceid")
        customerName = request.form.get("customerName")
        # key = request.form.get("sevApiKey")
        res = fetch_sev_invoice(sevApiKey, invoiceId.strip()).json()
        customerSevID = res.get("objects")[0].get("contact").get("id")
        existingCustomer = db.session.execute(
                db.select(CustomerModel).filter_by(lexID=customerSevID)
                ).scalar_one_or_none()
        if not existingCustomer:
            existingCustomer = currentSevacc.add_customer(customerSevID, customerName)
        existingCustomer.totalGrossAmount += float(res.get("objects")[0].get("sumGross"))
        existingCustomer.totalNetAmount += float(res.get("objects")[0].get("sumNet"))
        db.session.commit()

        print(f"{invoiceId= } {sevApiKey= } \n post method of sev_invoice l:285")
    customers = db.session.execute(
            db.select(CustomerModel).filter_by(lexAccId=currentSevacc.id)
            ).scalars().fetchall()
    return render_template("sev_invoice.html",
                           sevApiKey=sevApiKey,
                           customers=customers
                           )


# Make Invoice page for Sevdesk account.
@bp.route("/sev-get-invoice")
def sev_get_invoice():
    invoiceId = request.args.get("invoiceid")
    key = request.args.get("sevApiKey")
    if not key:
        return "No key found"
    if not invoiceId:
        return "No customerId found"
    res = fetch_sev_invoice(key, invoiceId.strip())
    if res.status_code != 200:
        return render_template("htmx/sev_invoice_details.html", customerName=None)
    customerName = f"{res.json().get('objects')[0].get('contact').get('surename')} \
{res.json().get('objects')[0].get('contact').get('familyname')}"
    return render_template("htmx/sev_invoice_details.html", customerName=customerName)
