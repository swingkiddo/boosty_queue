import discord
from discord.ui import View, Button
from discord.ext import commands
from models import Session, SessionRequestStatus
from services import SessionService, DiscordService, UserService
from factory import ServiceFactory
from logger import logger
from datetime import datetime, timedelta

class SessionQueueView(View):
    def __init__(self, session: Session, session_service: SessionService, discord_service: DiscordService, user_service: UserService):
        super().__init__()
        self.session = session
        self.session_service = session_service
        self.discord_service = discord_service
        self.user_service = user_service
        self.add_item(JoinSessionButton(session, session_service, user_service))
        self.add_item(CancelSessionButton(session, session_service, user_service))

class JoinSessionButton(Button):
    def __init__(self, session: Session, session_service: SessionService, user_service: UserService):
        super().__init__(label="Присоединиться", style=discord.ButtonStyle.success, custom_id="join_session")
        self.session = session
        self.session_service = session_service
        self.user_service = user_service
        
    async def callback(self, interaction: discord.Interaction):
        try:
            if interaction.user.id == self.session.coach_id:
                await interaction.response.send_message("Вы не можете присоединиться к своей сессии", ephemeral=True)
                return
            guild = interaction.guild
            members = guild.members
            info_message = interaction.message

            participant = await self.user_service.get_user(interaction.user.id)
            if not participant:
                participant = await self.user_service.create_user(interaction.user.id, interaction.user.name, join_date=interaction.user.joined_at.replace(tzinfo=None))

            request = await self.session_service.create_request(self.session.id, participant.id)
            requests = await self.session_service.get_requests_by_session_id(self.session.id)
            requests = [request for request in requests if request.status == SessionRequestStatus.PENDING.value]
            requests = [request.user_id for request in requests]
            members = [member for member in members if member.id in requests]
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

class CancelSessionButton(Button):
    def __init__(self, session: Session, session_service: SessionService, user_service: UserService):
        super().__init__(label="Выйти из очереди", style=discord.ButtonStyle.danger, custom_id="cancel_session")
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

class SessionQueueEmbed(discord.Embed):
    def __init__(self, coach, session_id: int):
        super().__init__(title=f"Очередь на сессию {session_id}")
        self.coach = coach
        self.add_field(name="Коуч", value=coach.mention, inline=False)
        self.add_field(name="Очередь", value="", inline=False)

    def update_queue(self, queue: list[discord.Member]):
        self.set_field_at(1, name="Очередь", value="\n".join([member.mention for member in queue]))

class SessionView(View):
    def __init__(self, session: Session, session_service: SessionService, discord_service: DiscordService, user_service: UserService):
        super().__init__()
        self.session = session
        self.session_service = session_service
        self.discord_service = discord_service
        self.user_service = user_service
        self.add_item(QuickJoinButton(session, session_service, user_service))
        self.add_item(QuitSessionButton(session, session_service, user_service))

class QuickJoinButton(Button):
    def __init__(self, session: Session, session_service: SessionService, user_service: UserService):
        super().__init__(label="Быстро присоединиться", style=discord.ButtonStyle.success, custom_id="quick_join")
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

            if request and request.status == SessionRequestStatus.REJECTED.value:
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

class QuitSessionButton(Button):
    def __init__(self, session: Session, session_service: SessionService, user_service: UserService):
        super().__init__(label="Выйти из сессии", style=discord.ButtonStyle.danger, custom_id="quit_session")
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
            await self.session_service.update_request_status(request.id, SessionRequestStatus.REJECTED)
            requests = await self.session_service.get_requests_by_session_id(self.session.id)
            participants = [interaction.guild.get_member(request.user_id) for request in requests if request.status == SessionRequestStatus.ACCEPTED.value]
            embed = SessionEmbed(participants, self.session.id, self.session.max_slots)
            await message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Error in QuitSessionButton: {e.with_traceback()}")
            await interaction.followup.send("Произошла ошибка при выходе из сессии", ephemeral=True)

class SessionEmbed(discord.Embed):
    def __init__(self, participants: list[discord.Member], session_id: int, max_slots: int = 8):
        super().__init__(title=f"Сессия {session_id}")
        self.slots = {slot_num: "" for slot_num in range(max_slots)}
        for slot_num in range(max_slots):
            if slot_num < len(participants):
                user = participants[slot_num]
                self.slots[slot_num] = user.mention
            self.add_field(name=f"Слот {slot_num + 1}", value="", inline=True)
        logger.info(f"SessionEmbed: slots: {self.slots}")
        self.update_fields()

    def update_fields(self):
        for slot_num, user in self.slots.items():
            self.set_field_at(slot_num, name=f"Слот {slot_num + 1}", value=user, inline=False)
        
    def count_free_slots(self) -> int:
        return sum(1 for user in self.slots.values() if user == "")

class EndSessionConfirmationView(discord.ui.View):
    def __init__(self, bot: commands.Bot, session: Session, service_factory: ServiceFactory, original_interaction: discord.Interaction = None):
        super().__init__(timeout=180) # Таймаут для View
        self.bot = bot
        self.session = session
        self.service_factory = service_factory
        self.original_interaction = original_interaction
        self.add_item(AllParticipantsReviewedButton(self.bot, self.session, self.service_factory))
        self.add_item(NotAllParticipantsReviewedButton(self.bot, self.session, self.service_factory))

    async def disable_all_items(self):
        for item in self.children:
            item.disabled = True
        if self.original_interaction:
            await self.original_interaction.edit_original_response(view=self)
        elif self.message: # Если View привязано к сообщению
            await self.message.edit(view=self)

    async def on_timeout(self):
        await self.disable_all_items()
        if self.original_interaction:
            await self.original_interaction.followup.send("Время на ответ истекло.", ephemeral=True)
        # Если нет original_interaction, но есть self.message, можно попытаться отредактировать его
        # или отправить новое сообщение в канал, где было исходное сообщение View.
        # Для этого потребуется доступ к каналу, например, через self.session.text_channel_id

class AllParticipantsReviewedButton(Button):
    def __init__(self, bot: commands.Bot, session: Session, service_factory: ServiceFactory):
        super().__init__(label="Да, все разобраны", style=discord.ButtonStyle.success, custom_id="all_reviewed")
        self.session = session
        self.service_factory = service_factory
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer() # Подтверждаем получение взаимодействия
        if not interaction.user.id == self.session.coach_id:
            await interaction.followup.send("Вы не можете завершить сессию, так как не являетесь коучем.", ephemeral=True)
            return
        try:
            session_service = self.service_factory.get_service('session')
            user_service = self.service_factory.get_service('user')
            await session_service.update_session(self.session.id, is_active=False)
            await interaction.followup.send(f"Сессия `{self.session.id}` успешно завершена. Все участники были разобраны.", ephemeral=True)
            requests = await session_service.get_requests_by_session_id(self.session.id)
            for request in requests:
                if request.status == SessionRequestStatus.ACCEPTED.value:
                    user = await user_service.get_user(request.user_id)
                    field_name = "total_replay_sessions" if self.session.type == "replay" else "total_creative_sessions"
                    field = getattr(user, field_name)
                    await user_service.update_user(user.id, **{field_name: field + 1})
            
            # Отключаем кнопки в исходном сообщении
            if self.view:
                await self.view.disable_all_items()
                await interaction.edit_original_response(view=self.view)

        except Exception as e:
            import traceback
            logger.error(f"Error in AllParticipantsReviewedButton: {traceback.format_exc()}")
            await interaction.followup.send("Произошла ошибка при завершении сессии.", ephemeral=True)


class NotAllParticipantsReviewedButton(Button):
    def __init__(self, bot: commands.Bot, session: Session, service_factory: ServiceFactory):
        super().__init__(label="Нет, не все", style=discord.ButtonStyle.danger, custom_id="not_all_reviewed")
        self.bot = bot
        self.session = session
        self.service_factory = service_factory

    async def callback(self, interaction: discord.Interaction):
        logger.info(interaction)
        if not interaction.user.id == self.session.coach_id:
            logger.info(f"NotAllParticipantsReviewedButton: interaction.user.id: {interaction.user.id}, session.coach_id: {self.session.coach_id}")
            await interaction.followup.send("Вы не можете выбрать участников для выбора, так как не являетесь коучем.", ephemeral=True)
            return
        try:
            await interaction.response.defer()
            # Здесь будет логика для отображения UserSelect
            # Пока просто заглушка
            
            user_service = self.service_factory.get_service('user')
            session_service = self.service_factory.get_service('session')
            logger.info(f"Session: {self.session}")
            requests = await session_service.get_requests_by_session_id(self.session.id)
            logger.info(f"Requests: {requests}")
            logger.info(f"Guild: {interaction.guild}")
            # Мы заинтересованы в тех, кто был принят или хотя бы ожидал
            accepted_or_pending_user_ids = [
                req.user_id for req in requests 
                if req.status in [SessionRequestStatus.ACCEPTED.value, SessionRequestStatus.PENDING.value]
            ]
            
            if not accepted_or_pending_user_ids:
                await interaction.followup.send("В сессии нет участников для выбора.", ephemeral=True)
                if self.view:
                    await self.view.disable_all_items()
                    await interaction.edit_original_response(view=self.view)
                return

            participants = await user_service.get_users_by_ids(accepted_or_pending_user_ids)
            
            # Преобразуем пользователей из БД в discord.Member или discord.User объекты для UserSelect
            guild_members = []
            for p_user in participants:
                member = interaction.guild.get_member(p_user.id)
                if member:
                    guild_members.append(member)
                else: # Если пользователь покинул сервер, но остался в БД
                    try:
                        user_obj = await interaction.client.fetch_user(p_user.id)
                        guild_members.append(user_obj) # UserSelect может работать и с discord.User
                    except discord.NotFound:
                        logger.warn(f"User with ID {p_user.id} not found on Discord.")


            if not guild_members:
                await interaction.followup.send("Не удалось получить информацию об участниках сессии для выбора.", ephemeral=True)
                if self.view:
                    await self.view.disable_all_items()
                    await interaction.edit_original_response(view=self.view)
                return

            # Создаем View с UserSelect
            select_view = UnreviewedParticipantsSelectView(self.session, self.service_factory, guild_members, interaction)
            await interaction.followup.send("Выберите неразобранных участников:", view=select_view, ephemeral=True)
            select_view.message = await interaction.original_response() # Сохраняем сообщение для View

            # Отключаем кнопки в исходном сообщении
            if self.view:
                await self.view.disable_all_items()
                # interaction.edit_original_response здесь не нужен, так как мы уже отправили followup
                # Если мы хотим отредактировать исходное сообщение, чтобы убрать кнопки:
                # if self.view.message:
                #     await self.view.message.edit(view=self.view)
                if self.view.original_interaction: # Если это View было отправлено как ответ на interaction
                     await self.view.original_interaction.edit_original_response(view=self.view)


        except Exception as e:
            import traceback
            logger.error(f"Error in NotAllParticipantsReviewedButton: {traceback.format_exc()}")
            await interaction.followup.send("Произошла ошибка при подготовке выбора участников.", ephemeral=True)

# Заглушка для View с UserSelect, которую мы реализуем далее
class UnreviewedParticipantsSelectView(View):
    def __init__(self, session: Session, service_factory: ServiceFactory, participants: list[discord.abc.User | discord.Member], original_interaction: discord.Interaction):
        super().__init__(timeout=300) # Таймаут для выбора
        self.session = session
        self.service_factory = service_factory
        # participants - это уже отфильтрованные discord.Member или discord.User объекты
        self.participants = participants 
        self.original_interaction = original_interaction 
        self.selected_user_ids = [] # Будем хранить строки ID

        # Ограничиваем количество участников для одного StringSelect (макс 25)
        # Если участников больше, нужно будет продумать пагинацию или несколько селектов.
        # Пока что просто возьмем первых 25.
        display_participants = participants[:25]
        if len(participants) > 25:
            # Можно добавить логгирование или уведомление коучу, что показаны не все
            logger.warn(f"Session {session.id}: More than 25 participants for UnreviewedParticipantsStringSelect, showing first 25.")


        self.add_item(UnreviewedParticipantsStringSelect(display_participants))
        self.add_item(ConfirmUnreviewedSelectionButton(self))

    async def disable_all_items(self):
        for item in self.children:
            item.disabled = True
        # Это View отправляется через followup.send.
        # Редактируем сообщение, к которому оно прикреплено, через self.message.
        if self.message: # self.message должно быть установлено после отправки View
            await self.message.edit(view=self)

    async def on_timeout(self):
        await self.disable_all_items()
        # Сообщаем пользователю, что время вышло
        await self.original_interaction.followup.send("Время на выбор неразобранных участников истекло. Сессия будет завершена без этой информации.", ephemeral=True)
        # Автоматически завершаем сессию, как если бы нажали "Да, все разобраны"
        # Это спорное поведение, возможно, лучше просто ничего не делать или запросить подтверждение.
        # Пока оставим так для простоты.
        session_service = self.service_factory.get_service('session')
        discord_service = self.service_factory.get_service('discord')
        guild = self.original_interaction.guild # Получаем guild из interaction

        await session_service.update_session(self.session.id, is_active=False)

# Меняем UserSelect на StringSelect, а точнее на правильный discord.ui.Select
class UnreviewedParticipantsStringSelect(discord.ui.Select):
    def __init__(self, participants: list[discord.abc.User | discord.Member]):
        options = []
        logger.info(f"Participants: {participants}")
        if not participants:
            # Если список участников пуст, добавляем "заглушку", чтобы Select не был пустым
            # Этого не должно происходить, если есть проверка в NotAllParticipantsReviewedButton
            options.append(discord.SelectOption(label="Нет участников для выбора", value="no_participants", default=True))
            max_opts = 1
            min_opts = 0 # или 1, если всегда должен быть выбор "нет участников"
        else:
            options = [
                discord.SelectOption(
                    label=member.display_name[:100], # label имеет лимит 100 символов
                    value=str(member.id),
                    description=f"ID: {member.id}"[:100] # description имеет лимит 100 символов
                )
                for member in participants # participants - это уже discord.Member или discord.User
            ]
            max_opts = len(options)
            min_opts = 0 # Разрешить не выбирать никого

        super().__init__(
            placeholder="Выберите неразобранных участников...",
            min_values=min_opts,
            max_values=max_opts, # Можно выбрать всех из предложенных
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # self.values будет списком строк (ID пользователей), которые были выбраны
        if "no_participants" in self.values:
             self.view.selected_user_ids = []
        else:
            self.view.selected_user_ids = self.values
        await interaction.response.defer()


class ConfirmUnreviewedSelectionButton(Button):
    def __init__(self, parent_view: UnreviewedParticipantsSelectView):
        super().__init__(label="Подтвердить выбор и завершить", style=discord.ButtonStyle.primary, custom_id="confirm_unreviewed_selection")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Получаем актуальные данные из parent_view
        session = self.parent_view.session
        service_factory = self.parent_view.service_factory
        selected_user_ids = self.parent_view.selected_user_ids # <--- Получаем актуальное значение здесь

        session_service = service_factory.get_service('session')
        user_service = service_factory.get_service('user') # Убедимся, что user_service тоже получаем из factory
        
        logger.info(f"Selected user IDs: {selected_user_ids}")
        unreviewed_db_user_ids = [int(uid) for uid in selected_user_ids]
        logger.info(f"Session {session.id}: Coach indicated users {unreviewed_db_user_ids} were not reviewed.")
        
        for user_id_str in selected_user_ids:
            try:
                logger.info(f"User ID: {user_id_str}")
                user_id = int(user_id_str)
                logger.info(f"User ID: {user_id}")
                request = await session_service.get_request_by_user_id(session.id, user_id)
                logger.info(f"Request: {request}")
                if request:
                    await session_service.update_request_status(request.id, SessionRequestStatus.SKIPPED)
            except Exception as e:
                # Используйте e.with_traceback(None) или просто e, если traceback уже залогирован или не нужен в сообщении
                logger.error(f"Error updating request status for user {user_id_str}: {e}", exc_info=True)


        await session_service.update_session(session.id, is_active=False)
        
        requests = await session_service.get_requests_by_session_id(session.id)
        # Убедимся, что users получаем после всех обновлений статусов, если это важно для логики ниже
        all_user_ids_in_session = [req.user_id for req in requests]
        
        # Проверка, есть ли вообще пользователи для обработки
        if not all_user_ids_in_session:
            logger.info(f"No users found in session {session.id} for post-session updates.")
        else:
            users_from_db = await user_service.get_users_by_ids(all_user_ids_in_session)
            users_map = {user.id: user for user in users_from_db}

            for request in requests:
                user = users_map.get(request.user_id)
                if not user:
                    logger.warn(f"User with ID {request.user_id} from session request not found in DB batch fetch.")
                    continue

                data = {}
                session_type = session.type # Получаем тип сессии из объекта session
                if request.status == SessionRequestStatus.ACCEPTED.value:
                    field = "total_replay_sessions" if session_type == 'replay' else "total_creative_sessions"
                    data[field] = getattr(user, field, 0) + 1 # getattr с default значением
                    if user.priority_coefficient == 1: # или user.priority_coefficient == 1.0 если это float
                        data['priority_coefficient'] = 0.0 # или 0.0
                        data['priority_expires_at'] = None
                    if data: # Обновляем только если есть что обновлять
                        await user_service.update_user(user.id, **data)
                        logger.info(f'User {user.nickname or user.name} (ID: {user.id}) ACCEPTED stats updated successfully with data: {data}')

                elif request.status == SessionRequestStatus.SKIPPED.value:
                    data = {
                        'priority_coefficient': 1.0, # или 1.0
                        'priority_expires_at': datetime.now() + timedelta(days=7)
                    }
                    await user_service.update_user(user.id, **data)
                    logger.info(f'User {user.nickname or user.name} (ID: {user.id}) SKIPPED stats updated successfully with data: {data}')

        selected_mentions = [f"<@{uid}>" for uid in self.selected_user_ids]
        message = f"Сессия `{self.session.id}` завершена. "
        if selected_mentions:
            message += f"Коуч отметил следующих участников как неразобранных: {', '.join(selected_mentions)}."
        else:
            message += "Все выбранные ранее участники были разобраны (или никто не был выбран как неразобранный)."

        await interaction.followup.send(message, ephemeral=True)
        
        # Отключаем элементы в UnreviewedParticipantsSelectView
        if self.view: # self.view здесь это UnreviewedParticipantsSelectView
            await self.view.disable_all_items()
            # Редактируем сообщение, к которому прикреплен UnreviewedParticipantsSelectView
            await self.parent_view.original_interaction.edit_original_response(view=self.view)

class ReviewSessionView(View):
    def __init__(self, session: Session, session_service: SessionService, user_service: UserService):
        super().__init__()
        self.session = session
        self.session_service = session_service
        self.user_service = user_service
        self.add_item(LikeButton(session, session_service, user_service))
        self.add_item(DislikeButton(session, session_service, user_service))

class LikeButton(Button):
    def __init__(self, session: Session, session_service: SessionService, user_service: UserService):
        super().__init__(label="👍", style=discord.ButtonStyle.success, custom_id="like")
        self.session = session
        self.session_service = session_service
        self.user_service = user_service

    async def callback(self, interaction: discord.Interaction):
        logger.info(f"LikeButton callback called for session {self.session.id}")
        await interaction.response.defer()
        try:
            user = interaction.user
            if user.id == self.session.coach_id:
                await interaction.followup.send("Вы не можете оценивать себя.", ephemeral=True)
                return
            reviews = await self.session_service.get_reviews_by_session_id(self.session.id)
            review = next((r for r in reviews if r.user_id == user.id), None)
            if review:
                await self.session_service.update_review(review.id, rating=1)
            else:
                await self.session_service.create_review(self.session.id, user.id, rating=1)
            await interaction.followup.send("Спасибо за оценку!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in LikeButton: {e.with_traceback()}")
            await interaction.followup.send("Произошла ошибка при оценке сессии", ephemeral=True)
            
class DislikeButton(Button):
    def __init__(self, session: Session, session_service: SessionService, user_service: UserService):
        super().__init__(label="👎", style=discord.ButtonStyle.danger, custom_id="dislike")
        self.session = session
        self.session_service = session_service
        self.user_service = user_service

    async def callback(self, interaction: discord.Interaction):
        logger.info(f"DislikeButton callback called for session {self.session.id}")
        await interaction.response.defer()
        try:
            user = interaction.user
            if user.id == self.session.coach_id:
                await interaction.followup.send("Вы не можете оценивать себя.", ephemeral=True)
                return
            reviews = await self.session_service.get_reviews_by_session_id(self.session.id)
            logger.info(f"Reviews: {reviews}")
            review = next((r for r in reviews if r.user_id == user.id), None)
            logger.info(f"Review: {review}")
            if review:
                await self.session_service.update_review(review.id, rating=0)
                logger.info(f"Review updated to 0 for user {user.id}")
            else:
                logger.info(f"Review not found for user {user.id}, creating new review")
                await self.session_service.create_review(self.session.id, user.id, rating=0)
                logger.info(f"Review created for user {user.id}")
            await interaction.followup.send("Спасибо за оценку!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in DislikeButton: {e.with_traceback()}")
            await interaction.followup.send("Произошла ошибка при оценке сессии", ephemeral=True)
