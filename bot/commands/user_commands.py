from discord.ext import commands
from discord.ext.commands import Cog
from factory import ServiceFactory, get_service_factory

class UserCommands(Cog):
    def __init__(self, bot: commands.Bot, service_factory: ServiceFactory):
        self.bot = bot
        self.service_factory = service_factory

    @commands.hybrid_command(name="stats")
    async def stats(self, ctx: commands.Context):
        async with get_service_factory(self.service_factory) as factory:
            user_service = await factory.get_service("user")
            user = await user_service.get_user(ctx.author.id)
            if not user:
                await ctx.send("You are not registered in the bot")
                return
            stats = f"Сессии разборов: {user.total_replay_sessions}\nСес    ии пг: {user.total_creative_sessions}"
            if ctx.interaction:
                await ctx.interaction.response.send_message(stats, ephemeral=True)
