from sqlalchemy.ext.asyncio import AsyncSession
from discord.ext import commands
from repositories import *
from services import *

class ServiceFactory:
    """Фабрика для создания сервисов"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._repositories = {}
        self._services = {}
        
        self._init_repositories()
        self._init_services()
        
    def _init_repositories(self):
        self._repositories['user'] = UserRepository(self.session)
        self._repositories['session'] = SessionRepository(self.session)
        
    def _init_services(self):
        self._services['user'] = UserService(self._repositories['user'])
        self._services['session'] = SessionService(self._repositories['session'])

    def init_discord_service(self, bot: commands.Bot):
        self._services['discord'] = DiscordService(bot)
        
    def get_service(self, service_name: str):
        service = self._services.get(service_name)
        if not service:
            raise ValueError(f"Service {service_name} not found")
        return service

    def get_services(self):
        return self.get_service("user"), self.get_service("session"), self.get_service("discord")
