from bot.repositories.session_repo import SessionRepository
from bot.models.session import Session, SessionRequest, SessionRequestStatus
from datetime import datetime
from typing import List, Optional

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
        return await self.session_repo.get_session_by_id(session_id)
    
    async def create_session(self, coach_id: int, **kwargs) -> Session:
        return await self.session_repo.create_session(coach_id, **kwargs)
    
    async def get_request_by_id(self, request_id: int) -> Optional[SessionRequest]:
        return await self.session_repo.get_request_by_id(request_id)
    
    async def get_requests_by_session_id(self, session_id: int) -> List[SessionRequest]:
        return await self.session_repo.get_requests_by_session_id(session_id)
    
    async def create_request(self, session_id: int, user_id: int, status: SessionRequestStatus) -> SessionRequest:
        return await self.session_repo.create_request(session_id, user_id, status)
    
    async def update_request_status(self, request_id: int, status: SessionRequestStatus) -> SessionRequest:
        return await self.session_repo.update_request_status(request_id, status)
    
    async def delete_request(self, request_id: int) -> SessionRequest:
        return await self.session_repo.delete_request(request_id)
