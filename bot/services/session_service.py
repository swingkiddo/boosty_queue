from repositories.session_repo import SessionRepository
from models.session import Session, SessionRequest, SessionRequestStatus, SessionReview, UserSessionActivity
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from logger import logger
import pandas as pd
from io import BytesIO

class SessionService:
    def __init__(self, session_repo: SessionRepository):
        self.session_repo = session_repo

    async def get_all_sessions(self) -> List[Session]:
        return await self.session_repo.get_all_sessions()
    
    async def get_active_sessions(self) -> List[Session]:
        return await self.session_repo.get_active_sessions()
    
    async def get_active_sessions_by_coach_id(self, coach_id: int) -> List[Session]:
        return await self.session_repo.get_active_sessions_by_coach_id(coach_id)
    
    async def get_active_sessions_by_user_id(self, user_id: int) -> List[Session]:
        return await self.session_repo.get_active_sessions_by_user_id(user_id)
    
    async def get_session_by_id(self, session_id: int) -> Optional[Session]:
        return await self.session_repo.get_by_id(session_id)

    async def get_active_sessions_by_coach_id(self, coach_id: int) -> List[Session]:
        return await self.session_repo.get_active_sessions_by_coach_id(coach_id)

    async def get_last_created_session_by_coach_id(self, coach_id: int) -> Optional[Session]:
        return await self.session_repo.get_last_created_session_by_coach_id(coach_id)
    
    async def create_session(self, coach_id: int, **kwargs) -> Session:
        return await self.session_repo.create(coach_id=coach_id, **kwargs)

    async def update_session(self, session_id: int, **kwargs) -> Session:
        return await self.session_repo.update(session_id, **kwargs)

    async def delete_session(self, session_id: int) -> Session:
        return await self.session_repo.delete(session_id)
    
    async def get_request_by_id(self, request_id: int) -> Optional[SessionRequest]:
        return await self.session_repo.get_request_by_id(request_id)

    async def get_request_by_user_id(self, session_id: int, user_id: int) -> Optional[SessionRequest]:
        return await self.session_repo.get_request_by_user_id(session_id, user_id)

    async def get_accepted_requests_by_session_id(self, session_id: int) -> List[SessionRequest]:
        requests = await self.get_requests_by_session_id(session_id)
        return [request for request in requests if request.status == SessionRequestStatus.ACCEPTED.value]
    
    async def get_requests_by_session_id(self, session_id: int) -> List[SessionRequest]:
        return await self.session_repo.get_requests_by_session_id(session_id)
    
    async def create_request(self, session_id: int, user_id: int) -> SessionRequest:
        return await self.session_repo.create_request(session_id, user_id, SessionRequestStatus.PENDING.value)
    
    async def update_request_status(self, request_id: int, status: SessionRequestStatus) -> SessionRequest:
        return await self.session_repo.update_request_status(request_id, status.value)
    
    async def delete_request(self, request_id: int) -> SessionRequest:
        return await self.session_repo.delete_request(request_id)

    async def create_review(self, session_id: int, user_id: int, rating: int) -> SessionReview:
        return await self.session_repo.create_review(session_id, user_id, rating=rating)
    
    async def get_reviews_by_session_id(self, session_id: int) -> List[SessionReview]:
        return await self.session_repo.get_reviews_by_session_id(session_id)

    async def get_reviews_by_user_id(self, user_id: int) -> List[SessionReview]:
        return await self.session_repo.get_reviews_by_user_id(user_id)
    
    async def get_review_by_id(self, review_id: int) -> Optional[SessionReview]:
        return await self.session_repo.get_review_by_id(review_id)
    
    async def update_review(self, review_id: int, **kwargs) -> SessionReview:
        return await self.session_repo.update_review(review_id, **kwargs)
    
    async def delete_review(self, review_id: int) -> bool:
        return await self.session_repo.delete_review(review_id)

    async def get_session_data(self, session_id: int) -> Optional[Dict[str, Any]]:
        session = await self.get_session_by_id(session_id)
        if not session:
            return None
        requests = await self.get_requests_by_session_id(session_id)
        reviews = await self.get_reviews_by_session_id(session_id)
        activities = await self.get_session_activities(session_id)
        return {
            "session": session,
            "requests": requests,
            "reviews": reviews,
            "activities": activities
        }

    async def create_user_session_activity(self, session_id: int, user_id: int, **kwargs) -> UserSessionActivity:
        return await self.session_repo.create_user_session_activity(session_id, user_id, **kwargs)

    async def get_user_session_activity_by_id(self, activity_id: int) -> Optional[UserSessionActivity]:
        return await self.session_repo.get_user_session_activity_by_id(activity_id)
    
    async def update_user_session_activity(self, activity_id: int, **kwargs) -> UserSessionActivity:
        return await self.session_repo.update_user_session_activity(activity_id, **kwargs)

    async def get_user_session_activities(self, session_id: int, user_id: int) -> List[UserSessionActivity]:
        return await self.session_repo.get_user_session_activities(session_id, user_id)

    async def get_session_activities(self, session_id: int) -> List[UserSessionActivity]:
        return await self.session_repo.get_session_activities(session_id)

    async def calculate_user_activity(self, session_id: int, user_id: int) -> float:
        activities = await self.get_user_session_activities(session_id, user_id)
        if not activities:
            return 0
        return sum(activity.duration for activity in activities)
