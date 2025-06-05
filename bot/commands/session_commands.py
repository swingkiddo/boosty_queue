import discord
from discord.ext import commands
from discord.ext.commands import Cog
from discord import User, Member, Guild

from config import config
from factory import ServiceFactory
from helpers import ScoreCalculator
from helpers.roles_manager import RolesManager
from logger import logger
from models.session import SessionRequestStatus, Session
from services.discord_service import Roles
from services import ReportService
from utils import get_current_time
from ui import (
    SessionQueueView,
    SessionQueueEmbed,
    SessionView,
    SessionEmbed,
    EndSessionConfirmationView,
    ReviewSessionView
)

import asyncio
import os


class SessionCommands(Cog):
    def __init__(self, bot: commands.Bot, service_factory: ServiceFactory):
        self.bot = bot
        self.service_factory = service_factory
        self.SESSION_AUTO_DELETE_TIME = 3600

    @commands.command(name='session')
    @commands.has_any_role(Roles.MOD, Roles.COACH)
    async def session(self, ctx: commands.Context):
        guild = ctx.guild
        member = await guild.fetch_member(427785500066054147)
        logger.info(f"member: {member}")
        ctx.author = member
        await self.create_session(ctx, "replay", 8)

    @commands.command(name='create')
    @commands.has_any_role(Roles.MOD, Roles.COACH)
    async def create_session(self, ctx: commands.Context, session_type: str, max_slots: int = 8):
        try:
            if session_type not in ["replay", "creative"]:
                await ctx.send("Неверный тип сессии. Пожалуйста, используйте 'replay' или 'creative'.")
                return
            author = ctx.author
            guild = ctx.guild
            roles_manager = RolesManager(guild)
            await roles_manager.check_roles()

            user_service = self.service_factory.get_service('user')
            session_service = self.service_factory.get_service('session')
            discord_service = self.service_factory.get_service('discord')


            coach = await user_service.get_user(author.id)
            if not coach:
                coach = await user_service.create_user(author.id, author.name, join_date=author.joined_at.replace(tzinfo=None))
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
                max_slots=max_slots
            )
            logger.info(f"Creating session with max_slots: {max_slots}")
            overwrites = roles_manager.get_session_channels_overwrites()
            category = await guild.create_category(f"Сессия {session.id}", overwrites=overwrites)
            voice_ch = await guild.create_voice_channel(f"{author.name}", category=category, overwrites=overwrites)
            text_ch = await guild.create_text_channel(f"Очередь", category=category, overwrites=overwrites)
            logger.info(f"Session channels created")

            embed = SessionQueueEmbed(author, session.id)
            view = SessionQueueView(session, session_service, discord_service, user_service)
            info_message = await text_ch.send(embed=embed, view=view)
            await info_message.pin()
            await session_service.update_session(session.id, info_message_id=info_message.id, voice_channel_id=voice_ch.id, text_channel_id=text_ch.id)

        except discord.Forbidden:
            await ctx.send("У меня нет прав на создание каналов в этом сервере.")
        except Exception as e:
            await text_ch.delete()
            await voice_ch.delete()
            await category.delete()
            import traceback
            logger.error(f"Error creating session: {traceback.format_exc()}")
            await ctx.send("Произошла ошибка при создании сессии. Пожалуйста, попробуйте позже.")

    @commands.command(name="start")
    @commands.has_any_role(Roles.MOD, Roles.COACH)
    async def start_session(self, ctx: commands.Context):
        logger.info(f"Starting session for {ctx.guild.name}")
        try:
            user_service, session_service, discord_service = self.service_factory.get_services()
            guild = ctx.guild
            active_sessions = await session_service.get_active_sessions_by_coach_id(ctx.author.id)
            if len(active_sessions) > 0:
                await ctx.send("У вас есть запущенная сессия. Пожалуйста, завершите её перед началом новой.")
                return
            session = await session_service.get_last_created_session_by_coach_id(ctx.author.id)
            if not session:
                await ctx.send("У вас нет созданных сессий. Пожалуйста, сначала создайте сессию.")
                return
            requests = await session_service.get_requests_by_session_id(session.id)
            if not requests:
                await ctx.send("У вас нет запросов в очередь. Перед тем как запускать распределение и сессию, дождитесь пока очередь заполнится.")
                return
            requests = [request for request in requests if request.status == SessionRequestStatus.PENDING.value]
            user_ids = [request.user_id for request in requests]
            users = await user_service.get_users_by_ids(user_ids)
            
            scored_users = []
            for user in users:
                score = ScoreCalculator.calculate_score(user, session.type)
                scored_users.append({"user": user, "score": score})
            sorted_users = sorted(scored_users, key=lambda x: x["score"], reverse=True)
            logger.info(f"sorted_users: {sorted_users}")
            accepted_users = sorted_users[:session.max_slots]
            accepted_users = [user["user"] for user in accepted_users]
            for request in requests:
                if request.user_id in [user.id for user in accepted_users]:
                    await session_service.update_request_status(request.id, SessionRequestStatus.ACCEPTED)
                else:
                    await session_service.update_request_status(request.id, SessionRequestStatus.REJECTED)
            class TestUser:
                def __init__(self, id: int, mention: str):
                    self.id = id
                    self.mention = mention
            participants = [guild.get_member(user.id) for user in accepted_users]
            for i, participant in enumerate(participants):
                if participant is None:
                    _user = accepted_users[i]
                    participants[i] = TestUser(_user.id, _user.nickname)
            logger.info(f"participants: {participants}")
            embed = SessionEmbed(participants, session.id, session.max_slots)
            view = SessionView(session, session_service, discord_service, user_service)
            session_message = await ctx.send(embed=embed, view=view)
            await session_service.update_session(session.id, is_active=True, session_message_id=session_message.id, start_time=get_current_time())

            text_channel = None
            for channel in guild.text_channels:
                if channel.id == session.text_channel_id:
                    text_channel = channel
            if not text_channel:
                await ctx.send("Канал не найден. Пожалуйста, создайте канал и попробуйте снова.")
                return
            await text_channel.send(f"Сессия {session.id} началась. Коуч: {ctx.author.mention}")
        except Exception as e:
            import traceback
            logger.error(f"Error starting session: {traceback.format_exc()}")
            await ctx.send("Произошла ошибка при начале сессии. Пожалуйста, попробуйте позже.")

    @commands.command(name='delete_channels')
    @commands.has_any_role(Roles.MOD)
    async def delete_channels(self, ctx: commands.Context):
        logger.info(f"Deleting channels for {ctx.guild.name}")
        try:
            bot = ctx.bot
            guild = ctx.guild
            categories = guild.categories
            for category in categories:
                if category.name.startswith('Сессия'):
                    for channel in category.channels:
                        await channel.delete()
                        bot.clear_channel_state(channel.id)
                    await category.delete()
            await ctx.send("Все каналы были удалены.")
        except Exception as e:
            import traceback
            logger.error(f"Error deleting channels: {traceback.format_exc()}")
            await ctx.send("Произошла ошибка при удалении каналов. Пожалуйста, попробуйте позже.")

    async def delete_session_channels(self, guild: Guild, session: Session):
        categories = guild.categories
        for category in categories:
            if category.name == f"Сессия {session.id}":
                for channel in category.channels:
                    await channel.delete()
                await category.delete()

    async def prepare_session_report(self, guild: Guild, session: Session):
        session_service = self.service_factory.get_service('session')
        session_data = await session_service.get_session_data(session.id)
        coach = guild.get_member(session.coach_id)
        participants = [guild.get_member(request.user_id) for request in session_data["requests"]]
        report_service = ReportService(self.bot, coach, participants, session_data)
        report = await report_service.create_report()
        return report

    @commands.command(name="end")
    @commands.has_any_role(Roles.MOD, Roles.COACH)
    async def end_session(self, ctx: commands.Context):
        logger.info(f"Attempting to end session for coach {ctx.author.name} in guild {ctx.guild.name}")
        try:
            user_service = self.service_factory.get_service('user')
            session_service = self.service_factory.get_service('session')
            active_sessions = await session_service.get_active_sessions_by_coach_id(ctx.author.id)
            logger.info(f"Active sessions: {active_sessions}")  

            if not active_sessions:
                await ctx.send("У вас нет активных сессий для завершения.", ephemeral=True)
                return
            active_session = active_sessions[0]
            end_session_view = EndSessionConfirmationView(ctx.bot, active_session, self.service_factory, ctx.interaction if ctx.interaction else None)
            
            message_content = "Все ли участники были разобраны во время сессии?"
            if ctx.interaction:
                # Для слеш-команд используем response.send_message
                await ctx.interaction.response.send_message(message_content, view=end_session_view, ephemeral=True)
                # Сохраняем сообщение для View, чтобы оно могло себя редактировать
                # view.message = await ctx.interaction.original_response() # Это нужно если мы не используем followup/edit_original_response в View напрямую
            else:
                # Для команд с префиксом
                sent_message = await ctx.bot.get_user(active_session.coach_id).send(message_content, view=end_session_view)
                end_session_view.message = sent_message # View сможет редактировать это сообщение

            message_content = "Пожалуйста, оцените сессию."
            review_session_view = ReviewSessionView(active_session, session_service, user_service)
            channel = ctx.guild.get_channel(active_session.text_channel_id)
            if channel:
                await channel.send(message_content, view=review_session_view)
            await session_service.update_session(active_session.id, is_active=False, end_time=get_current_time())

            await ctx.send("Сессия завершена. Каналы автоматически будут удалены через 1 час.")
            await asyncio.sleep(self.SESSION_AUTO_DELETE_TIME)
            await self.delete_session_channels(ctx.guild, active_session)

            report = await self.prepare_session_report(ctx.guild, active_session)
            with open(report, "rb") as file:
                await ctx.bot.get_user(config.ADMIN_ID).send(file=discord.File(file))
            os.remove(report)

        except Exception as e:
            import traceback
            logger.error(f"Error ending session: {traceback.format_exc()}")
            error_message = "Произошла ошибка при завершении сессии. Пожалуйста, попробуйте позже."
            if ctx.interaction and not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(error_message, ephemeral=True)
            elif ctx.interaction:
                await ctx.interaction.followup.send(error_message, ephemeral=True)
            else:
                await ctx.send(error_message)

    @commands.command(name="report")
    async def send_report(self, ctx: commands.Context, session_id: int = None):
        logger.info(f"Sending report for session {session_id}")
        if ctx.author.id != config.ADMIN_ID:
            return

        session_service = self.service_factory.get_service('session')
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
            await ctx.send("Коуч не найден. Пожалуйста, проверьте есть ли коуч в базе данных.")
            return
        participants = []
        tasks = []
        for req in [req for req in requests if req.status == SessionRequestStatus.ACCEPTED.value or req.status == SessionRequestStatus.SKIPPED.value]:
            participant = ctx.guild.get_member(req.user_id)
            if participant is None:
                tasks.append(self.bot.fetch_user(req.user_id))
            if participant:
                participants.append(participant)
        participants.extend(await asyncio.gather(*tasks))
        report_service = ReportService(self.bot, coach, participants, session_data)
        try:
            await ctx.bot.get_user(config.ADMIN_ID).send("Начинаю создание отчёта...")
            report = await report_service.create_report()
            await ctx.bot.get_user(config.ADMIN_ID).send(content=f"Отчёт для сессии {session.id} создан", file=discord.File(report))
            os.remove(report)
        except Exception as e:
            logger.error(f"Error sending report: {e.with_traceback()}")
            await ctx.send("Произошла ошибка при отправке отчёта. Пожалуйста, попробуйте позже.")

    @commands.command(name="report_activity")
    async def report_activity(self, ctx: commands.Context, session_id: int = None):
        import pandas as pd
        from random import randint
        from datetime import datetime, timedelta
        logger.info(f"Reporting activity for session {session_id}")
        if ctx.author.id != config.ADMIN_ID:
            return
        user_service = self.service_factory.get_service('user')
        session_service = self.service_factory.get_service('session')
        activities = await session_service.get_session_activities(session_id)
        activities = [activity.to_dict() for activity in activities]
        logger.info(f"Activities: {activities}")
        activities_df = pd.DataFrame(activities)
        if activities_df.empty:
            await ctx.send("Нет данных об активности для этой сессии.")
            return
        activities_df['join_time'] = pd.to_datetime(activities_df['join_time'])
        activities_df['leave_time'] = pd.to_datetime(activities_df['leave_time'])
        activities_df['duration'] = activities_df['leave_time'] - activities_df['join_time']
        activities_df['duration'] = activities_df['duration'].dt.total_seconds()
        
        # Группировка по user_id и суммирование duration
        user_activity_summary = activities_df.groupby('user_id')['duration'].sum().reset_index()
        user_activity_summary.rename(columns={'duration': 'total_duration_seconds'}, inplace=True)

        # Получение уникальных user_id
        unique_users = activities_df['user_id'].unique()

        logger.info(f"User Activity Summary: \n{user_activity_summary}")
        logger.info(f"Unique Users: {unique_users.tolist()}")

        response_message = "Отчет по активности:\n"
        response_message += "Суммарное время нахождения в канале для каждого пользователя:\n"
        for index, row in user_activity_summary.iterrows():
            response_message += f"User ID: {row['user_id']}, Total Duration: {row['total_duration_seconds']:.2f} seconds\n"
        
        response_message += "\nУникальные пользователи в сессии:\n"
        response_message += ", ".join(map(str, unique_users.tolist()))

        # Отправка длинных сообщений частями, если необходимо
        if len(response_message) > 2000:
            parts = [response_message[i:i+2000] for i in range(0, len(response_message), 2000)]
            for part in parts:
                await ctx.send(part)
        else:
            await ctx.send(response_message)
