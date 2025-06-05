from datetime import datetime
from discord import Intents, Member, VoiceState
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from factory import ServiceFactory
from commands import SessionCommands
from logger import logger
from database.db import init_db
from helpers import Roles, RolesManager

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

    async def on_ready(self):
        guild
        logger.info(f"Logged in as {self.user}")
        for guild in self.guilds:
            if guild.name.startswith("At0m"):
                self.guild = guild
                break

        if self.guild:
            channels = [ch.name for ch in self.guild.channels]
            roles_manager = RolesManager(self.guild)
            await roles_manager.check_roles()
            admin_overwrites = await roles_manager.get_session_admin_overwrites()
            if "Запуск сессии" not in channels:
                await self.guild.create_text_channel("Запуск сессии", overwrites=admin_overwrites)

            if "Логи сессий" not in channels:
                await self.guild.create_text_channel("Логи сессий", overwrites=admin_overwrites)


    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        logger.info(f"Voice state update: {member} {before} {after}")
        session_service = self.service_factory.get_service('session')

        if after.channel is not None:
            if member.bot:
                return
            voice_ch = after.channel
            category = voice_ch.category
            if category and category.name.startswith("Сессия"):
                session_id = int(category.name.split(" ")[1])
                await session_service.create_user_session_activity(session_id, member.id, join_time=datetime.now())
                logger.info(f"User {member.name} joined session {session_id}")

                if not voice_ch.id in self.channel_states:
                    self.channel_states[voice_ch.id] = {
                        'current_users': [member.name],
                        'unique_users': set([member]),
                    }
                else:
                    self.channel_states[voice_ch.id]['current_users'].append(member.name)
                    self.channel_states[voice_ch.id]['unique_users'].add(member)

        if before.channel is not None:
            if before.channel.id in self.channel_states:
                category = before.channel.category
                if category and category.name.startswith("Сессия"):
                    session_id = int(category.name.split(" ")[1])
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

    async def on_ready(self):
        from random import randint
        logger.info(f"Logged in as {self.user}")
        # user_service = self.service_factory.get_service('user')
        # guilds = self.guilds
        # guild = None
        # for g in guilds:
        #     logger.info(f"Guild: {g.name}")
        #     if g.name.startswith("At0m"):
        #         guild = g
        #         break
        # logger.info(f"Guild: {guild}")
        # if guild:
        #     users = guild.members
        #     try:
        #         for user in users:
        #             roles = [role.name for role in user.roles]
        #             if Roles.SUB in roles or Roles.COACH in roles:
        #                 logger.info(f"User: {user.name} {user.id}")
        #                 await user_service.create_user(
        #                     user.id,
        #                     user.name,
        #                     join_date=user.joined_at.replace(tzinfo=None),
        #                     total_replay_sessions=randint(0, 40),
        #                     total_creative_sessions=randint(0, 40)
        #                 )
        #     except Exception as e:
        #         logger.error(f"Error creating user: {e}")
        #         import traceback
        #         logger.error(traceback.format_exc())

    async def load_commands(self):
        try: 
            session_commands = SessionCommands(self, self.service_factory)
            await self.add_cog(session_commands)
            logger.info("Commands loaded")
        except Exception as e:
            logger.error(f"Error loading commands: {e}")
            import traceback
            logger.error(traceback.format_exc())
