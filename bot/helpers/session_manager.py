from models.session import Session

class SessionManager:
    def __init__(self):
        self.sessions = {}

    def add_session(self, session: Session, slots: dict[int, str] = {}):
        self.sessions[session.id] = {
            "session": session,
            "slots": slots
        }

    def get_session(self, session_id: int) -> Session:
        return self.sessions[session_id]["session"]

    def remove_session(self, session_id: int):
        del self.sessions[session_id]

    def count_free_slots(self, session_id: int) -> int:
        return self.sessions[session_id]["session"].max_slots - len(self.sessions[session_id]["slots"])

    def get_slots(self, session_id: int) -> dict[int, str]:
        return self.sessions[session_id]["slots"]
    
    def set_slot(self, session_id: int, slot_num: int, user_mention: str):
        self.sessions[session_id]["slots"][slot_num] = user_mention

    def remove_slot(self, session_id: int, slot_num: int):
        del self.sessions[session_id]["slots"][slot_num]


        