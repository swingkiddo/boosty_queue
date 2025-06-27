import pytest
import datetime

from bot.models import Session, User
from bot.helpers import ScoreCalculator

@pytest.mark.asyncio
async def test_score_calculator():
    """Тест для проверки расчета очков."""
    calculator = ScoreCalculator()
    now = datetime.datetime.utcnow() # Используем UTCNow, как в ScoreCalculator
    yesterday = now - datetime.timedelta(days=1)
    tomorrow = now + datetime.timedelta(days=1)

    users_data = []
    # Группа 1: Новые пользователи (без приоритета)
    for i in range(7):
        sessions = [(0,0), (1,0), (0,1), (1,1), (2,1), (1,2), (2,2)][i]
        users_data.append({
            "id": i + 1, "nickname": f"NewUser{i+1}",
            "total_replay_sessions": sessions[0], "total_creative_sessions": sessions[1],
            "priority_coefficient": 0.0, "priority_expires_at": None
        })

    # Группа 2: Обычные пользователи (без приоритета)
    for i in range(7):
        sessions = [(5,5), (6,7), (8,6), (10,9), (7,5), (9,10), (5,8)][i]
        users_data.append({
            "id": i + 8, "nickname": f"RegularUser{i+1}",
            "total_replay_sessions": sessions[0], "total_creative_sessions": sessions[1],
            "priority_coefficient": 0.0, "priority_expires_at": None
        })

    # Группа 3: Активные пользователи (без приоритета)
    for i in range(6):
        sessions = [(20,20), (25,22), (22,25), (30,28), (28,30), (20,30)][i]
        users_data.append({
            "id": i + 15, "nickname": f"ActiveUser{i+1}",
            "total_replay_sessions": sessions[0], "total_creative_sessions": sessions[1],
            "priority_coefficient": 0.0, "priority_expires_at": None
        })

    # Группа 4: Пользователи с активным высоким приоритетом (3.0, было 1.0)
    for i in range(7):
        sessions = [(0,1), (2,0), (5,5), (1,3), (3,1), (0,0), (4,4)][i]
        users_data.append({
            "id": i + 21, "nickname": f"HighPrioUser{i+1}",
            "total_replay_sessions": sessions[0], "total_creative_sessions": sessions[1],
            "priority_coefficient": 3.0, "priority_expires_at": tomorrow # Изменено с 1.0 на 3.0
        })
    
    # Группа 5: Пользователи с истекшим высоким приоритетом (3.0, было 1.0)
    for i in range(7):
        sessions = [(0,1), (2,0), (5,5), (1,3), (3,1), (0,0), (4,4)][i] # Такие же сессии как у группы 4 для сравнения
        users_data.append({
            "id": i + 28, "nickname": f"ExpiredPrioUser{i+1}",
            "total_replay_sessions": sessions[0], "total_creative_sessions": sessions[1],
            "priority_coefficient": 3.0, "priority_expires_at": yesterday # Изменено с 1.0 на 3.0
        })

    # Группа 6: Пользователи с активным средним приоритетом (1.5, было 0.5, без даты истечения)
    for i in range(6):
        sessions = [(0,1), (2,0), (5,5), (1,3), (3,1), (0,0)][i]
        users_data.append({
            "id": i + 35, "nickname": f"MidPrioUser{i+1}",
            "total_replay_sessions": sessions[0], "total_creative_sessions": sessions[1],
            "priority_coefficient": 1.5, "priority_expires_at": None # Изменено с 0.5 на 1.5
        })

    test_users = [
        User(**ud) for ud in users_data
    ]

    # --- Тест для Replay сессии ---
    scored_users_replay = []
    for user in test_users:
        score = calculator.calculate_score(user, ScoreCalculator.SESSION_TYPE_REPLAY)
        scored_users_replay.append({"user": user, "score": score})
    
    # Сортируем по убыванию очков, затем по возрастанию replay_sessions (для стабильности при равных очках), затем по id
    sorted_users_replay = sorted(
        scored_users_replay,
        key=lambda x: (x["score"], -x["user"].total_replay_sessions, x["user"].id), # -session_count для обратного порядка
        reverse=True
    )
    
    # Ожидаемые ID групп в порядке приоритета для Replay
    # Группа 4 (HighPrio, ID 21-27)
    # Группа 6 (MidPrio, ID 35-40)
    # Группы 1, 2, 3, 5 (без активного приоритета или с истекшим)

    # Проверяем, что пользователи из группы 4 наверху и отсортированы по total_replay_sessions
    top_7_replay_ids = [u["user"].id for u in sorted_users_replay[:7]]
    assert all(21 <= uid <= 27 for uid in top_7_replay_ids), "HighPrio users should be first for Replay"
    
    group4_replay_scores_sessions = [(u["score"], u["user"].total_replay_sessions) for u in sorted_users_replay[:7]]
    for i in range(len(group4_replay_scores_sessions) - 1):
        # Ожидаем убывание score, или если score равен, то возрастание session_count (из-за ключа сортировки)
        # BaseScore = 1 / (1+sessions), Score = BaseScore + Prio.
        # При одинаковом Prio, чем меньше sessions, тем больше BaseScore, тем больше итоговый Score.
        assert group4_replay_scores_sessions[i][0] >= group4_replay_scores_sessions[i+1][0]
        if group4_replay_scores_sessions[i][0] == group4_replay_scores_sessions[i+1][0]:
             assert group4_replay_scores_sessions[i][1] <= group4_replay_scores_sessions[i+1][1]


    # Проверяем, что пользователи из группы 6 следующие и отсортированы по total_replay_sessions
    next_6_replay_ids = [u["user"].id for u in sorted_users_replay[7:13]]
    assert all(35 <= uid <= 40 for uid in next_6_replay_ids), "MidPrio users should be after HighPrio for Replay"

    group6_replay_scores_sessions = [(u["score"], u["user"].total_replay_sessions) for u in sorted_users_replay[7:13]]
    for i in range(len(group6_replay_scores_sessions) - 1):
        assert group6_replay_scores_sessions[i][0] >= group6_replay_scores_sessions[i+1][0]
        if group6_replay_scores_sessions[i][0] == group6_replay_scores_sessions[i+1][0]:
             assert group6_replay_scores_sessions[i][1] <= group6_replay_scores_sessions[i+1][1]

    # Проверяем, что оставшиеся пользователи (без приоритета или с истекшим) отсортированы по total_replay_sessions
    remaining_users_replay = sorted_users_replay[13:]
    for i in range(len(remaining_users_replay) - 1):
        user_i_data = remaining_users_replay[i]
        user_j_data = remaining_users_replay[i+1]
        # Ожидаем, что score[i] >= score[j]. Если score[i] == score[j], то sessions_replay[i] <= sessions_replay[j]
        assert user_i_data["score"] >= user_j_data["score"]
        if user_i_data["score"] == user_j_data["score"]:
            assert user_i_data["user"].total_replay_sessions <= user_j_data["user"].total_replay_sessions


    # --- Тест для Creative сессии ---
    scored_users_creative = []
    for user in test_users:
        score = calculator.calculate_score(user, ScoreCalculator.SESSION_TYPE_CREATIVE)
        scored_users_creative.append({"user": user, "score": score})

    sorted_users_creative = sorted(
        scored_users_creative,
        key=lambda x: (x["score"], -x["user"].total_creative_sessions, x["user"].id),
        reverse=True
    )

    # Проверки аналогичны Replay, но для creative_sessions и соответствующих групп
    top_7_creative_ids = [u["user"].id for u in sorted_users_creative[:7]]
    assert all(21 <= uid <= 27 for uid in top_7_creative_ids), "HighPrio users should be first for Creative"
    
    group4_creative_scores_sessions = [(u["score"], u["user"].total_creative_sessions) for u in sorted_users_creative[:7]]
    for i in range(len(group4_creative_scores_sessions) - 1):
        assert group4_creative_scores_sessions[i][0] >= group4_creative_scores_sessions[i+1][0]
        if group4_creative_scores_sessions[i][0] == group4_creative_scores_sessions[i+1][0]:
             assert group4_creative_scores_sessions[i][1] <= group4_creative_scores_sessions[i+1][1]

    next_6_creative_ids = [u["user"].id for u in sorted_users_creative[7:13]]
    assert all(35 <= uid <= 40 for uid in next_6_creative_ids), "MidPrio users should be after HighPrio for Creative"

    group6_creative_scores_sessions = [(u["score"], u["user"].total_creative_sessions) for u in sorted_users_creative[7:13]]
    for i in range(len(group6_creative_scores_sessions) - 1):
        assert group6_creative_scores_sessions[i][0] >= group6_creative_scores_sessions[i+1][0]
        if group6_creative_scores_sessions[i][0] == group6_creative_scores_sessions[i+1][0]:
             assert group6_creative_scores_sessions[i][1] <= group6_creative_scores_sessions[i+1][1]


    remaining_users_creative = sorted_users_creative[13:]
    for i in range(len(remaining_users_creative) - 1):
        user_i_data = remaining_users_creative[i]
        user_j_data = remaining_users_creative[i+1]
        assert user_i_data["score"] >= user_j_data["score"]
        if user_i_data["score"] == user_j_data["score"]:
            assert user_i_data["user"].total_creative_sessions <= user_j_data["user"].total_creative_sessions
            
    # --- Тест на неизвестный тип сессии ---
    user_for_unknown = test_users[0] # Берем любого пользователя
    unknown_score = calculator.calculate_score(user_for_unknown, "invalid_session_type")
    assert unknown_score == 0.0, "Score should be 0.0 for unknown session type"

    # --- Тест: priority_coefficient = 0.0, но есть дата истечения ---
    user_prio_zero_expiry = User(
        id=100, nickname="PrioZeroExpiry", join_date=now,
        total_replay_sessions=5, total_creative_sessions=5,
        priority_coefficient=0.0, priority_expires_at=tomorrow, # Коэффициент 0, дата есть
        priority_given_by=None
    )
    expected_score_prio_zero = 1.0 / (1.0 + 5.0) # Только base score
    actual_score_prio_zero = calculator.calculate_score(user_prio_zero_expiry, ScoreCalculator.SESSION_TYPE_REPLAY)
    assert actual_score_prio_zero == pytest.approx(expected_score_prio_zero), \
        "Score should be base score if priority_coefficient is 0, even with expiry date"

    # --- Тест: priority_coefficient != 0.0, priority_expires_at = None ---
    user_prio_val_no_expiry = User(
        id=101, nickname="PrioValNoExpiry", join_date=now,
        total_replay_sessions=2, total_creative_sessions=2,
        priority_coefficient=0.25, priority_expires_at=None, # Коэффициент есть, даты нет
        priority_given_by=None
    )
    expected_score_prio_val_no_expiry = (1.0 / (1.0 + 2.0)) + 0.25
    actual_score_prio_val_no_expiry = calculator.calculate_score(user_prio_val_no_expiry, ScoreCalculator.SESSION_TYPE_REPLAY)
    assert actual_score_prio_val_no_expiry == pytest.approx(expected_score_prio_val_no_expiry), \
        "Score should include priority_coefficient if it's non-zero and expires_at is None"
