from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base

from typing import List

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    user_name: Mapped[str] = mapped_column(String(50))

    # 1:M (1 user -> M exercises)
    exercises: Mapped[List["Exercise"]] = relationship(back_populates="user")


class BodyPart(Base):
    __tablename__ = 'body_part'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    exercises: Mapped[List["Exercise"]] = relationship(back_populates="body_part")


class Exercise(Base):
    __tablename__ = 'exercise'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    bp_id: Mapped[int] = mapped_column(ForeignKey("body_part.id"))
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # M:1 (M exercises -> 1 user)
    user: Mapped["User"] = relationship(back_populates="exercises")
    # M:1 (M exercises -> 1 body part)
    body_part: Mapped["BodyPart"] = relationship(back_populates="exercises")


class History(Base):
    __tablename__ = 'history'

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[int] = mapped_column(ForeignKey("user.id"))
    bp_id: Mapped[int] = mapped_column(ForeignKey("body_part.id"))
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # M:1 (M exercises -> 1 user)
    user: Mapped["User"] = relationship(back_populates="exercises")
    # M:1 (M exercises -> 1 body part)
    body_part: Mapped["BodyPart"] = relationship(back_populates="exercises")


