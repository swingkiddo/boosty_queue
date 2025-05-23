from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime
from bot.utils import get_current_time

class Base(DeclarativeBase):
    __abstract__ = True

    created_at = Column(DateTime, default=get_current_time)
    updated_at = Column(DateTime, default=get_current_time, onupdate=get_current_time)

