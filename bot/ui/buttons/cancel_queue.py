import discord
from discord.ui import Button
from models.session import Session, SessionRequestStatus
from ui.embeds import SessionQueueEmbed
from services import SessionService, UserService
from logger import logger

class CancelQueueButton(Button):
    def __init__(self, session: Session, session_service: SessionService, user_service: UserService):
        super().__init__(label="❌ Выйти", style=discord.ButtonStyle.danger, custom_id="cancel_session")
        self.session = session
        self.session_service = session_service
        self.user_service = user_service

    async def callback(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
            all_guild_members = guild.members # Store all members for reliable filtering
            info_message = interaction.message

            participant = await self.user_service.get_user(interaction.user.id)
            if not participant:
                participant = await self.user_service.create_user(interaction.user.id, interaction.user.name, join_date=interaction.user.joined_at.replace(tzinfo=None))

            request = await self.session_service.get_request_by_user_id(self.session.id, participant.id)

            if not request:
                await interaction.response.send_message("Вы не присоединились к этой сессии", ephemeral=True)
                return

            response_message_content = ""
            refresh_embed = False

            if request.status == SessionRequestStatus.PENDING.value:
                await self.session_service.delete_request(request.id)
                response_message_content = "Вы отменили свою заявку на участие в сессии."
                refresh_embed = True
            else:
                response_message_content = f"Ваша заявка не может быть отменена, так как её текущий статус: '{request.status}'. Очередь не была изменена для вас."
                # Embed will still be refreshed to show current state, as per original logic.
                refresh_embed = True

            # Always refresh the embed to show the current state of the queue
            # This was the original behavior: embed is updated regardless of whether the specific user's request was PENDING.
            current_session_requests = await self.session_service.get_requests_by_session_id(self.session.id)
            pending_user_ids = [req.user_id for req in current_session_requests if req.status == SessionRequestStatus.PENDING.value]
            
            # Filter from the complete list of guild members
            actual_pending_members = [member for member in all_guild_members if member.id in pending_user_ids]
            
            coach = await guild.fetch_member(self.session.coach_id)
            embed = SessionQueueEmbed(coach, self.session.id)
            embed.update_queue(actual_pending_members)
            await info_message.edit(embed=embed)

            # Send the single, appropriate response to the interaction
            await interaction.response.send_message(response_message_content, ephemeral=True)

        except discord.Forbidden:
            # Check if interaction already responded to, common in error handling
            if interaction and not interaction.response.is_done():
                await interaction.response.send_message("У меня нет прав на выполнение этого действия.", ephemeral=True)
            else:
                await interaction.followup.send("У меня нет прав на выполнение этого действия.", ephemeral=True)
        except discord.HTTPException:
            if interaction and not interaction.response.is_done():
                await interaction.response.send_message("Произошла ошибка сети при отмене заявки.", ephemeral=True)
            else:
                await interaction.followup.send("Произошла ошибка сети при отмене заявки.", ephemeral=True)
        except discord.NotFound:
            if interaction and not interaction.response.is_done():
                await interaction.response.send_message("Необходимые данные не найдены для отмены заявки.", ephemeral=True)
            else:
                await interaction.followup.send("Необходимые данные не найдены для отмены заявки.", ephemeral=True)
        except Exception as e:
            import traceback
            logger.error(f"Error canceling session: {traceback.format_exc()}")
            if interaction and not interaction.response.is_done():
                await interaction.response.send_message("Произошла непредвиденная ошибка при отмене заявки на участие в сессии.", ephemeral=True)
            elif interaction: # If deferred or already responded, use followup
                await interaction.followup.send("Произошла непредвиденная ошибка при отмене заявки на участие в сессии.", ephemeral=True)
