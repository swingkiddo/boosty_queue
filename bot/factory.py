from sqlalchemy.ext.asyncio import AsyncSession
from discord.ext import commands
from repositories import *
from services import *
from database.db import get_db_session
from contextlib import asynccontextmanager
from logger import logger

class ServiceFactory:
    """Фабрика для создания сервисов"""

    def __init__(self):
        self._services = {}
        self._session = None
        self._session_context = None

    def init_discord_service(self, bot: commands.Bot):
        self._services['discord'] = DiscordService(bot)

    async def _ensure_session(self):
        """Обеспечивает наличие активной сессии БД"""
        if self._session is None:
            self._session_context = get_db_session()
            self._session = await self._session_context.__aenter__()

    async def get_service(self, service_name: str):
        if service_name == 'discord':
            return self._services['discord']

        await self._ensure_session()

        if service_name == 'user':
            if 'user' not in self._services:
                user_repo = UserRepository(self._session)
                self._services['user'] = UserService(user_repo)
            return self._services['user']
        elif service_name == 'session':
            if 'session' not in self._services:
                session_repo = SessionRepository(self._session)
                self._services['session'] = SessionService(session_repo)
            return self._services['session']

        raise ValueError(f"Service {service_name} not found")

    async def close(self):
        """Закрывает сессию БД"""
        if self._session_context and self._session:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing session: {e}")
            finally:
                self._session = None
                self._session_context = None
                # Очищаем кэш сервисов, которые зависят от БД
                for key in list(self._services.keys()):
                    if key != 'discord':
                        del self._services[key]

@asynccontextmanager
async def get_service_factory(existing_factory: ServiceFactory = None):
    """Контекстный менеджер для безопасной работы с ServiceFactory"""
    if existing_factory:
        # Используем существующую фабрику, но создаем новую сессию
        factory = ServiceFactory()
        factory._services['discord'] = existing_factory._services.get('discord')
    else:
        factory = ServiceFactory()

    try:
        yield factory
    finally:
        await factory.close()
