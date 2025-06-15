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
    is_active = Column(Boolean, default=False)
    coach = relationship("User", back_populates="sessions")
    requests = relationship("SessionRequest", back_populates="session")
    reviews = relationship("SessionReview", back_populates="session")
    activities = relationship("UserSessionActivity", back_populates="session")

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
    slot_number = Column(Integer, nullable=True)

class SessionReview(Base):
    __tablename__ = "session_reviews"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    session = relationship("Session", back_populates="reviews")

class UserSessionActivity(Base):
    __tablename__ = "user_session_activity"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    join_time = Column(DateTime, nullable=False)
    leave_time = Column(DateTime, nullable=True) # Может быть NULL, если пользователь еще в канале
    user = relationship("User", back_populates="session_activities")
    session = relationship("Session", back_populates="activities")

    @property
    def duration(self) -> float:
        result = 0
        if self.leave_time:
            result = (self.leave_time - self.join_time).total_seconds()

        logger.info(f"Duration: {result}")
        return result

    def calculate_duration(self) -> float:
        if self.leave_time:
            return (self.leave_time - self.join_time).total_seconds()
        return 0
