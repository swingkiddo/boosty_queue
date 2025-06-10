from datetime import datetime
from discord import Intents, Member, VoiceState, VoiceChannel
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

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
    def __init__(self, session: AsyncSession):
        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        super().__init__(command_prefix='$', intents=intents)
        self.session = session
        self.service_factory = ServiceFactory(self.session)
        self.service_factory.init_discord_service(self)
        self.channel_states = {}
        self.guild = None

    async def setup_hook(self):
        await init_db()
        await self.load_commands()

    def is_session_channel(self, channel: VoiceChannel):
        return channel.category and channel.category.name.startswith("Сессия")

    async def handle_voice_channel_join(self, member: Member, voice_ch: VoiceChannel):
        session_service = self.service_factory.get_service('session')
        session_id = int(voice_ch.category.name.split(" ")[1])
        await session_service.create_user_session_activity(session_id, member.id, join_time=datetime.now())
        logger.info(f"User {member.name} joined session {session_id}")
        

    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        logger.info(f"Voice state update: {member} {before} {after}")
        session_service = self.service_factory.get_service('session')

        if after.channel is not None:
            if member.bot:
                return
            voice_ch = after.channel
            if self.is_session_channel(voice_ch):
                session_id = int(voice_ch.category.name.split(" ")[1])
                await session_service.create_user_session_activity(session_id, member.id, join_time=datetime.now())
                logger.info(f"User {member.name} joined session {session_id}")

                if not voice_ch.id in self.channel_states:
                    self.channel_states[voice_ch.id] = {
                        'current_users': [member.name],
                        'unique_users': {member.id: member}
                    }
                else:
                    self.channel_states[voice_ch.id]['current_users'].append(member.name)
                    self.channel_states[voice_ch.id]['unique_users'][member.id] = member

        if before.channel is not None and before.channel.id in self.channel_states:
            if self.is_session_channel(before.channel):
                session_id = int(before.channel.category.name.split(" ")[1])
                user_activities = await session_service.get_user_session_activities(session_id, member.id)
                activity = user_activities[0]
                await session_service.update_user_session_activity(activity.id, leave_time=datetime.now())
                logger.info(f"User {member.name} left session {session_id}")

            logger.info(f"Removing user: {member.name} from channel: {before.channel.name}")
            self.channel_states[before.channel.id]['current_users'].remove(member.name)

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
            logger.info(f"Member {after.name} updated roles: {before.roles} -> {after.roles}")
            gained_roles = [role.name for role in after.roles if role not in before.roles]
            logger.info(f"Gained roles: {gained_roles}")
            lost_roles = [role.name for role in before.roles if role not in after.roles]
            logger.info(f"Lost roles: {lost_roles}")
            logger.info("getting user_service")
            user_service = self.service_factory.get_service('user')
            logger.info(f"user_service: {user_service}")
            user = await user_service.get_user(after.id)
            if not user:
                user = await user_service.create_user(after.id, after.name, join_date=after.joined_at.replace(tzinfo=None))
            if "Coach T1" in gained_roles:
                logger.info("updating user coach_tier to Coach_T1")
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
                    logger.info(f"Creating session start channel: {Channels.SESSION_START_CHANNEL.value}")
                    await self.guild.create_text_channel(Channels.SESSION_START_CHANNEL.value, category=category, overwrites=admin_overwrites)
                if Channels.SESSION_LOGS_CHANNEL.value not in channels:
                    logger.info(f"Creating session logs channel: {Channels.SESSION_LOGS_CHANNEL.value}")
                    await self.guild.create_text_channel(Channels.SESSION_LOGS_CHANNEL.value, category=category, overwrites=admin_overwrites)

                user_service = self.service_factory.get_service('user')
                for member in self.guild.members:
                    if member.bot:
                        continue
                    if Roles.SUB in [role.name for role in member.roles]:
                        user = await user_service.get_user(member.id)
                        join_date = member.joined_at.replace(tzinfo=None)
                        if not user:
                                await user_service.create_user(member.id, member.name, join_date=join_date)

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
