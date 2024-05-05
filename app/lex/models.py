from app.database import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime


class LexAcc(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    key: Mapped[str] = mapped_column(unique=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agency.id"))
    agency: Mapped["Agency"] = relationship(back_populates="lex_acces")
    name: Mapped[str]
    added_on: Mapped[datetime] = mapped_column(default_factory=datetime.utcnow)
