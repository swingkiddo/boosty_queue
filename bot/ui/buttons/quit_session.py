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
            message = interaction.message
            user = interaction.user
            request = await self.session_service.get_request_by_user_id(self.session.id, user.id)
            if not request:
                await interaction.followup.send("Вы не участвуете в этой сессии", ephemeral=True)
                return
            await self.session_service.update_request(request.id, status=SessionRequestStatus.REJECTED.value, slot_number=None)
            requests = await self.session_service.get_accepted_requests(self.session.id)
            for idx, req in enumerate(requests):
                if req.slot_number != idx + 1:
                    await self.session_service.update_request(req.id, slot_number=idx + 1)
            participants = [interaction.guild.get_member(request.user_id) for request in requests]
            embed = SessionEmbed(participants, self.session.id, self.session.max_slots)
            await message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Error in QuitSessionButton: {e.with_traceback()}")
            await interaction.followup.send("Произошла ошибка при выходе из сессии", ephemeral=True)
