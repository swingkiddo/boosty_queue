import discord
from logger import logger

class SessionQueueEmbed(discord.Embed):
    def __init__(self, coach, session_id: int):
        super().__init__(title=f"Очередь на сессию {session_id}")
        self.coach = coach
        self.add_field(name="Коуч", value=coach.mention, inline=False)
        self.add_field(name="Очередь", value="", inline=False)
        help_text = (
            f"$queue {session_id} - присоединиться к очереди\n"
            f"$leave {session_id} - покинуть очередь\n\n"
            f"Команды нужно вводить в канале КОМАНДЫ-ДЛЯ-БОТА"
        )
        self.add_field(name="Доступные команды", value=help_text, inline=False)

    def update_queue(self, queue: list[discord.Member]):
        self.set_field_at(1, name="Очередь", value="\n".join([member.mention for member in queue]))

class SessionEmbed(discord.Embed):
    def __init__(self, participants: list[discord.Member], session_id: int, max_slots: int = 8):
        super().__init__(title=f"Сессия {session_id}")
        self.slots = {slot_num: "" for slot_num in range(max_slots)}
        for slot_num in range(max_slots):
            if slot_num < len(participants):
                user = participants[slot_num]
                self.slots[slot_num] = user.mention
            self.add_field(name=f"Слот {slot_num + 1}", value="", inline=True)
        help_text = (
            f"$join {session_id} - присоединиться к сессии\n"
            f"$quit {session_id} - освободить слот\n\n"
            f"Команды нужно вводить в канале КОМАНДЫ-ДЛЯ-БОТА"
        )
        self.add_field(name="Доступные команды", value=help_text, inline=False)
        logger.info(f"SessionEmbed: slots: {self.slots}")
        self.update_fields()

    def update_fields(self):
        for slot_num, user in self.slots.items():
            self.set_field_at(slot_num, name=f"Слот {slot_num + 1}", value=user, inline=False)
        
    def count_free_slots(self) -> int:
        return sum(1 for user in self.slots.values() if user == "")