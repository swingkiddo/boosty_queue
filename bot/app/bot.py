from discord import Intents
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from factory import ServiceFactory
from commands import SessionCommands
from logger import logger
from database.db import init_db
from helpers import Roles

class BoostyQueueBot(commands.Bot):
    def __init__(self, session: AsyncSession):
        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='$', intents=intents)
        self.session = session
        self.service_factory = ServiceFactory(self.session)
        self.service_factory.init_discord_service(self)

    async def setup_hook(self):
        await init_db()
        await self.load_commands()

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
