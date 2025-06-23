import discord
from discord.ui import Button
from models.session import Session, SessionRequestStatus
from ui.embeds import SessionEmbed
from services import SessionService, UserService
from logger import logger

class QuitSessionButton(Button):
    def __init__(self, session: Session, session_service: SessionService, user_service: UserService):
        super().__init__(label="Освободить слот", style=discord.ButtonStyle.danger, custom_id="quit_session")
        self.session = session
        self.session_service = session_service
        self.user_service = user_service

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            # Используем тот же алгоритм, что и в командах
            success, error_msg = await self._remove_user_from_session(interaction)
            
            if success:
                await interaction.followup.send("Вы успешно покинули сессию", ephemeral=True)
            else:
                await interaction.followup.send(error_msg, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in QuitSessionButton: {e}")
            await interaction.followup.send("Произошла ошибка при выходе из сессии", ephemeral=True)

    async def _remove_user_from_session(self, interaction: discord.Interaction) -> tuple[bool, str]:
        """Приватный метод для удаления пользователя из сессии (аналогичен основному классу)."""
        try:
            guild = interaction.guild
            user_id = interaction.user.id
            request = await self.session_service.get_request_by_user_id(self.session.id, user_id)
            if not request or request.status != SessionRequestStatus.ACCEPTED.value:
                return False, "Вы не участвуете в этой сессии"
            
            await self.session_service.update_request(
                request.id, 
                status=SessionRequestStatus.REJECTED.value, 
                slot_number=None
            )
            
            # Пересчитываем слоты
            accepted_requests = await self.session_service.get_accepted_requests(self.session.id)
            for idx, req in enumerate(accepted_requests):
                if req.slot_number != idx + 1:
                    await self.session_service.update_request(req.id, slot_number=idx + 1)
            
            # Обновляем embed
            participants = [guild.get_member(req.user_id) for req in accepted_requests]
            embed = SessionEmbed(participants, self.session.id, self.session.max_slots)
            await interaction.message.edit(embed=embed)
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error removing user {user_id} from session: {e}")
            return False, "Произошла ошибка при удалении из сессии"
