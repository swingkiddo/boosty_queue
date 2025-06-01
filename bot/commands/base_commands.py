from discord.ext import commands
from logger import logger

class BaseCommands(commands.Cog):
    """Базовый класс для всех команд с общей функциональностью"""

    def __init__(self):
        pass

    # Метод, который вызывается при добавлении Cog'а в бота
    async def cog_load(self) -> None:
        """
        Вызывается при загрузке Cog'а.
        Можно переопределить в дочерних классах для дополнительной инициализации.
        """
        pass

    # # Метод для синхронизации слэш-команд с сервером
    # async def sync_commands(self) -> None:
    #     """
    #     Синхронизирует слэш-команды с Discord.
    #     Этот метод следует вызывать после добавления всех когов.
    #     """
    #     try:
    #         # Синхронизируем команды глобально
    #         synced = await self.bot.tree.sync()
    #         logger.info(f"Синхронизировано {len(synced)} команд")
    #     except Exception as e:
    #         logger.error(f"Ошибка при синхронизации команд: {str(e)}")
