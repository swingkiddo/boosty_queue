from repositories.user_repo import UserRepository
from models.user import User
from typing import List
class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def get_user(self, user_id: int) -> User:
        return await self.user_repo.get_by_id(user_id)
    
    async def create_user(self, user_id: int, nickname: str, **kwargs) -> User:
        return await self.user_repo.create(id=user_id, nickname=nickname, **kwargs)
    
    async def update_user(self, user_id: int, **kwargs) -> User:
        return await self.user_repo.update(user_id, **kwargs)
    
    async def delete_user(self, user_id: int) -> bool:
        return await self.user_repo.delete(user_id)
    
    async def get_all_users(self) -> list[User]:
        return await self.user_repo.get_all()

    async def get_users_by_ids(self, user_ids: List[int]) -> List[User]:
        return await self.user_repo.get_users_by_ids(user_ids)
