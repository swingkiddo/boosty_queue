import discord
from discord.ext import commands
from discord.ext.commands import Cog
from discord import User, Member, Guild, TextChannel

from config import config
from factory import ServiceFactory, get_service_factory
from helpers import ScoreCalculator
from helpers.roles_manager import RolesManager
from logger import logger
from models.session import (
    SessionRequestStatus,
    SessionRequest,
    SessionReview,
    UserSessionActivity,
    Session,
)
from services.discord_service import Roles
from services import ReportService
from utils import get_current_time
from typing import List
from ui import (
    SessionQueueView,
    SessionQueueEmbed,
    SessionView,
    SessionEmbed,
    EndSessionConfirmationView,
    ReviewSessionView,
)

import asyncio
import os
import re  # Добавляем импорт для регулярных выражений


class SessionInfo:
    def __init__(
        self,
        session_id: int,
        coach_id: int,
        requests: List[SessionRequest],
        reviews: List[SessionReview],
        activities: List[UserSessionActivity],
        text_channel_id: int,
        voice_channel_id: int,
        category_id: int,
        max_slots: int,
    ):
        self.session_id = session_id
        self.coach_id = coach_id
        self.requests = requests
        self.reviews = reviews
        self.activities = activities
        self.text_channel_id = text_channel_id
        self.voice_channel_id = voice_channel_id
        self.category_id = category_id
        self.max_slots = max_slots


class SessionCommands(Cog):
    def __init__(self, bot: commands.Bot, service_factory: ServiceFactory):
        self.bot = bot
        self.service_factory = service_factory
        self.SESSION_AUTO_DELETE_TIME = 600
        self.sessions = {}

    async def response_to_user(
        self, ctx: commands.Context, message: str, channel: TextChannel = None
    ):
        if ctx.interaction:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(message, ephemeral=True)
            else:
                await ctx.interaction.followup.send(message, ephemeral=True)
        else:
            await ctx.send(message) if not channel else await channel.send(message)

    @commands.command(name="test")
    async def test(self, ctx: commands.Context):
        user_service = await self.service_factory.get_service("user")

    @commands.hybrid_command(name="create")
    @commands.has_any_role(Roles.MOD, Roles.COACH_T1, Roles.COACH_T2, Roles.COACH_T3)
    async def create_session(
        self, ctx: commands.Context, session_type: str, max_slots: int = 8
    ):
        logger.info(f"type(ctx): {type(ctx)}")
        try:
            logger.info(f"ctx.channel.name: {ctx.channel.name}")
            if not ctx.interaction and not "запуск-сессии" in ctx.channel.name:
                await self.response_to_user(
                    ctx,
                    "Вы не можете создать сессию в этом канале. Пожалуйста, используйте канал 'запуск-сессии'.",
                    ctx.channel,
                )
                return
            if session_type not in ["replay", "creative"]:
                await self.response_to_user(
                    ctx,
                    "Неверный тип сессии. Пожалуйста, используйте 'replay' или 'creative'.",
                    ctx.channel,
                )
                return
            if max_slots > 25:
                await self.response_to_user(
                    ctx,
                    "Максимальное количество участников в сессии - 25.",
                    ctx.channel,
                )
                return

            author = ctx.author
            guild = ctx.guild
            roles_manager = RolesManager(guild)
            await roles_manager.check_roles()

            async with get_service_factory(self.service_factory) as factory:
                user_service = await factory.get_service("user")
                session_service = await factory.get_service("session")
                discord_service = await factory.get_service("discord")

                coach = await user_service.get_user(author.id)
                if not coach:
                    coach = await user_service.create_user(
                        author.id,
                        author.name,
                        join_date=author.joined_at.replace(tzinfo=None),
                    )
                date = get_current_time()
                session = await session_service.create_session(
                    coach.id,
                    type=session_type,
                    date=date,
                    info_message_id=None,
                    voice_channel_id=None,
                    text_channel_id=None,
                    start_time=None,
                    end_time=None,
                    max_slots=max_slots,
                )

                overwrites = roles_manager.get_session_channels_overwrites()
                category = await guild.create_category(
                    f"Сессия {session.id}", overwrites=overwrites
                )
                text_ch = await guild.create_text_channel(
                    f"🚦・Очередь", category=category, overwrites=overwrites
                )
                logger.info(f"Session channels created")

                embed = SessionQueueEmbed(author, session.id)
                view = SessionQueueView(
                    session, session_service, discord_service, user_service
                )
                info_message = await text_ch.send(embed=embed, view=view)
                await info_message.pin()
                await session_service.update_session(
                    session.id, info_message_id=info_message.id, text_channel_id=text_ch.id
                )
                if ctx.interaction:
                    await ctx.interaction.response.send_message(
                        f"Сессия {session.id} создана. Коуч: {author.mention}. Количество слотов: {max_slots}"
                    )
                else:
                    await text_ch.send(
                        f"Сессия {session.id} создана. Коуч: {author.mention}. Количество слотов: {max_slots}"
                    )

                for channel in guild.text_channels:
                    if "логи-сессий" in channel.name:
                        await self.response_to_user(
                            ctx,
                            f"Сессия {session.id} создана. Коуч: {author.mention}. Количество слотов: {max_slots}",
                            channel,
                        )

        except discord.Forbidden:
            await self.response_to_user(
                ctx, "У меня нет прав на создание каналов в этом сервере.", channel
            )
        except Exception as e:
            await text_ch.delete()
            await category.delete()
            import traceback

            logger.error(f"Error creating session: {traceback.format_exc()}")
            await self.response_to_user(
                ctx,
                "Произошла ошибка при создании сессии. Пожалуйста, попробуйте позже.",
                channel,
            )

    @commands.hybrid_command(name="start")
    @commands.has_any_role(Roles.MOD, Roles.COACH_T1, Roles.COACH_T2, Roles.COACH_T3)
    async def start_session(self, ctx: commands.Context):
        logger.info(f"Starting session for {ctx.author.name}")
        try:
            async with get_service_factory(self.service_factory) as factory:
                user_service = await factory.get_service("user")
                session_service = await factory.get_service("session")
                discord_service = await factory.get_service("discord")
                guild = ctx.guild
                active_sessions = await session_service.get_active_sessions_by_coach_id(
                    ctx.author.id
                )
                coach = guild.get_member(ctx.author.id)
                if len(active_sessions) > 0:
                    await self.response_to_user(
                        ctx,
                        "У вас есть запущенная сессия. Пожалуйста, завершите её перед началом новой.",
                        ctx.channel,
                    )
                    return

                session = await session_service.get_last_created_session_by_coach_id(
                    ctx.author.id
                )
                if not session:
                    await self.response_to_user(
                        ctx,
                        "У вас нет созданных сессий. Пожалуйста, сначала создайте сессию.",
                        ctx.channel,
                    )
                    return

                if ctx.channel.id != session.text_channel_id:
                    await self.response_to_user(
                        ctx,
                        f"Вы не можете начать сессию в этом канале. Пожалуйста, используйте канал, где была создана очередь для сессии: {session.id}.",
                        ctx.channel,
                    )
                    return

                requests = await session_service.get_requests_by_session_id(session.id)
                if not requests:
                    await self.response_to_user(
                        ctx,
                        "У вас нет запросов в очередь. Перед тем как запускать распределение и сессию, дождитесь пока очередь заполнится.",
                        ctx.channel,
                    )
                    return

                requests = [
                    request
                    for request in requests
                    if request.status == SessionRequestStatus.PENDING.value
                ]
                user_ids = [request.user_id for request in requests]
                users = await user_service.get_users_by_ids(user_ids)
                scored_users = []
                for user in users:
                    score = ScoreCalculator.calculate_score(user, session.type)
                    scored_users.append({"user": user, "score": score})
                logger.info(f"scored_users: {scored_users}")
                sorted_users = sorted(scored_users, key=lambda x: x["score"], reverse=True)
                accepted_users = sorted_users[: session.max_slots]
                logger.info(f"sorted_users: {sorted_users}")
                accepted_users = [user["user"] for user in sorted_users[: session.max_slots]]
                accepted_users_ids = [user.id for user in accepted_users]
                logger.info(f"accepted_users: {accepted_users}")
                for request in requests:
                    if request.user_id in accepted_users_ids:
                        idx = accepted_users_ids.index(request.user_id)
                        await session_service.update_request(
                            request.id, status=SessionRequestStatus.ACCEPTED.value, slot_number=idx + 1
                        )
                    else:
                        await session_service.update_request_status(
                            request.id, SessionRequestStatus.REJECTED
                        )

                participants = [guild.get_member(user.id) for user in accepted_users]
                for i, participant in enumerate(participants):
                    if participant is None:
                        participants[i] = await self.bot.fetch_user(accepted_users[i].id)
                embed = SessionEmbed(participants, session.id, session.max_slots)
                view = SessionView(session, session_service, discord_service, user_service)
                session_message = await ctx.send(embed=embed, view=view)
                channel = guild.get_channel(session.text_channel_id)
                async for message in channel.history(limit=100):
                    if message.id == session.info_message_id:
                        await message.delete()
                        break
                await session_service.update_session(
                    session.id,
                    is_active=True,
                    session_message_id=session_message.id,
                    start_time=get_current_time(),
                )

                for category in guild.categories:
                    if category.name == f"Сессия {session.id}":
                        overwrites = RolesManager(guild).get_session_channels_overwrites()
                        voice_channel = await guild.create_voice_channel(
                            f"{coach.name}", category=category, overwrites=overwrites
                        )
                        await session_service.update_session(
                            session.id, voice_channel_id=voice_channel.id
                        )
                text_channel = None
                for channel in guild.text_channels:
                    if channel.id == session.text_channel_id:
                        text_channel = channel
                    if "логи-сессий" in channel.name:
                        await channel.send(
                            f"Сессия {session.id} началась. Коуч: {ctx.author.mention}. Участники: {', '.join([participant.mention for participant in participants])}"
                        )

                if not text_channel:
                    await self.response_to_user(
                        ctx,
                        "Канал не найден. Пожалуйста, создайте канал и попробуйте снова.",
                        ctx.channel,
                    )
                    return
                await text_channel.send(
                    f"Сессия {session.id} началась. Коуч: {ctx.author.mention}"
                )
        except Exception as e:
            import traceback

            logger.error(f"Error starting session: {traceback.format_exc()}")
            await self.response_to_user(
                ctx,
                "Произошла ошибка при начале сессии. Пожалуйста, попробуйте позже.",
                ctx.channel,
            )

    @commands.command(name="delete_channels")
    @commands.has_any_role(Roles.MOD)
    async def delete_channels(self, ctx: commands.Context):
        logger.info(f"Deleting channels for {ctx.guild.name}")
        async with get_service_factory(self.service_factory) as factory:
            session_service = await factory.get_service("session")
            try:
                guild = ctx.guild
                categories = guild.categories
                for category in categories:
                    if category.name.startswith("Сессия"):
                        session_id = int(category.name.split(" ")[1])
                        session = await session_service.get_session_by_id(session_id)
                        if not session:
                            continue
                        if session.is_active:
                            continue
                        for channel in category.channels:
                            await channel.delete()
                        await category.delete()
                await self.response_to_user(ctx, "Все каналы были удалены.", ctx.channel)
            except Exception as e:
                import traceback

                logger.error(f"Error deleting channels: {traceback.format_exc()}")
                await self.response_to_user(
                    ctx,
                    "Произошла ошибка при удалении каналов. Пожалуйста, попробуйте позже.",
                    ctx.channel,
                )

    async def delete_session_channels(self, guild: Guild, session: Session):
        categories = guild.categories
        if session.is_active:
            await guild.get_channel(session.text_channel_id).send(
                "Каналы не могут быть удалены, пока сессия активна. Завершите сессию /end"
            )
        for category in categories:
            if category.name == f"Сессия {session.id}" and not session.is_active:
                for channel in category.channels:
                    await channel.delete()
                await category.delete()

    async def prepare_session_report(self, guild: Guild, session: Session):
        try:
            session_service = await self.service_factory.get_service("session")
            user_service = await self.service_factory.get_service("user")
            session_data = await session_service.get_session_data(session.id)
            coach_db = await user_service.get_user(session.coach_id)
            session_data["coach_tier"] = coach_db.coach_tier
            coach = guild.get_member(session.coach_id)
            users_ids = [request.user_id for request in session_data["requests"]] + [
                session.coach_id
            ]
            users = await user_service.get_users_by_ids(users_ids)
            session_data["users"] = users
            participants = [
                guild.get_member(request.user_id)
                for request in session_data["requests"]
            ]
            # for request in session_data["requests"]:
            #     participant = await self.bot.fetch_user(request.user_id)
            #     participants.append(participant)

            report_service = ReportService(self.bot, coach, participants, session_data)
            report = await report_service.create_report()
            return report
        except Exception as e:
            logger.error(f"Error preparing session report: {e.with_traceback()}")
            return None

    @commands.hybrid_command(name="end")
    @commands.has_any_role(Roles.MOD, Roles.COACH_T1, Roles.COACH_T2, Roles.COACH_T3)
    async def end_session(self, ctx: commands.Context):
        logger.info(
            f"Attempting to end session for coach {ctx.author.name} in guild {ctx.guild.name}"
        )
        try:
            async with get_service_factory(self.service_factory) as factory:
                user_service = await factory.get_service("user")
                session_service = await factory.get_service("session")
            
                active_sessions = await session_service.get_active_sessions_by_coach_id(
                    ctx.author.id
                )
                logger.info(f"Active sessions: {active_sessions}")

                if not active_sessions:
                    await self.response_to_user(
                        ctx, "У вас нет активных сессий для завершения.", ctx.channel
                    )
                    return
                active_session = active_sessions[0]
                if active_session.text_channel_id != ctx.channel.id:
                    await self.response_to_user(
                        ctx,
                        "Вы не можете завершить сессию в этом канале. Пожалуйста, используйте канал, где была создана очередь для сессии.",
                        ctx.channel,
                    )
                    return
                text_channel = ctx.guild.get_channel(active_session.text_channel_id)
                end_session_view = EndSessionConfirmationView(
                    ctx.bot,
                    active_session,
                    self.service_factory,
                    ctx.interaction if ctx.interaction else None,
                )

                message_content = "Все ли участники были разобраны во время сессии?"
                if ctx.interaction:
                    await ctx.interaction.response.send_message(
                        message_content, view=end_session_view, ephemeral=True
                    )
                else:
                    if text_channel:
                        sent_message = await text_channel.send(
                            message_content, view=end_session_view, ephemeral=True
                        )
                        end_session_view.message = sent_message
                end_time = get_current_time()
                await session_service.update_session(
                    active_session.id, is_active=False, end_time=end_time
                )
                for ch in ctx.guild.text_channels:
                    if "логи-сессий" in ch.name:
                        duration = end_time - active_session.start_time
                        duration = f"{duration}".split(".")[0]
                        await ch.send(
                            f"Сессия {active_session.id} завершена. Коуч: {ctx.author.mention}. Продолжительность: {duration}"
                        )
                for ch in ctx.guild.voice_channels:
                    if active_session.voice_channel_id == ch.id:
                        await ch.delete()

                message_content = f"Сессия {active_session.id} завершена. Коуч: {ctx.author.mention}. Пожалуйста, оцените сессию."
                review_session_view = ReviewSessionView(
                    active_session, session_service, user_service
                )
                await text_channel.send(message_content, view=review_session_view)

                session_activities = await session_service.calculate_session_activities(
                    active_session.id
                )
                logger.info(f"Session activities: {session_activities}")

                for user_id, duration in session_activities.items():
                    if duration > 300 and user_id != active_session.coach_id:
                        try:
                            await self.bot.get_user(user_id).send(
                                message_content, view=review_session_view
                            )
                        except Exception as e:
                            import traceback
                            logger.error(f"Error sending review message: {traceback.format_exc()}")

                await text_channel.send(f"Сессия {active_session.id} завершена. Канал автоматически удалится через 10 минут.")
                await asyncio.sleep(self.SESSION_AUTO_DELETE_TIME)
                await self.delete_session_channels(ctx.guild, active_session)

                report = await self.prepare_session_report(ctx.guild, active_session)
                with open(report, "rb") as file:
                    await ctx.bot.get_user(config.ADMIN_ID).send(file=discord.File(file))
            # os.remove(report)

        except Exception as e:
            import traceback

            logger.error(f"Error ending session: {traceback.format_exc()}")
            error_message = (
                "Произошла ошибка при завершении сессии. Пожалуйста, попробуйте позже."
            )
            if ctx.interaction and not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(
                    error_message, ephemeral=True
                )
            elif ctx.interaction:
                await ctx.interaction.followup.send(error_message, ephemeral=True)
            else:
                await ctx.send(error_message)

    @commands.hybrid_command(name="queue")
    @commands.has_any_role(Roles.SUB)
    async def join_queue(self, ctx: commands.Context, session_id: int):
        logger.info(f"Joining queue for {ctx.author.name}")
        async with get_service_factory(self.service_factory) as factory:
            session_service = await factory.get_service("session")
            session = await session_service.get_session_by_id(session_id)
            if not session:
                await self.response_to_user(ctx, f"Сессия {session_id} не найдена.", ctx.channel)
                return
            if session.coach_id == ctx.author.id:
                await self.response_to_user(ctx, f"Вы не можете присоединиться к своей сессии.", ctx.channel)
                return
            if session and session.is_active:
                await self.response_to_user(ctx, f"Сессия {session_id} уже началась. Используйте /join, если есть свободные слоты.", ctx.channel)
                return
            request = await session_service.get_request_by_user_id(session.id, ctx.author.id)
            if not request:
                request = await session_service.create_request(session_id, ctx.author.id)
            else:
                await self.response_to_user(ctx, f"Вы уже в очереди на сессию {session.id}", ctx.channel)
                return
            guild = ctx.guild
            coach = await guild.fetch_member(session.coach_id)
            channel = await guild.fetch_channel(session.text_channel_id)
            queue_message = await channel.fetch_message(session.info_message_id)
            queue_embed = SessionQueueEmbed(coach, session.id)
            members = await session_service.get_queue_participants(guild, session.id)
            queue_embed.update_queue(members)
            await queue_message.edit(embed=queue_embed)
            await self.response_to_user(ctx, f"Вы успешно присоединились к очереди на сессию {session.id}", ctx.channel)

    @commands.hybrid_command(name="leave")
    @commands.has_any_role(Roles.SUB)
    async def leave_queue(self, ctx: commands.Context, session_id: int):
        logger.info(f"Leaving queue for {ctx.author.name}")
        async with get_service_factory(self.service_factory) as factory:
            session_service = await factory.get_service("session")
            session = await session_service.get_session_by_id(session_id)
            if not session:
                await self.response_to_user(ctx, f"Сессия {session_id} не найдена.", ctx.channel)
                return
            if session.coach_id == ctx.author.id:
                await self.response_to_user(ctx, f"Вы не можете покинуть очередь на свою сессию.", ctx.channel)
                return
            if session.is_active:
                await self.response_to_user(ctx, f"Сессия {session_id} уже началась, вы не можете покинуть очередь.", ctx.channel)
                return
            request = await session_service.get_request_by_user_id(session.id, ctx.author.id)
            if not request:
                await self.response_to_user(ctx, f"Вы не в очереди на сессию {session.id}", ctx.channel)
                return

            if request.status == SessionRequestStatus.PENDING.value:
                await session_service.delete_request(request.id)
            coach = await ctx.guild.fetch_member(session.coach_id)
            channel = await ctx.guild.fetch_channel(session.text_channel_id)
            queue_message = await channel.fetch_message(session.info_message_id)
            queue_embed = SessionQueueEmbed(coach, session.id)
            members = await session_service.get_queue_participants(ctx.guild, session.id)
            queue_embed.update_queue(members)
            await queue_message.edit(embed=queue_embed)

            await self.response_to_user(ctx, f"Вы успешно покинули очередь на сессию {session.id}", ctx.channel)

    @commands.hybrid_command(name="join")
    @commands.has_any_role(Roles.SUB)
    async def join_session(self, ctx: commands.Context, session_id: int):
        logger.info(f"Joining session {session_id}")
        async with get_service_factory(self.service_factory) as factory:
            session_service = await factory.get_service("session")
            session = await session_service.get_session_by_id(session_id)
            if not session:
                await self.response_to_user(ctx, f"Сессия {session_id} не найдена.", ctx.channel)
                return
            if session.coach_id == ctx.author.id:
                await self.response_to_user(ctx, f"Вы не можете присоединиться к своей сессии.", ctx.channel)
                return
            if not session.is_active:
                await self.response_to_user(ctx, f"Сессия {session_id} еще не началась или уже завершена.", ctx.channel)
                return

            accepted_requests = await session_service.get_accepted_requests(session.id)
            if len(accepted_requests) >= session.max_slots:
                await self.response_to_user(ctx, "Все слоты заняты.", ctx.channel)
                return

            request = await session_service.get_request_by_user_id(session.id, ctx.author.id)
            if request and request.status == SessionRequestStatus.ACCEPTED.value:
                await self.response_to_user(ctx, f"Вы уже присоединились к сессии {session.id}", ctx.channel)
                return

            if not request:
                request = await session_service.create_request(session.id, ctx.author.id)
            await session_service.update_request(request.id, status=SessionRequestStatus.ACCEPTED.value, slot_number=len(accepted_requests) + 1)

            requests = await session_service.get_accepted_requests(session.id)
            participants = [ctx.guild.get_member(request.user_id) for request in requests]
            embed = SessionEmbed(participants, session.id, session.max_slots)
            channel = await ctx.guild.fetch_channel(session.text_channel_id)
            message = await channel.fetch_message(session.session_message_id)
            await message.edit(embed=embed)
            await self.response_to_user(ctx, f"Вы присоединились к сессии {session.id}", ctx.channel)

    async def _remove_user_from_session(
        self, 
        session_service, 
        guild: Guild, 
        session: Session, 
        user_id: int
    ) -> tuple[bool, str]:
        """
        Приватный метод для удаления пользователя из сессии.
        
        Returns:
            tuple[bool, str]: (success, error_message)
        """
        try:
            # Получаем запрос пользователя
            request = await session_service.get_request_by_user_id(session.id, user_id)
            if not request or request.status != SessionRequestStatus.ACCEPTED.value:
                return False, "Пользователь не участвует в сессии"
            
            # Исключаем пользователя из сессии
            await session_service.update_request(
                request.id, 
                status=SessionRequestStatus.REJECTED.value, 
                slot_number=None
            )
            
            # Пересчитываем номера слотов для оставшихся участников
            await self._reorder_session_slots(session_service, session.id)
            
            # Обновляем embed с участниками
            await self._update_session_embed(session_service, guild, session)
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error removing user {user_id} from session {session.id}: {e}")
            return False, "Произошла ошибка при удалении пользователя из сессии"

    async def _reorder_session_slots(self, session_service, session_id: int):
        """Приватный метод для пересчёта номеров слотов в сессии."""
        accepted_requests = await session_service.get_accepted_requests(session_id)
        for idx, req in enumerate(accepted_requests):
            if req.slot_number != idx + 1:
                await session_service.update_request(req.id, slot_number=idx + 1)

    async def _update_session_embed(self, session_service, guild: Guild, session: Session):
        """Приватный метод для обновления embed сессии."""
        accepted_requests = await session_service.get_accepted_requests(session.id)
        participants = [guild.get_member(req.user_id) for req in accepted_requests]
        embed = SessionEmbed(participants, session.id, session.max_slots)
        
        channel = await guild.fetch_channel(session.text_channel_id)
        message = await channel.fetch_message(session.session_message_id)
        await message.edit(embed=embed)

    # @commands.hybrid_command(name="quit")
    # @commands.has_any_role(Roles.SUB)
    # async def quit_session(self, ctx: commands.Context, session_id: int):
    #     try:
    #         logger.info(f"Quitting session {session_id}")
    #         async with get_service_factory(self.service_factory) as factory:
    #             session_service = await factory.get_service("session")
                
    #             session = await session_service.get_session_by_id(session_id)
    #             if not session:
    #                 await self.response_to_user(ctx, f"Сессия {session_id} не найдена.", ctx.channel)
    #                 return
                
    #             if session.coach_id == ctx.author.id:
    #                 await self.response_to_user(ctx, f"Вы не можете покинуть свою сессию.", ctx.channel)
    #                 return
                
    #             # Используем общий метод
    #             success, error_msg = await self._remove_user_from_session(
    #                 session_service, ctx.guild, session, ctx.author.id
    #             )
                
    #             if success:
    #                 await self.response_to_user(ctx, f"Вы покинули сессию {session.id}", ctx.channel)
    #             else:
    #                 await self.response_to_user(ctx, error_msg, ctx.channel)
                    
    #     except Exception as e:
    #         logger.error(f"Error quitting session: {e}")
    #         await self.response_to_user(
    #             ctx,
    #             f"Произошла ошибка при покидании сессии {session_id}. Пожалуйста, попробуйте позже.",
    #             ctx.channel
    #         )

    @commands.hybrid_command(name="kick")
    @commands.has_any_role(Roles.MOD, Roles.COACH_T1, Roles.COACH_T2, Roles.COACH_T3)
    async def kick_from_session(self, ctx: commands.Context, user: Member):
        try:
            # Проверяем, что команда выполняется в правильном канале
            if not ctx.channel.category:
                await self.response_to_user(
                    ctx, 
                    "Эта команда должна выполняться в канале сессии.", 
                    ctx.channel
                )
                return
            
            # Регулярное выражение для проверки названия категории и извлечения ID сессии
            pattern = r"^Сессия (\d+)$"
            match = re.match(pattern, ctx.channel.category.name)
            
            if not match:
                await self.response_to_user(
                    ctx, 
                    "Эта команда может быть выполнена только в канале активной сессии.", 
                    ctx.channel
                )
                return
            
            session_id = int(match.group(1))
            logger.info(f"Kicking user {user.mention} from session {session_id}")
            
            async with get_service_factory(self.service_factory) as factory:
                session_service = await factory.get_service("session")
                
                session = await session_service.get_session_by_id(session_id)
                if not session:
                    await self.response_to_user(
                        ctx, 
                        f"Сессия {session_id} не найдена.", 
                        ctx.channel
                    )
                    return
                
                if not session.is_active:
                    await self.response_to_user(
                        ctx, 
                        f"Сессия {session_id} не активна.", 
                        ctx.channel
                    )
                    return
                
                # Используем общий метод
                success, error_msg = await self._remove_user_from_session(
                    session_service, ctx.guild, session, user.id
                )
                
                if success:
                    await self.response_to_user(
                        ctx, 
                        f"Пользователь {user.mention} исключен из сессии {session_id}.", 
                        ctx.channel
                    )
                else:
                    await self.response_to_user(ctx, error_msg, ctx.channel)
                    
        except Exception as e:
            logger.error(f"Error kicking user from session: {e}")
            await self.response_to_user(
                ctx, 
                f"Произошла ошибка при исключении пользователя из сессии. Пожалуйста, попробуйте позже.", 
                ctx.channel
            )

    @commands.hybrid_command(name="force_end")
    @commands.has_any_role(Roles.MOD, Roles.COACH_T1, Roles.COACH_T2, Roles.COACH_T3)
    async def force_end_session(self, ctx: commands.Context, session_id: int):
        logger.info(f"Force ending session {session_id}")
        async with get_service_factory(self.service_factory) as factory:
            session_service = await factory.get_service("session")
            session = await session_service.get_session_by_id(session_id)
            if session.coach_id != ctx.author.id:
                await self.response_to_user(
                    ctx,
                    "Вы не можете завершить эту сессию. Пожалуйста, используйте команду для завершения своей сессии.",
                    ctx.channel,
                )
                return
            await self.end_session(ctx)

    @commands.command(name="report")
    async def send_report(
        self, ctx: commands.Context, session_id: int = None, mode: str = "prod"
    ):
        logger.info(f"Sending report for session {session_id}")
        if ctx.author.id not in [config.ADMIN_ID, config.DEVELOPER_ID]:
            return
        async with get_service_factory(self.service_factory) as factory:
            user_service = await factory.get_service("user")
            session_service = await factory.get_service("session")
            if session_id:
                session = await session_service.get_session_by_id(session_id)
            else:
                sessions = await session_service.get_all_sessions()
                session = sessions[-1]
            session_data = await session_service.get_session_data(session.id)
            requests = session_data["requests"]
            try:
                coach = ctx.guild.get_member(session.coach_id)
            except Exception as e:
                logger.error(f"Error getting coach: {e.with_traceback()}")
            if not coach:
                await ctx.send(
                    "Коуч не найден. Пожалуйста, проверьте есть ли коуч в базе данных."
                )
                return
            coach_db = await user_service.get_user(coach.id)
            participants = []
            tasks = []
            for req in [
                req
                for req in requests
                if req.status == SessionRequestStatus.ACCEPTED.value
                or req.status == SessionRequestStatus.SKIPPED.value
            ]:
                participant = ctx.guild.get_member(req.user_id)
                if participant is None:
                    tasks.append(self.bot.fetch_user(req.user_id))
                if participant:
                    participants.append(participant)
            participants.extend(await asyncio.gather(*tasks))
            users_ids = [request.user_id for request in requests] + [session.coach_id]
            users = await user_service.get_users_by_ids(users_ids)
            logger.info(f"Users: {users}")
            session_data["users"] = users
            session_data["coach_tier"] = coach_db.coach_tier
            report_service = ReportService(self.bot, coach, participants, session_data)
            try:
                admin_id = config.ADMIN_ID if not config.DEBUG else config.DEVELOPER_ID
                admin_user = await ctx.bot.fetch_user(admin_id)
                logger.info(f"Admin user: {admin_user.name}")
                await admin_user.send("Начинаю создание отчёта...")
                report = await report_service.create_report()
                await admin_user.send(
                    content=f"Отчёт для сессии {session.id} создан",
                    file=discord.File(report),
                )
                #os.remove(report)
            except Exception as e:
                logger.error(f"Error sending report: {e.with_traceback()}")
                await ctx.send(
                    "Произошла ошибка при отправке отчёта. Пожалуйста, попробуйте позже."
                ) 

    @commands.command(name="review")
    @commands.has_any_role(Roles.MOD)
    async def review_session(self, ctx: commands.Context, session_id: int):
        try:
            async with get_service_factory(self.service_factory) as factory:
                session_service = await factory.get_service("session")
                user_service = await factory.get_service("user")
                session = await session_service.get_session_by_id(session_id)
                if not session:
                    await self.response_to_user(ctx, f"Сессия {session_id} не найдена.", ctx.channel)
                    return
                activities = await session_service.calculate_session_activities(session_id)
                if not activities:
                    await self.response_to_user(ctx, f"Сессия {session_id} не имеет активностей.", ctx.channel)
                    return
                logger.info(f"Activities: {activities}")
                review_session_view = ReviewSessionView(
                    session, session_service, user_service
                )
                coach = await ctx.guild.fetch_member(session.coach_id)
                message_content = f"Сессия {session.id} завершена. Коуч: {coach.mention}. Пожалуйста, оцените сессию."
                for user_id, duration in activities.items():
                    logger.info(f"User {user_id} has duration {duration}")
                    if user_id == config.DEVELOPER_ID:
                        member = await ctx.guild.fetch_member(user_id)
                        logger.info(f"Member: {member}")
                        await member.send(message_content, view=review_session_view)
                    if duration > 300 and user_id != session.coach_id:
                        try:
                            member = await ctx.guild.fetch_member(user_id)
                            logger.info(f"Sending review message to {member.mention}")
                            await member.send(
                                message_content, view=review_session_view
                            )
                            logger.info(f"Sent review message to {member.mention}")
                        except Exception as e:
                            logger.error(f"Error sending review message: {e.with_traceback()}")
                # await ctx.send(view=review_session_view)
        except Exception as e:
            logger.error(f"Error reviewing session: {e.with_traceback()}")
            await self.response_to_user(ctx, "Произошла ошибка при оценке сессии. Пожалуйста, попробуйте позже.", ctx.channel)
