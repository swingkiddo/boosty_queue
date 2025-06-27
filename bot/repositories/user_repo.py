from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from .base_repo import BaseRepository
from models.user import User
from models.session import SessionRequest

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_users_by_ids(self, user_ids: List[int]) -> List[User]:
        query = select(User).options(
            selectinload(User.session_requests).selectinload(SessionRequest.session)
        ).where(User.id.in_(user_ids))
        result = await self.session.execute(query)
        return result.scalars().all()
