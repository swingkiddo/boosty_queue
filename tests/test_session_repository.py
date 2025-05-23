import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import datetime

from bot.models import Session, SessionRequest, SessionRequestStatus, User, Base
from bot.repositories import SessionRepository, UserRepository
from bot.services import SessionService, UserService
from bot.logger import logger

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
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(engine): # Переименовал фикстуру session в db_session, чтобы избежать конфликта имен
    """Фикстура для создания сессии БД для каждого теста."""
    SessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with SessionLocal() as sess:
        yield sess
        await sess.rollback() 

# --- Фикстуры для Пользователей ---
@pytest.fixture
def user_repo(db_session: AsyncSession) -> UserRepository:
    return UserRepository(db_session)

@pytest.fixture
def user_service(user_repo: UserRepository) -> UserService:
    return UserService(user_repo)

# --- Фикстуры для Сессий ---
@pytest.fixture
def session_repo(db_session: AsyncSession) -> SessionRepository:
    """Фикстура для SessionRepository."""
    # Важно: SessionRepository должен получать db_session при инициализации
    # Измените конструктор SessionRepository, чтобы он принимал сессию, как BaseRepository
    return SessionRepository(db_session)


@pytest.fixture
def session_service(session_repo: SessionRepository) -> SessionService:
    """Фикстура для SessionService."""
    return SessionService(session_repo)

# --- Тестовые данные ---
TEST_COACH_ID = 1
TEST_USER_ID_1 = 2
TEST_USER_ID_2 = 3
TEST_VOICE_CHANNEL_ID = 123456789012345678
TEST_TEXT_CHANNEL_ID = 123456789012345679
TEST_INFO_MESSAGE_ID = 123456789012345680

@pytest_asyncio.fixture
async def test_coach(user_service: UserService) -> User:
    current_time = get_current_time()
    return await user_service.create_user(
        user_id=TEST_COACH_ID, nickname="TestCoach",
        join_date=current_time, priority_given_by=0,
        priority_expires_at=current_time + datetime.timedelta(days=30)
    )

@pytest_asyncio.fixture
async def test_user1(user_service: UserService) -> User:
    current_time = get_current_time()
    return await user_service.create_user(
        user_id=TEST_USER_ID_1, nickname="TestUser1",
        join_date=current_time, priority_given_by=0,
        priority_expires_at=current_time + datetime.timedelta(days=30)
    )

@pytest_asyncio.fixture
async def test_user2(user_service: UserService) -> User:
    current_time = get_current_time()
    return await user_service.create_user(
        user_id=TEST_USER_ID_2, nickname="TestUser2",
        join_date=current_time, priority_given_by=0,
        priority_expires_at=current_time + datetime.timedelta(days=30)
    )


# --- Тесты для SessionService ---

@pytest.mark.asyncio
async def test_create_and_get_session(session_service: SessionService, test_coach: User):
    """Тестирует создание и получение сессии."""
    now = get_current_time()
    planned_start = now + datetime.timedelta(hours=1)
    end_time = now + datetime.timedelta(hours=2)

    created_session = await session_service.create_session(
        coach_id=test_coach.id,
        date=now.date(),
        voice_channel_id=TEST_VOICE_CHANNEL_ID,
        text_channel_id=TEST_TEXT_CHANNEL_ID,
        info_message_id=TEST_INFO_MESSAGE_ID,
        planned_start_time=planned_start,
        end_time=end_time,
        max_slots=5
    )

    assert created_session is not None
    assert created_session.coach_id == test_coach.id
    assert created_session.voice_channel_id == TEST_VOICE_CHANNEL_ID
    assert created_session.max_slots == 5

    retrieved_session = await session_service.get_session_by_id(created_session.id)
    assert retrieved_session is not None
    assert retrieved_session.id == created_session.id
    assert retrieved_session.coach_id == test_coach.id

@pytest.mark.asyncio
async def test_get_all_active_sessions(session_service: SessionService, test_coach: User):
    """Тестирует получение всех активных сессий."""
    now = get_current_time()
    
    # Активная сессия
    await session_service.create_session(
        coach_id=test_coach.id, date=now.date(), voice_channel_id=1, text_channel_id=1,
        info_message_id=1, planned_start_time=now - datetime.timedelta(minutes=30),
        end_time=now + datetime.timedelta(hours=1) # Заканчивается через час
    )
    # Завершенная сессия
    await session_service.create_session(
        coach_id=test_coach.id, date=(now - datetime.timedelta(days=1)).date(), voice_channel_id=2, text_channel_id=2,
        info_message_id=2, planned_start_time=now - datetime.timedelta(days=1, hours=2),
        end_time=now - datetime.timedelta(days=1, hours=1) # Закончилась вчера
    )
    # Будущая сессия (тоже должна считаться активной, если end_time > now)
    await session_service.create_session(
        coach_id=test_coach.id, date=(now + datetime.timedelta(days=1)).date(), voice_channel_id=3, text_channel_id=3,
        info_message_id=3, planned_start_time=now + datetime.timedelta(days=1, hours=1),
        end_time=now + datetime.timedelta(days=1, hours=2) # Закончится завтра
    )

    active_sessions = await session_service.get_active_sessions()
    assert len(active_sessions) == 2 # Первая и третья сессии

    active_coach_sessions = await session_service.get_active_sessions_by_coach_id(test_coach.id)
    assert len(active_coach_sessions) == 2

    # Проверим для несуществующего тренера
    active_coach_sessions_none = await session_service.get_active_sessions_by_coach_id(999)
    assert len(active_coach_sessions_none) == 0


@pytest.mark.asyncio
async def test_create_and_manage_session_requests(session_service: SessionService, test_coach: User, test_user1: User, test_user2: User):
    """Тестирует создание запросов на сессию и управление ими."""
    now = get_current_time()
    created_session = await session_service.create_session(
        coach_id=test_coach.id, date=now.date(), voice_channel_id=TEST_VOICE_CHANNEL_ID,
        text_channel_id=TEST_TEXT_CHANNEL_ID, info_message_id=TEST_INFO_MESSAGE_ID,
        planned_start_time=now + datetime.timedelta(hours=1),
        end_time=now + datetime.timedelta(hours=2)
    )

    # 1. Создание запросов
    request1 = await session_service.create_request(session_id=created_session.id, user_id=test_user1.id, status=SessionRequestStatus.PENDING)
    assert request1 is not None
    assert request1.session_id == created_session.id
    assert request1.user_id == test_user1.id
    assert request1.status == SessionRequestStatus.PENDING # Статус по умолчанию

    request2 = await session_service.create_request(session_id=created_session.id, user_id=test_user2.id, status=SessionRequestStatus.PENDING)
    assert request2 is not None

    # 2. Получение запросов
    retrieved_request1 = await session_service.get_request_by_id(request1.id)
    assert retrieved_request1 is not None
    assert retrieved_request1.id == request1.id

    session_requests = await session_service.get_requests_by_session_id(created_session.id)
    assert len(session_requests) == 2
    request_ids = {req.id for req in session_requests}
    assert request1.id in request_ids
    assert request2.id in request_ids

    # 3. Обновление статуса запроса
    updated_request1 = await session_service.update_request_status(request_id=request1.id, status=SessionRequestStatus.ACCEPTED)
    assert updated_request1 is not None
    assert updated_request1.id == request1.id
    assert updated_request1.status == SessionRequestStatus.ACCEPTED

    retrieved_request1_after_update = await session_service.get_request_by_id(request1.id)
    assert retrieved_request1_after_update.status == SessionRequestStatus.ACCEPTED

    # 4. Удаление запроса
    # В SessionService сейчас нет delete_request, но есть в SessionRepository
    # Если нужно протестировать, его нужно добавить в сервис или тестировать репозиторий напрямую
    # Для примера, предположим, что он есть в сервисе:
    # deleted_request = await session_service.delete_request(request2.id)
    # assert deleted_request is not None
    # assert deleted_request.id == request2.id
    
    # # Проверяем, что запрос действительно удален
    # assert await session_service.get_request_by_id(request2.id) is None
    # session_requests_after_delete = await session_service.get_requests_by_session_id(created_session.id)
    # assert len(session_requests_after_delete) == 1
    # assert session_requests_after_delete[0].id == request1.id

@pytest.mark.asyncio
async def test_active_sessions_by_user(session_service: SessionService, test_coach: User, test_user1: User, test_user2: User):
    """Тестирует получение активных сессий, на которые записан пользователь."""
    now = get_current_time()
    session1 = await session_service.create_session(
        coach_id=test_coach.id, date=now.date(), voice_channel_id=1, text_channel_id=1, info_message_id=1,
        planned_start_time=now + datetime.timedelta(hours=1), end_time=now + datetime.timedelta(hours=2)
    )
    session2 = await session_service.create_session( # Другая активная сессия
        coach_id=test_coach.id, date=now.date(), voice_channel_id=2, text_channel_id=2, info_message_id=2,
        planned_start_time=now + datetime.timedelta(hours=3), end_time=now + datetime.timedelta(hours=4)
    )
    session_past = await session_service.create_session( # Прошедшая сессия
        coach_id=test_coach.id, date=now.date(), voice_channel_id=3, text_channel_id=3, info_message_id=3,
        planned_start_time=now - datetime.timedelta(hours=2), end_time=now - datetime.timedelta(hours=1)
    )

    # Пользователь 1 записывается на сессию 1 и на прошедшую сессию
    await session_service.create_request(session_id=session1.id, user_id=test_user1.id, status=SessionRequestStatus.PENDING)
    await session_service.create_request(session_id=session_past.id, user_id=test_user1.id, status=SessionRequestStatus.PENDING)

    # Пользователь 2 записывается на сессию 2
    await session_service.create_request(session_id=session2.id, user_id=test_user2.id, status=SessionRequestStatus.PENDING)
    
    # В SessionService нет прямого метода get_active_sessions_by_user_id,
    # он есть в репозитории. Для теста сервиса нужно либо добавить метод в сервис,
    # либо тестировать комбинацию get_active_sessions и фильтрации запросов.
    # Для примера, если бы такой метод был в сервисе:
    # user1_active_sessions = await session_service.get_active_sessions_by_user_id(test_user1.id)
    # assert len(user1_active_sessions) == 1
    # assert user1_active_sessions[0].id == session1.id

    # user2_active_sessions = await session_service.get_active_sessions_by_user_id(test_user2.id)
    # assert len(user2_active_sessions) == 1
    # assert user2_active_sessions[0].id == session2.id

    # Пока что этот тест будет неполным, так как метод отсутствует в сервисе.
    # Если вы добавите его, раскомментируйте и адаптируйте проверки.
    active_sessions = await session_service.get_active_sessions() # Получаем все активные
    
    user1_joined_active_sessions = []
    for sess in active_sessions:
        requests = await session_service.get_requests_by_session_id(sess.id)
        for req in requests:
            if req.user_id == test_user1.id:
                user1_joined_active_sessions.append(sess)
                break
    
    assert len(user1_joined_active_sessions) == 1
    assert user1_joined_active_sessions[0].id == session1.id
