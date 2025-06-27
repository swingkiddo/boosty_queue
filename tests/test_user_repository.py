import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import datetime

# Предполагается, что ваши модули доступны через 'bot.'
# Если структура вашего проекта другая, эти импорты, возможно, потребуется скорректировать.
from bot.models.base import Base
from bot.models.user import User
from bot.repositories.user_repo import UserRepository
from bot.services.user_service import UserService
from bot.logger import logger
# Предположим, что у вас есть такой utils.py или аналогичный для get_current_time
# Если нет, замените на datetime.datetime.utcnow или datetime.datetime.now(datetime.timezone.utc)
# from bot.utils import get_current_time 

# Заглушка для get_current_time, если он не импортируется
def get_current_time():
    return datetime.datetime.now(datetime.timezone.utc)

# Используем in-memory SQLite для тестов
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def engine():
    """Фикстура для создания и очистки тестовой БД."""
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # Для in-memory SQLite очистка таблиц после не обязательна,
    # но для других БД может потребоваться:
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine):
    """Фикстура для создания сессии БД для каждого теста."""
    SessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with SessionLocal() as sess:
        yield sess
        await sess.rollback() # Откатываем все изменения после теста

@pytest.fixture
def user_repo(session: AsyncSession) -> UserRepository:
    """Фикстура для UserRepository."""
    return UserRepository(session)

@pytest.fixture
def user_service(user_repo: UserRepository) -> UserService:
    """Фикстура для UserService."""
    return UserService(user_repo)

# Данные для тестов
TEST_USER_ID = 12345
TEST_NICKNAME = "test_user"
UPDATED_NICKNAME = "updated_user"

@pytest.mark.asyncio
async def test_create_and_get_user(user_service: UserService):
    """Тестирует создание и получение пользователя."""
    user = await user_service.get_user(TEST_USER_ID)
    assert user is None, "Пользователя не должно существовать изначально"

    current_time = get_current_time()
    # Для модели User поля join_date, priority_given_by, priority_expires_at обязательны (nullable=False)
    # Передаем их через kwargs в create_user
    created_user = await user_service.create_user(
        user_id=TEST_USER_ID,
        nickname=TEST_NICKNAME,
        join_date=current_time,
        priority_given_by=0,  # Пример значения
        priority_expires_at=current_time + datetime.timedelta(days=30) # Пример значения
    )
    logger.info(f"created_user: {created_user}")
    logger.info(f"join_date: {created_user.join_date}")
    logger.info(f"current_time: {current_time}")
    logger.info(f"join_date == current_time: {created_user.join_date == current_time}")
    
    assert created_user is not None, "Пользователь должен быть создан"
    assert created_user.id == TEST_USER_ID
    assert created_user.nickname == TEST_NICKNAME
    assert created_user.join_date.year == current_time.year
    assert created_user.join_date.month == current_time.month
    assert created_user.join_date.day == current_time.day
    assert created_user.priority_given_by == 0
    assert created_user.total_replay_sessions == 0 # Проверка default значения

    retrieved_user = await user_service.get_user(TEST_USER_ID)
    assert retrieved_user is not None, "Созданный пользователь должен быть найден"
    assert retrieved_user.id == TEST_USER_ID
    assert retrieved_user.nickname == TEST_NICKNAME

@pytest.mark.asyncio
async def test_update_user(user_service: UserService):
    """Тестирует обновление полей пользователя."""
    current_time = get_current_time()
    initial_total_replays = 10
    
    await user_service.create_user(
        user_id=TEST_USER_ID,
        nickname=TEST_NICKNAME,
        join_date=current_time,
        priority_given_by=0,
        priority_expires_at=current_time,
        total_replay_sessions=initial_total_replays
    )

    updated_data = {
        "nickname": UPDATED_NICKNAME,
        "total_replay_sessions": 20,
        "priority_coefficient": 1.5
    }
    updated_user = await user_service.update_user(TEST_USER_ID, **updated_data)
    
    assert updated_user is not None, "Пользователь должен быть обновлен"
    assert updated_user.id == TEST_USER_ID
    assert updated_user.nickname == UPDATED_NICKNAME
    assert updated_user.total_replay_sessions == 20
    assert updated_user.priority_coefficient == 1.5

    retrieved_user = await user_service.get_user(TEST_USER_ID)
    assert retrieved_user is not None, "Обновленный пользователь должен быть найден"
    assert retrieved_user.nickname == UPDATED_NICKNAME
    assert retrieved_user.total_replay_sessions == 20
    assert retrieved_user.priority_coefficient == 1.5

@pytest.mark.asyncio
async def test_delete_user(user_service: UserService):
    """Тестирует удаление пользователя."""
    current_time = get_current_time()
    await user_service.create_user(
        user_id=TEST_USER_ID,
        nickname=TEST_NICKNAME,
        join_date=current_time,
        priority_given_by=0,
        priority_expires_at=current_time
    )

    delete_result = await user_service.delete_user(TEST_USER_ID)
    assert delete_result is True, "Удаление существующего пользователя должно вернуть True"

    deleted_user = await user_service.get_user(TEST_USER_ID)
    assert deleted_user is None, "Пользователь должен быть удален"

    delete_non_existent = await user_service.delete_user(99999) # Несуществующий ID
    assert delete_non_existent is False, "Удаление несуществующего пользователя должно вернуть False"

@pytest.mark.asyncio
async def test_get_all_users(user_service: UserService):
    """Тестирует получение всех пользователей."""
    current_time = get_current_time()
    
    all_users_empty = await user_service.get_all_users()
    assert len(all_users_empty) == 0, "Список пользователей должен быть пуст изначально"

    user1_data = {
        "user_id": 1, "nickname": "user1", "join_date": current_time, 
        "priority_given_by": 0, "priority_expires_at": current_time
    }
    user2_data = {
        "user_id": 2, "nickname": "user2", "join_date": current_time,
        "priority_given_by": 0, "priority_expires_at": current_time
    }
    await user_service.create_user(**user1_data)
    await user_service.create_user(**user2_data)

    all_users = await user_service.get_all_users()
    assert len(all_users) == 2, "Должно быть два пользователя в списке"
    
    user_ids = {user.id for user in all_users}
    assert 1 in user_ids
    assert 2 in user_ids

@pytest.mark.asyncio
async def test_complex_scenario_create_update_delete(user_service: UserService):
    """Комплексный сценарий: создание, обновление, удаление нескольких пользователей."""
    current_time = get_current_time()
    user_a_id = 101
    user_b_id = 102
    user_a_initial_nick = "user_A_initial"
    user_b_initial_nick = "user_B_initial"
    user_a_updated_nick = "user_A_updated"

    # 1. Создать пользователя А
    await user_service.create_user(
        user_id=user_a_id, nickname=user_a_initial_nick, join_date=current_time,
        priority_given_by=0, priority_expires_at=current_time
    )
    # 2. Создать пользователя Б
    await user_service.create_user(
        user_id=user_b_id, nickname=user_b_initial_nick, join_date=current_time,
        priority_given_by=0, priority_expires_at=current_time, total_creative_sessions=5
    )

    # 3. Проверить, что оба пользователя созданы
    user_a = await user_service.get_user(user_a_id)
    user_b = await user_service.get_user(user_b_id)
    assert user_a is not None and user_a.nickname == user_a_initial_nick
    assert user_b is not None and user_b.nickname == user_b_initial_nick
    assert user_b.total_creative_sessions == 5

    # 4. Обновить пользователя А (nickname и total_replays_session)
    await user_service.update_user(
        user_a_id,
        nickname=user_a_updated_nick,
        total_replay_sessions=10
    )

    # 5. Проверить, что пользователь А обновлен, а пользователь Б не изменился
    retrieved_user_a = await user_service.get_user(user_a_id)
    retrieved_user_b = await user_service.get_user(user_b_id)

    assert retrieved_user_a.nickname == user_a_updated_nick
    assert retrieved_user_a.total_replay_sessions == 10
    
    assert retrieved_user_b.nickname == user_b_initial_nick # не изменился
    assert retrieved_user_b.total_creative_sessions == 5 # не изменился

    # 6. Удалить пользователя А
    delete_result_a = await user_service.delete_user(user_a_id)
    assert delete_result_a is True

    # 7. Проверить, что пользователь А удален, а пользователь Б остался
    assert await user_service.get_user(user_a_id) is None
    assert await user_service.get_user(user_b_id) is not None

    # 8. Проверить, что get_all_users возвращает только пользователя Б
    all_users = await user_service.get_all_users()
    assert len(all_users) == 1
    assert all_users[0].id == user_b_id
    assert all_users[0].nickname == user_b_initial_nick