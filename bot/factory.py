from sqlalchemy.ext.asyncio import AsyncSession


class ServiceFactory:
    """Фабрика для создания сервисов"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._repositories = {}
        self._services = {}
        
