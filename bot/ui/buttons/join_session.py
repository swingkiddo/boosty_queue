import discord
from discord.ui import Button
from models.session import Session, SessionRequestStatus
from ui.embeds import SessionEmbed
from services import SessionService, UserService
from logger import logger

class JoinSessionButton(Button):
    def __init__(self, session: Session, session_service: SessionService, user_service: UserService):
        super().__init__(label="Присоединиться", style=discord.ButtonStyle.success, custom_id="quick_join")
        self.session = session
        self.session_service = session_service
        self.user_service = user_service

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            user = interaction.user
            if user.id == self.session.coach_id:
                await interaction.followup.send("Вы не можете присоединиться к своей сессии", ephemeral=True)
                return
            message = interaction.message
            requests = await self.session_service.get_accepted_requests_by_session_id(self.session.id)
            accepted_requests = [request for request in requests if request.status == SessionRequestStatus.ACCEPTED.value]
            if len(accepted_requests) >= self.session.max_slots:
                await interaction.followup.send("В очереди уже достаточно участников", ephemeral=True)
                return

            request = await self.session_service.get_request_by_user_id(self.session.id, user.id)
            if request and request.status == SessionRequestStatus.ACCEPTED.value:
                await interaction.followup.send("Вы уже участвуете в сессии", ephemeral=True)
                return

            if request and (request.status == SessionRequestStatus.REJECTED.value or request.status == SessionRequestStatus.PENDING.value):
                await self.session_service.update_request_status(request.id, SessionRequestStatus.ACCEPTED)
            
            if not request:
                request = await self.session_service.create_request(self.session.id, user.id)
                await self.session_service.update_request_status(request.id, SessionRequestStatus.ACCEPTED)
                
            requests = await self.session_service.get_requests_by_session_id(self.session.id)
            accepted_requests = [request for request in requests if request.status == SessionRequestStatus.ACCEPTED.value]
            participants = [interaction.guild.get_member(request.user_id) for request in accepted_requests]
            await interaction.followup.send(f"Вы присоединились к сессии", ephemeral=True)
            embed = SessionEmbed(participants, self.session.id, self.session.max_slots)
            await message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Error in QuickJoinButton: {e.with_traceback()}")
            await interaction.followup.send("Произошла ошибка при присоединении к сессии", ephemeral=True)