from sqlalchemy.ext.asyncio import AsyncSession

from .base_repo import BaseRepository
from bot.models.user import User

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
