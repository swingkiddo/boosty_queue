from .base import Base
from sqlalchemy import Column, String, BigInteger, DateTime, Integer, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    coach_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    voice_channel_id = Column(BigInteger, nullable=False)
    text_channel_id = Column(BigInteger, nullable=False)
    info_message_id = Column(BigInteger, nullable=False)
    planned_start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    max_slots = Column(Integer, default=8)
    requests = relationship("SessionRequest", back_populates="session")

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
    status = Column(Enum(SessionRequestStatus), nullable=False)
    session = relationship("Session", back_populates="requests")
