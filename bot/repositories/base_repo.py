from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import TypeVar, Generic, Type, List, Optional

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Базовый репозиторий для работы с моделями"""
    
    def __init__(self, session: AsyncSession, model_cls: Type[T]):
        """
        Инициализация репозитория
        
        Args:
            session: Асинхронная сессия SQLAlchemy
            model_cls: Класс модели
        """
        self.session = session
        self.model_cls = model_cls
    
    async def get_by_id(self, id: int) -> Optional[T]:
        """
        Получение объекта по ID
        
        Args:
            id: Идентификатор объекта
            
        Returns:
            Объект модели или None
        """
        query = select(self.model_cls).where(self.model_cls.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[T]:
        """
        Получение всех объектов
        
        Returns:
            Список объектов модели
        """
        query = select(self.model_cls)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_filtered(self, **filters) -> List[T]:
        """
        Получение объектов с фильтрацией
        
        Args:
            **filters: Условия фильтрации в формате имя_поля=значение
            
        Returns:
            Список отфильтрованных объектов
        """
        query = select(self.model_cls)
        for field, value in filters.items():
            if hasattr(self.model_cls, field):
                query = query.where(getattr(self.model_cls, field) == value)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create(self, **kwargs) -> T:
        """
        Создание нового объекта
        
        Args:
            **kwargs: Атрибуты создаваемого объекта
            
        Returns:
            Созданный объект
        """
        obj = self.model_cls(**kwargs)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj
    
    async def update(self, id: int, **kwargs) -> Optional[T]:
        """
        Обновление объекта по ID
        
        Args:
            id: Идентификатор объекта
            **kwargs: Атрибуты для обновления
            
        Returns:
            Обновленный объект или None, если объект не найден
        """
        query = update(self.model_cls).where(self.model_cls.id == id).values(**kwargs).returning(self.model_cls)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.scalar_one_or_none()
    
    async def delete(self, id: int) -> bool:
        """
        Удаление объекта по ID
        
        Args:
            id: Идентификатор объекта
            
        Returns:
            True если объект был удален, иначе False
        """
        query = delete(self.model_cls).where(self.model_cls.id == id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    async def count(self, **filters) -> int:
        """
        Подсчет количества объектов, опционально с фильтрами
        
        Args:
            **filters: Условия фильтрации в формате имя_поля=значение
            
        Returns:
            Количество объектов
        """
        from sqlalchemy import func
        query = select(func.count()).select_from(self.model_cls)
        
        for field, value in filters.items():
            if hasattr(self.model_cls, field):
                query = query.where(getattr(self.model_cls, field) == value)
        
        result = await self.session.execute(query)
        return result.scalar_one()
