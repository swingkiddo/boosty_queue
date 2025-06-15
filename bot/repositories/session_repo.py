from repositories.base_repo import BaseRepository
from models.session import (
    Session,
    SessionRequest,
    SessionRequestStatus,
    SessionReview,
    UserSessionActivity,
)
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from logger import logger


class SessionRepository(BaseRepository[Session]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Session)
    
    async def get_by_id(self, session_id: int) -> Optional[Session]:
        query = select(Session).options(
            selectinload(Session.requests),
            selectinload(Session.reviews),
            selectinload(Session.activities),
            selectinload(Session.coach),
        ).where(Session.id == session_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all_sessions(self) -> List[Session]:
        query = select(Session).options(
            selectinload(Session.requests),
            selectinload(Session.reviews),
            selectinload(Session.activities),
            selectinload(Session.coach),
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_sessions(self) -> List[Session]:
        query = (
            select(Session)
            .options(
                selectinload(Session.requests),
                selectinload(Session.reviews),
                selectinload(Session.activities),
                selectinload(Session.coach),
            )
            .where(Session.is_active == True)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_sessions_by_coach_id(self, coach_id: int) -> List[Session]:
        query = (
            select(Session)
            .options(
                selectinload(Session.requests),
                selectinload(Session.reviews),
                selectinload(Session.activities),
                selectinload(Session.coach),
            )
            .where(Session.coach_id == coach_id, Session.is_active == True)
            .order_by(Session.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_sessions_by_user_id(self, user_id: int) -> List[Session]:
        query = (
            select(Session)
            .options(
                selectinload(Session.requests),
                selectinload(Session.reviews),
                selectinload(Session.activities),
                selectinload(Session.coach),
            )
            .where(Session.is_active == True, Session.coach_id == user_id)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_last_created_session_by_coach_id(
        self, coach_id: int
    ) -> Optional[Session]:
        query = (
            select(Session)
            .options(
                selectinload(Session.requests),
                selectinload(Session.reviews),
                selectinload(Session.activities),
                selectinload(Session.coach),
            )
            .where(Session.coach_id == coach_id)
            .order_by(Session.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_request_by_id(self, request_id: int) -> Optional[SessionRequest]:
        query = (
            select(SessionRequest)
            .options(
                selectinload(SessionRequest.session),
                selectinload(SessionRequest.user),
            )
            .where(SessionRequest.id == request_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_requests_by_session_id(self, session_id: int) -> List[SessionRequest]:
        query = (
            select(SessionRequest)
            .options(
                selectinload(SessionRequest.session),
                selectinload(SessionRequest.user),
            )
            .where(SessionRequest.session_id == session_id)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_accepted_requests(self, session_id: int) -> List[SessionRequest]:
        query = (
            select(SessionRequest)
            .where(SessionRequest.session_id == session_id, SessionRequest.status == SessionRequestStatus.ACCEPTED.value)
            .order_by(SessionRequest.slot_number)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_requests_by_user_id(self, user_id: int) -> List[SessionRequest]:
        query = (
            select(SessionRequest)
            .options(
                selectinload(SessionRequest.session),
                selectinload(SessionRequest.user),
            )
            .where(SessionRequest.user_id == user_id)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_sessions_count(self, user_id: int, session_type: str) -> int:
        query = (
            select(SessionRequest)
            .join(Session)
            .where(
                SessionRequest.user_id == user_id,
                Session.type == session_type,
                SessionRequest.status == SessionRequestStatus.ACCEPTED.value,
            )
        )
        result = await self.session.execute(query)
        return len(result.scalars().all())

    async def get_request_by_user_id(
        self, session_id: int, user_id: int
    ) -> Optional[SessionRequest]:
        query = (
            select(SessionRequest)
            .options(
                selectinload(SessionRequest.session),
                selectinload(SessionRequest.user),
            )
            .where(
                SessionRequest.session_id == session_id,
                SessionRequest.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_request(
        self, session_id: int, user_id: int, status: SessionRequestStatus
    ) -> SessionRequest:
        request = SessionRequest(session_id=session_id, user_id=user_id, status=status)
        self.session.add(request)
        await self.session.commit()
        return request

    async def update_request(
        self, request_id: int, **kwargs
    ) -> SessionRequest:
        query = (
            update(SessionRequest)
            .where(SessionRequest.id == request_id)
            .values(**kwargs)
            .returning(SessionRequest)
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def update_request_status(
        self, request_id: int, status: SessionRequestStatus
    ) -> SessionRequest:
        query = (
            select(SessionRequest)
            .options(
                selectinload(SessionRequest.session),
                selectinload(SessionRequest.user),
            )
            .where(SessionRequest.id == request_id)
        )
        result = await self.session.execute(query)
        request = result.scalar_one_or_none()
        if request:
            request.status = status
            await self.session.commit()
        return request

    async def delete_request(self, request_id: int) -> bool:
        query = (
            select(SessionRequest)
            .options(selectinload(SessionRequest.session))
            .where(SessionRequest.id == request_id)
        )
        result = await self.session.execute(query)
        request = result.scalar_one_or_none()
        if request:
            await self.session.delete(request)
            await self.session.commit()
            return True
        return False

    async def create_review(
        self, session_id: int, user_id: int, **kwargs
    ) -> SessionReview:
        review = SessionReview(session_id=session_id, user_id=user_id, **kwargs)
        self.session.add(review)
        await self.session.commit()
        return review

    async def get_reviews_by_session_id(self, session_id: int) -> List[SessionReview]:
        logger.info(f"Getting reviews for session {session_id}")
        query = (
            select(SessionReview)
            .options(selectinload(SessionReview.session))
            .where(SessionReview.session_id == session_id)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_review_by_id(self, review_id: int) -> Optional[SessionReview]:
        query = (
            select(SessionReview)
            .options(selectinload(SessionReview.session))
            .where(SessionReview.id == review_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_reviews_by_user_id(self, user_id: int) -> List[SessionReview]:
        query = (
            select(SessionReview)
            .options(selectinload(SessionReview.session))
            .where(SessionReview.user_id == user_id)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_review(self, review_id: int, **kwargs) -> SessionReview:
        query = (
            update(SessionReview)
            .where(SessionReview.id == review_id)
            .values(**kwargs)
            .returning(SessionReview)
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete_review(self, review_id: int) -> bool:
        query = delete(SessionReview).where(SessionReview.id == review_id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0

    async def create_user_session_activity(
        self, session_id: int, user_id: int, **kwargs
    ) -> UserSessionActivity:
        activity = UserSessionActivity(session_id=session_id, user_id=user_id, **kwargs)
        self.session.add(activity)
        await self.session.commit()
        return activity

    async def get_user_session_activity_by_id(
        self, activity_id: int
    ) -> Optional[UserSessionActivity]:
        query = (
            select(UserSessionActivity)
            .options(
                selectinload(UserSessionActivity.session),
                selectinload(UserSessionActivity.user),
            )
            .where(UserSessionActivity.id == activity_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_session_activities(
        self, session_id: int, user_id: int
    ) -> List[UserSessionActivity]:
        query = (
            select(UserSessionActivity)
            .options(
                selectinload(UserSessionActivity.session),
                selectinload(UserSessionActivity.user),
            )
            .where(
                UserSessionActivity.session_id == session_id,
                UserSessionActivity.user_id == user_id,
            )
            .order_by(UserSessionActivity.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_user_session_activity(
        self, activity_id: int, **kwargs
    ) -> UserSessionActivity:
        query = (
            update(UserSessionActivity)
            .where(UserSessionActivity.id == activity_id)
            .values(**kwargs)
            .returning(UserSessionActivity)
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def get_session_activities(
        self, session_id: int
    ) -> List[UserSessionActivity]:
        query = (
            select(UserSessionActivity)
            .options(
                selectinload(UserSessionActivity.session),
                selectinload(UserSessionActivity.user),
            )
            .where(UserSessionActivity.session_id == session_id)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
