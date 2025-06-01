from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import config
from models.base import Base
from models.user import User
from datetime import datetime, timedelta
from sqlalchemy import select, insert
engine = create_async_engine(config.DATABASE_URL, echo=True)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        test_user = [
            {
                "id": 427785500066054147,
                "nickname": "trycart1getbanned",
                "join_date": datetime.now(),
                "total_replay_sessions": 3,
                "total_creative_sessions": 9,
                "priority_coefficient": 0,
                "priority_given_by": None,
                "priority_expires_at": None,
            },
            {
                "id": 503267257414057985,
                "nickname": "cosm1c_ivan",
                "join_date": datetime.now(),
                "total_replay_sessions": 9,
                "total_creative_sessions": 3,
                "priority_coefficient": 1,
                "priority_given_by": None,
                "priority_expires_at": datetime.now() + timedelta(days=30),
            },
            {
                "id": 550326654380277761,
                "nickname": "achrommm",
                "join_date": datetime.now(),
                "total_replay_sessions": 5,
                "total_creative_sessions": 5,
                "priority_coefficient": 0,
                "priority_given_by": None,
                "priority_expires_at": None,
            },
            {
                "id": 613678861686931467,
                "nickname": "turistxxl",
                "join_date": datetime.now(),
                "total_replay_sessions": 1,
                "total_creative_sessions": 1,
                "priority_coefficient": 0,
                "priority_given_by": None,
                "priority_expires_at": None,
            },
        ]
        users = await conn.execute(select(User))
        user_ids = [user.id for user in users]
        for user in test_user:
            if user["id"] not in user_ids:
                await conn.execute(insert(User).values(user))
        

async def get_session() -> AsyncSession:
    return async_session()

