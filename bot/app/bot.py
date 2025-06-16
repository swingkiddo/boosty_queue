from datetime import datetime
from discord import Intents, Member, VoiceState, VoiceChannel
from discord.ext import commands

from factory import ServiceFactory
from commands import SessionCommands, UserCommands
from logger import logger
from database.db import init_db
from helpers import Roles, RolesManager
import enum


class Channels(enum.Enum):
    SESSION_START_CHANNEL = "🚀・запуск-сессии"
    SESSION_LOGS_CHANNEL = "📃・логи-сессий"


class BoostyQueueBot(commands.Bot):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        super().__init__(command_prefix="$", intents=intents)
        self.service_factory = ServiceFactory()
        self.service_factory.init_discord_service(self)
        self.channel_states = {}
        self.guild = None

    async def setup_hook(self):
        await init_db()
        await self.load_commands()

    def is_session_channel(self, channel: VoiceChannel):
        return channel.category and channel.category.name.startswith("Сессия")

    async def handle_voice_channel_join(self, member: Member, voice_ch: VoiceChannel):
        session_service = await self.service_factory.get_service("session")
        session_id = int(voice_ch.category.name.split(" ")[1])
        await session_service.create_user_session_activity(
            session_id, member.id, join_time=datetime.now()
        )
        logger.info(f"User {member.name} joined session {session_id}")

    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        if member.bot:
            return

        session_service = await self.service_factory.get_service("session")
        logger.info(
            f"on_voice_state_update: {member.name} {before.channel} {after.channel}"
        )
        if after.channel and self.is_session_channel(after.channel):
            session_id = int(after.channel.category.name.split(" ")[1])
            logger.info(f"session_id: {session_id}")
            active_activities = await session_service.get_active_user_activities(
                session_id, member.id
            )
            if not active_activities:
                await session_service.create_user_session_activity(
                    session_id, member.id, join_time=datetime.now()
                )
                logger.info(f"User {member.name} joined session {session_id}")

        if before.channel and self.is_session_channel(before.channel):
            session_id = int(before.channel.category.name.split(" ")[1])
            logger.info(f"session_id: {session_id}")
            active_activities = await session_service.get_active_user_activities(
                session_id, member.id
            )
            for activity in active_activities:
                await session_service.complete_user_activity(
                    activity.id, datetime.now()
                )

            logger.info(f"User {member.name} left session {session_id}")

        logger.info(f"Channel states: {self.channel_states}")

    def clear_channel_state(self, channel_id: int):
        if channel_id in self.channel_states:
            del self.channel_states[channel_id]

    def get_channel_state(self, channel_id: int):
        if channel_id in self.channel_states:
            return self.channel_states[channel_id]
        return None

    async def on_member_update(self, before: Member, after: Member):
        if before.roles != after.roles:
            logger.info(
                f"Member {after.name} updated roles: {before.roles} -> {after.roles}"
            )
            gained_roles = [
                role.name for role in after.roles if role not in before.roles
            ]
            lost_roles = [role.name for role in before.roles if role not in after.roles]
            user_service = await self.service_factory.get_service("user")
            user = await user_service.get_user(after.id)
            if not user:
                user = await user_service.create_user(
                    after.id, after.name, join_date=after.joined_at.replace(tzinfo=None)
                )
            if "Coach T1" in gained_roles:
                await user_service.update_user(user.id, coach_tier="Coach T1")
            elif "Coach T2" in gained_roles:
                await user_service.update_user(user.id, coach_tier="Coach T2")
            elif "Coach T3" in gained_roles:
                await user_service.update_user(user.id, coach_tier="Coach T3")

            if "Coach T1" in lost_roles:
                await user_service.update_user(user.id, coach_tier=None)
            elif "Coach T2" in lost_roles:
                await user_service.update_user(user.id, coach_tier=None)
            elif "Coach T3" in lost_roles:
                await user_service.update_user(user.id, coach_tier=None)

    async def on_ready(self):
        from random import randint

        logger.info(f"Guilds: {self.guilds}")
        try:
            for guild in self.guilds:
                logger.info(f"Guild: {guild.name}")
                if guild.name.startswith("At0m") or guild.name.startswith("test"):
                    self.guild = guild
                    break

            if self.guild:
                synced = await self.tree.sync()
                logger.info(f"Synced commands: {synced}")
                roles_manager = RolesManager(self.guild)
                await roles_manager.check_roles()

                admin_overwrites = await roles_manager.get_session_admin_overwrites()
                categories = [ch for ch in self.guild.categories if ch.name == "Сессии"]
                channels = [ch.name for ch in self.guild.channels]
                if len(categories) == 0:
                    category = await self.guild.create_category("Сессии")
                    logger.info(f"Created category: {category.name}")
                else:
                    category = categories[0]
                if Channels.SESSION_START_CHANNEL.value not in channels:
                    logger.info(
                        f"Creating session start channel: {Channels.SESSION_START_CHANNEL.value}"
                    )
                    await self.guild.create_text_channel(
                        Channels.SESSION_START_CHANNEL.value,
                        category=category,
                        overwrites=admin_overwrites,
                    )
                if Channels.SESSION_LOGS_CHANNEL.value not in channels:
                    logger.info(
                        f"Creating session logs channel: {Channels.SESSION_LOGS_CHANNEL.value}"
                    )
                    await self.guild.create_text_channel(
                        Channels.SESSION_LOGS_CHANNEL.value,
                        category=category,
                        overwrites=admin_overwrites,
                    )

                user_service = await self.service_factory.get_service("user")
                for member in self.guild.members:
                    roles = [role.name for role in member.roles]
                    if member.bot:
                        continue
                    if Roles.SUB in roles:
                        user = await user_service.get_user(member.id)
                        join_date = member.joined_at.replace(tzinfo=None)
                        if not user:
                            await user_service.create_user(
                                member.id, member.name, join_date=join_date
                            )
                    if (
                        Roles.COACH_T1 in roles
                        or Roles.COACH_T2 in roles
                        or Roles.COACH_T3 in roles
                    ):
                        coach_tier = (
                            Roles.COACH_T1
                            if Roles.COACH_T1 in roles
                            else (
                                Roles.COACH_T2
                                if Roles.COACH_T2 in roles
                                else Roles.COACH_T3
                            )
                        )
                        user = await user_service.get_user(member.id)
                        if not user:
                            await user_service.create_user(
                                member.id,
                                member.name,
                                join_date=join_date,
                                coach_tier=coach_tier,
                            )
                        else:
                            await user_service.update_user(
                                member.id, coach_tier=coach_tier
                            )
                # session_service = await self.service_factory.get_service('session')
                # session_id = 4
                # session = await session_service.get_session_by_id(session_id)
                # logger.info(f"Getting session activities for session {session_id}")
                # activities = await session_service.get_session_activities(session_id)
                # logger.info(f"Activities: {activities}")
                # from ui.session_view import ReviewSessionView

                # review_session_view = ReviewSessionView(
                #     session, session_service, user_service
                # )
                # coach = self.guild.get_member(session.coach_id)
                # text = f"Сессия {session_id} завершена. Коуч: {coach.mention}. Оцени сессию."

                # for user_id, duration in activities.items():
                #     member = self.guild.get_member(user_id)
                #     logger.info(f"Member: {member.name} {duration}")
                #     if member.name == "koochamala":
                #         await member.send(text, view=review_session_view)
                #     if duration > 300 and member.id != session.coach_id:
                #         if member:
                #             await member.send(text, view=review_session_view)
                #             logger.info(f"Sent review session view to {member.name}")

        except Exception as e:
            logger.error(f"Error on_ready: {e}")
            import traceback

            logger.error(traceback.format_exc())

    async def load_commands(self):
        try:
            session_commands = SessionCommands(self, self.service_factory)
            await self.add_cog(session_commands)
            user_commands = UserCommands(self, self.service_factory)
            await self.add_cog(user_commands)
            logger.info("Commands loaded")
        except Exception as e:
            logger.error(f"Error loading commands: {e}")
            import traceback

            logger.error(traceback.format_exc())
