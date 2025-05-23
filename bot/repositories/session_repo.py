from bot.repositories.base_repo import BaseRepository
from bot.models.session import Session, SessionRequest, SessionRequestStatus
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
class SessionRepository(BaseRepository[Session]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Session)

    async def get_all_sessions(self) -> List[Session]:
        query = select(Session).options(selectinload(Session.requests))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_sessions(self) -> List[Session]:
        query = select(Session).where(Session.end_time > datetime.now())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_sessions_by_coach_id(self, coach_id: int) -> List[Session]:
        query = select(Session).where(Session.coach_id == coach_id, Session.end_time > datetime.now())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_sessions_by_user_id(self, user_id: int) -> List[Session]:
        query = select(Session).where(Session.user_id == user_id, Session.end_time > datetime.now())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_session_by_id(self, session_id: int) -> Optional[Session]:
        query = select(Session).where(Session.id == session_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_session(self, coach_id: int, **kwargs) -> Session:
        session = Session(coach_id=coach_id, **kwargs)
        self.session.add(session)
        await self.session.commit()
        return session

    async def get_request_by_id(self, request_id: int) -> Optional[SessionRequest]:
        query = select(SessionRequest).where(SessionRequest.id == request_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_requests_by_session_id(self, session_id: int) -> List[SessionRequest]:
        query = select(SessionRequest).where(SessionRequest.session_id == session_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_request(self, session_id: int, user_id: int, status: SessionRequestStatus) -> SessionRequest:
        request = SessionRequest(session_id=session_id, user_id=user_id, status=status)
        self.session.add(request)
        await self.session.commit()
        return request

    async def update_request_status(self, request_id: int, status: SessionRequestStatus) -> SessionRequest:
        query = select(SessionRequest).where(SessionRequest.id == request_id)
        result = await self.session.execute(query)
        request = result.scalar_one_or_none()
        if request:
            request.status = status
            await self.session.commit()
        return request

    async def delete_request(self, request_id: int) -> bool:
        query = select(SessionRequest).where(SessionRequest.id == request_id)
        result = await self.session.execute(query)
        request = result.scalar_one_or_none()
        if request:
            await self.session.delete(request)
            await self.session.commit()
            return True
        return False
    