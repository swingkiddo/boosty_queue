import discord
from discord.ui import Button
from models.session import Session, SessionRequestStatus
from ui.embeds import SessionQueueEmbed
from services import SessionService, UserService
from logger import logger

class JoinQueueButton(Button):
    def __init__(self, session: Session, session_service: SessionService, user_service: UserService):
        super().__init__(label="🏃 В очередь", style=discord.ButtonStyle.success, custom_id="join_session")
        self.session = session
        self.session_service = session_service
        self.user_service = user_service
        
    async def callback(self, interaction: discord.Interaction):
        try:
            # if interaction.user.id == self.session.coach_id:
            #     await interaction.response.send_message("Вы не можете присоединиться к своей сессии", ephemeral=True)
            #     return
            guild = interaction.guild
            members = guild.members
            info_message = interaction.message

            participant = await self.user_service.get_user(interaction.user.id)
            if not participant:
                participant = await self.user_service.create_user(interaction.user.id, interaction.user.name, join_date=interaction.user.joined_at.replace(tzinfo=None))

            request = await self.session_service.get_request_by_user_id(self.session.id, participant.id)
            if request:
                await interaction.response.send_message("Вы уже в очереди", ephemeral=True)
                return

            request = await self.session_service.create_request(self.session.id, participant.id)
            requests = await self.session_service.get_requests_by_session_id(self.session.id)
            requests = [request for request in requests if request.status == SessionRequestStatus.PENDING.value]
            user_ids = [request.user_id for request in requests]
            members = [member for member in members if member.id in user_ids]

            coach = await guild.fetch_member(self.session.coach_id)
            embed = SessionQueueEmbed(coach, self.session.id)
            embed.update_queue(members)

            await info_message.edit(embed=embed)
            await interaction.response.send_message("Вы присоединились к сессии", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("У меня нет прав на редактирование этого сообщения", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("Произошла ошибка при присоединении к сессии", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("Сообщение не найдено", ephemeral=True)
        except Exception as e:
            import traceback
            logger.error(f"Error joining session: {traceback.format_exc()}")
            await interaction.response.send_message("Произошла ошибка при присоединении к сессии", ephemeral=True)
