from app.database import db
from app.auth.errors import UserAlreadyExist
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash


class Agency(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]

    @staticmethod
    def create_agency(email, password):
        existingUser = db.session.execute(
                db.select(Agency).filter_by(email=email)
                ).scalar_one_or_none()
        if existingUser:
            raise UserAlreadyExist("User with this email already exist", "danger")
        hdPassword = Agency.genrate_password(password)
        newUser = Agency(email=email, password=hdPassword)
        db.session.add(newUser)

    @staticmethod
    def genrate_password(password):
        return generate_password_hash(password)

    @staticmethod
    def check_password(hd_password, password):
        return check_password_hash(hd_password, password)
