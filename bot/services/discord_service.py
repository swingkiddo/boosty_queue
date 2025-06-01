import discord
from discord.ext import commands
from logger import logger
from models.session import Session
from helpers import Roles


class DiscordService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_message(self, channel_id: int, message: str) -> discord.Message:
        channel = self.bot.get_channel(channel_id)
        return await channel.send(message)

    async def delete_message(self, channel_id: int, message_id: int):
        channel = self.bot.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        await message.delete()

    async def create_voice_channel(self, guild: discord.Guild, channel_name: str, category: discord.CategoryChannel = None, overwrites: dict[discord.Role, discord.PermissionOverwrite] = None) -> discord.VoiceChannel:
        if overwrites is None:
            overwrites = {}
        return await guild.create_voice_channel(channel_name, category=category, overwrites=overwrites)

    async def delete_voice_channel(self, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        await channel.delete()

    async def create_category(self, guild: discord.Guild, category_name: str, overwrites: dict[discord.Role, discord.PermissionOverwrite] = None) -> discord.CategoryChannel:
        if overwrites is None:
            overwrites = {}
        return await guild.create_category(category_name, overwrites=overwrites)

    async def delete_category(self, category_id: int):
        category = self.bot.get_channel(category_id)
        await category.delete()

    async def create_text_channel(self, guild: discord.Guild, channel_name: str, category: discord.CategoryChannel = None, overwrites: dict[discord.Role, discord.PermissionOverwrite] = None) -> discord.TextChannel:
        if overwrites is None:
            overwrites = {}
        return await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

    async def delete_text_channel(self, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        await channel.delete()

    async def create_role(self, guild: discord.Guild, role_name: str) -> discord.Role:
        return await guild.create_role(name=role_name)
    
    async def delete_role(self, role_id: int):
        role = self.bot.get_role(role_id)
        await role.delete()

    async def add_role_to_user(self, user_id: int, role_id: int):
        user = self.bot.get_user(user_id)
        role = self.bot.get_role(role_id)
        await user.add_roles(role)

    async def remove_role_from_user(self, user: discord.Member, role: discord.Role):
        await self.bot.remove_roles(user, role)

    async def get_role_by_name(self, guild: discord.Guild, role_name: str) -> discord.Role:
        return discord.utils.get(guild.roles, name=role_name)

    async def get_roles(self, guild: discord.Guild) -> list[discord.Role]:
        return guild.roles

    async def get_member(self, guild: discord.Guild, member_id: int) -> discord.Member:
        return guild.get_member(member_id)

    async def create_session_channels(self, guild: discord.Guild, coach: discord.Member, session: Session):
        coach_role = await self.get_role_by_name(guild, Roles.COACH)
        sub_role = await self.get_role_by_name(guild, Roles.SUB)
        mod_role = await self.get_role_by_name(guild, Roles.MOD)
        overwrites = {
            coach_role: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=True,
            ),
            sub_role: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=False,
            ),
            mod_role: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=True,
            ),
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
                connect=False
            )
        }
        session_category = await self.create_category(guild, f"Сессия {session.id} {coach.name}", overwrites=overwrites)
        session_voice_channel = await self.create_voice_channel(guild, f"Сессия {session.id} {coach.name}", session_category, overwrites=overwrites)
        session_text_channel = await self.create_text_channel(guild, f"Сессия {session.id} {coach.name}", session_category, overwrites=overwrites)
        return session_category, session_voice_channel, session_text_channel