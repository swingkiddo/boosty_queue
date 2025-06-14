from sqlalchemy.ext.asyncio import AsyncSession
from discord.ext import commands
from repositories import *
from services import *
from database.db import get_session

class ServiceFactory:
    """Фабрика для создания сервисов"""
    
    def __init__(self):
        self._services = {}
        self._init_services()
        
    def _init_services(self):
        # Discord сервис инициализируется отдельно
        pass

    def init_discord_service(self, bot: commands.Bot):
        self._services['discord'] = DiscordService(bot)
        
    async def get_service(self, service_name: str):
        if service_name == 'discord':
            return self._services['discord']
        
        # Для каждого запроса создаем новую сессию БД
        session = await get_session()
        
        if service_name == 'user':
            user_repo = UserRepository(session)
            return UserService(user_repo)
        elif service_name == 'session':
            session_repo = SessionRepository(session)
            return SessionService(session_repo)
        
        raise ValueError(f"Service {service_name} not found")

    async def get_services(self):
        return (
            await self.get_service("user"), 
            await self.get_service("session"), 
            await self.get_service("discord")
        )
