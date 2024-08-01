from app.database import db
from app.errors import UserAlreadyExist, UserDoesntExist, CustomerAlreadyExist
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from typing import List, Optional
from datetime import datetime
import sqlalchemy as sa
import sqlalchemy.orm as so

# TODO: Optimize defining on fileds, such as:
# TODO: For email have: email: Mapped[str] = mapped_column(sa.String(60), unique=True)
# TODO: replace id with _id throughout the codebase.
# TODO: Make more functional and scalable tables.


class Agency(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column(deferred=True)
    lex_acces: Mapped[Optional[List["LexAcc"]]] = relationship(
            back_populates="agency", cascade="all, delete-orphan", init=False
            )
    manual: Mapped[Optional[List["Manual"]]] = relationship(
            back_populates="agency", cascade="all, delete-orphan", init=False
            )
    bank_users: so.WriteOnlyMapped["BankUser"] = relationship(
            back_populates="agency", cascade="all, delete-orphan", init=False
            )

    @staticmethod
    def create_agency(email, password):
        try:
            existingUser = Agency.get_agency_from_email(email)
            if existingUser:
                raise UserAlreadyExist("User with this email already exist", "danger")
        except UserDoesntExist:
            hdPassword = Agency.genrate_password(password)
            newUser = Agency(email=email, password=hdPassword)
            db.session.add(newUser)

    @staticmethod
    def get_agency_from_email(email):
        existingUser = db.session.execute(
                db.select(Agency).filter_by(email=email)
                ).scalar_one_or_none()
        if not existingUser:
            raise UserDoesntExist("User with this email doesn't exist", "danger")
        return existingUser

    @staticmethod
    def genrate_password(password):
        return generate_password_hash(password)

    @staticmethod
    def check_password(hd_password, password):
        return check_password_hash(hd_password, password)


class LexAcc(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    key: Mapped[str] = mapped_column(unique=True)
    orgID: Mapped[str] = mapped_column(unique=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agency.id"))
    agency: Mapped["Agency"] = relationship(back_populates="lex_acces")
    customers: Mapped[Optional[List["Customer"]]] = relationship(
            back_populates="lexAcc", cascade="all, delete-orphan", init=False
            )
    name: Mapped[str]
    source: Mapped[str] = mapped_column(nullable=False)
    eventID: Mapped[Optional[str]] = mapped_column(init=False)
    added_on: Mapped[datetime] = mapped_column(default_factory=datetime.utcnow)

    def add_customer(self, lexID, name):
        existingCustomer = db.session.execute(
                db.select(Customer).filter_by(lexID=lexID)
                ).scalar_one_or_none()
        if existingCustomer:
            raise CustomerAlreadyExist("Customer already exist.", "danger")
        newCustomer = Customer(lexID=lexID, lexAccId=self.id, lexAcc=self, name=name)
        db.session.add(newCustomer)
        return newCustomer


class Customer(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    lexID: Mapped[str] = mapped_column(unique=True)
    lexAccId: Mapped[int] = mapped_column(ForeignKey("lex_acc.id"))
    lexAcc: Mapped["LexAcc"] = relationship(back_populates="customers")
    name: Mapped[str]
    # invoices: Mapped[Optional[List["Invoice"]]] = relationship(
    #         back_populates="customer", cascade="all, delete-orphan", init=False
    #         )
    totalGrossAmount: Mapped[float] = mapped_column(
            nullable=False,
            init=False,
            default_factory=lambda: 0.0
            )
    totalNetAmount: Mapped[float] = mapped_column(
            nullable=False,
            init=False,
            default_factory=lambda: 0.0
            )
    addedOn: Mapped[datetime] = mapped_column(default_factory=datetime.utcnow)

    def add_invoice_amounts(self, grossAmount, netAmount):
        self.totalGrossAmount += grossAmount
        self.totalNetAmount += netAmount


# class Invoice(db.Model):
#     id: Mapped[int] = mapped_column(primary_key=True, init=False)
#     lexID: Mapped[str] = mapped_column(unique=True)
#     customerID: Mapped[int] = mapped_column(ForeignKey("customer.id"))
#     customer: Mapped["Customer"] = relationship(back_populates="invoices")
#     gorssAmount: Mapped[float] = mapped_column(nullable=False)
#     netAmount: Mapped[float] = mapped_column(nullable=False)
class Manual(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agency.id"))
    agency: Mapped["Agency"] = relationship(back_populates="manual")
    identifier: Mapped[str] = mapped_column(unique=True)
    source: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[str]
    totalAmount: Mapped[float] = mapped_column(
            init=False,
            nullable=False,
            default_factory=lambda: 0.0
            )
    addedOn: Mapped[datetime] = mapped_column(default_factory=datetime.utcnow)


class BankUser(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    email: Mapped[str] = mapped_column(sa.String(60), unique=True)
    phone: Mapped[str] = mapped_column(sa.String(15), unique=True)
    password: Mapped[str]
    refresh_token: Mapped[Optional[str]] = mapped_column(sa.String(256), init=False)
    webform_id: Mapped[Optional[str]] = mapped_column(sa.String(256), init=False)
    agency_id: Mapped[int] = mapped_column(sa.ForeignKey("agency.id"))
    agency: Mapped["Agency"] = relationship(back_populates="bank_users")
    is_connected: Mapped[bool] = mapped_column(default_factory=lambda: False)
