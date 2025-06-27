import math
from datetime import datetime, timedelta
from models import User
from logger import logger

class ScoreCalculator:
    SESSION_TYPE_REPLAY = "replay"
    SESSION_TYPE_CREATIVE = "creative"

    @staticmethod
    def calculate_score(user: User, session_type: str) -> float:
        """
        Рассчитывает очки пользователя для определения приоритета в очереди на сессию.

        Score = BaseScore + PriorityCoefficient
        BaseScore = 1 / (1 + session_count)
        PriorityCoefficient действителен, если priority_expires_at не истек.

        Args:
            user: Объект пользователя (User).
            session_type: Тип сессии (ScoreCalculator.SESSION_TYPE_REPLAY или ScoreCalculator.SESSION_TYPE_CREATIVE).

        Returns:
            Рассчитанный балл (score).
        """

        if not session_type in [ScoreCalculator.SESSION_TYPE_REPLAY, ScoreCalculator.SESSION_TYPE_CREATIVE]:
            logger.warning(
                f"Unknown session type: '{session_type}' for user {user.id} ({user.nickname}). "
                f"Valid types are '{ScoreCalculator.SESSION_TYPE_REPLAY}' and '{ScoreCalculator.SESSION_TYPE_CREATIVE}'. "
                "Returning 0.0 score."
            )
            return 0.0

        # Приведение session_count к float для корректного деления
        # Предполагается, что session_count всегда >= 0
        session_count = user.get_sessions_count(session_type)
        base_score = 1.0 / (1.0 + float(session_count))

        applied_priority_coefficient = 0.0
        # user.priority_coefficient имеет default=0 и не nullable
        if user.priority_coefficient != 0.0: # Сравнение float с float
            if user.priority_expires_at is None or datetime.utcnow() < user.priority_expires_at:
                applied_priority_coefficient = user.priority_coefficient
            else:
                logger.info(
                    f"Priority coefficient for user {user.id} ({user.nickname}) has expired. "
                    f"Expired at: {user.priority_expires_at}, Coefficient value: {user.priority_coefficient}. "
                    "It will not be applied."
                )
        
        final_score = base_score + applied_priority_coefficient

        logger.debug(
            f"Score calculation details for user {user.id} ({user.nickname}), session type '{session_type}':\n"
            f"  Session Count ({('replay' if session_type == ScoreCalculator.SESSION_TYPE_REPLAY else 'creative')} sessions): {session_count}\n"
            f"  Base Score (1.0 / (1.0 + session_count)): {base_score:.4f}\n"
            f"  User's Stored Priority Coefficient: {user.priority_coefficient}\n"
            f"  User's Priority Expires At: {user.priority_expires_at}\n"
            f"  Applied Priority Coefficient (after checking expiry): {applied_priority_coefficient:.4f}\n"
            f"  Final Score (Base Score + Applied Priority Coefficient): {final_score:.4f}"
        )

        return final_score
