from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from .base_repo import BaseRepository
from models.user import User

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_users_by_ids(self, user_ids: List[int]) -> List[User]:
        query = select(User).where(User.id.in_(user_ids))
        result = await self.session.execute(query)
        return result.scalars().all()
