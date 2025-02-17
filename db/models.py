from datetime import datetime
from typing import List

from sqlalchemy import String, ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import UniqueConstraint


class Base(AsyncAttrs, DeclarativeBase):
    pass


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
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # M:1 (M exercises -> 1 user)
    user: Mapped["User"] = relationship(back_populates="exercises")
    # M:1 (M exercises -> 1 body part)
    body_part: Mapped["BodyPart"] = relationship(back_populates="exercises")

    __table_args__ = (
        UniqueConstraint('name', 'bp_id', name='uq_exercise_name_bp_id'),
    )


class History(Base):
    __tablename__ = 'history'

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    bp_id: Mapped[int] = mapped_column(ForeignKey("body_part.id"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercise.id"))
    note: Mapped[str] = mapped_column(String(50))

    exercise: Mapped["Exercise"] = relationship(foreign_keys=[exercise_id])
    body_part: Mapped["BodyPart"] = relationship(foreign_keys=[bp_id])
