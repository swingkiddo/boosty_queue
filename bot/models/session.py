from .base import Base
from sqlalchemy import Column, String, BigInteger, DateTime, Integer, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
import enum

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    coach_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    voice_channel_id = Column(BigInteger, nullable=True)
    text_channel_id = Column(BigInteger, nullable=True)
    info_message_id = Column(BigInteger, nullable=True)
    session_message_id = Column(BigInteger, nullable=True)
    start_time = Column(DateTime, nullable=True, )
    end_time = Column(DateTime, nullable=True)
    max_slots = Column(Integer, default=8)
    requests = relationship("SessionRequest", back_populates="session")
    is_active = Column(Boolean, default=False)

class SessionRequestStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SKIPPED = "skipped"

class SessionRequest(Base):
    __tablename__ = "session_requests"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False)
    session = relationship("Session", back_populates="requests")
    user = relationship("User", back_populates="session_requests")

class SessionReview(Base):
    __tablename__ = "session_reviews"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)

class UserSessionActivity(Base):
    __tablename__ = "user_session_activity"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    join_time = Column(DateTime, nullable=False)
    leave_time = Column(DateTime, nullable=True) # Может быть NULL, если пользователь еще в канале
