from .base import Base
from sqlalchemy import Column, String, BigInteger, DateTime, Integer, Float
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    nickname = Column(String, nullable=False)
    join_date = Column(DateTime, nullable=False)
    coach_tier = Column(String, nullable=True)
    total_replay_sessions = Column(Integer, default=0)
    total_creative_sessions = Column(Integer, default=0)
    priority_coefficient = Column(Float, default=0)
    priority_given_by = Column(BigInteger, nullable=True)
    priority_expires_at = Column(DateTime, nullable=True)
    session_requests = relationship("SessionRequest", back_populates="user")