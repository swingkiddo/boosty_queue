import discord

class Roles:
    MOD = "Moderator"
    SUB = "Subscriber"
    COACH_T1 = "Coach T1"
    COACH_T2 = "Coach T2"
    COACH_T3 = "Coach T3"

class RolesManager:
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.role_names = {
            Roles.COACH_T1: "Coach T1",
            Roles.COACH_T2: "Coach T2",
            Roles.COACH_T3: "Coach T3",
            Roles.SUB: "Subscriber",
            Roles.MOD: "Moderator",
        }
        self.roles = {
            Roles.COACH_T1: discord.utils.get(guild.roles, name=Roles.COACH_T1),
            Roles.COACH_T2: discord.utils.get(guild.roles, name=Roles.COACH_T2),
            Roles.COACH_T3: discord.utils.get(guild.roles, name=Roles.COACH_T3),
            Roles.SUB: discord.utils.get(guild.roles, name=Roles.SUB),
            Roles.MOD: discord.utils.get(guild.roles, name=Roles.MOD),
        }

    async def get_role(self, role_name: str) -> discord.Role:
        return self.roles[role_name]
    
    def get_session_channels_overwrites(self) -> dict[discord.Role, discord.PermissionOverwrite]:
        return {
            self.roles[Roles.COACH_T1]: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=True,
            ),
            self.roles[Roles.COACH_T2]: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=True,
            ),
            self.roles[Roles.COACH_T3]: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=True,
            ),
            self.roles[Roles.MOD]: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=True,
            ),
            self.roles[Roles.SUB]: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=False,
            ),
            self.guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
                connect=False,
                speak=False,
                read_messages=False,
                send_messages=False,
            )
        }

    async def get_session_admin_overwrites(self) -> dict[discord.Role, discord.PermissionOverwrite]:
        return {
            self.roles[Roles.COACH_T1]: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=True,
            ),
            self.roles[Roles.COACH_T2]: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=True,
            ),
            self.roles[Roles.COACH_T3]: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=True,
            ),
            self.roles[Roles.MOD]: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                read_messages=True,
                send_messages=True,
            ),
            self.guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
                connect=False,
                speak=False,
                read_messages=False,
                send_messages=False,
            )
        }



    async def create_role(self, role_name: str) -> discord.Role:
        role = await self.guild.create_role(name=role_name)
        self.roles[role_name] = role
        return role

    async def check_roles(self):
        for role_name in self.role_names:
            if not self.roles[role_name]:
                await self.create_role(self.role_names[role_name])

    async def get_role_by_name(self, role_name: str) -> discord.Role:
        return discord.utils.get(self.guild.roles, name=role_name)
