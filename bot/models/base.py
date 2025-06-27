from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime
from utils.utils import get_current_time

class Base(DeclarativeBase):
    __abstract__ = True

    created_at = Column(DateTime, default=get_current_time)
    updated_at = Column(DateTime, default=get_current_time, onupdate=get_current_time)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}