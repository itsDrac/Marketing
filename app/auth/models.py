from app.extensions import db
from sqlalchemy.orm import Mapped, mapped_column


class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
