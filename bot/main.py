from logger import logger
from config import config
import asyncio
import discord
from discord.ext import commands
from factory import ServiceFactory
from database.db import get_session, init_db
from sqlalchemy.ext.asyncio import AsyncSession
from commands import SessionCommands
from discord.ext.commands import Cog
from app.bot import BoostyQueueBot

async def main():
    """
    Главная асинхронная функция для запуска бота.
    """
    try:
        db_session = await get_session()
        bot = BoostyQueueBot(db_session)
        async with bot:
            await bot.start(config.DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.error("Ошибка входа: неверный токен. Проверьте конфигурационный файл.")
    except discord.HTTPException as e:
        logger.error(f"Ошибка HTTP при подключении: {e.status} {e.text}")
    except discord.PrivilegedIntentsRequired:
        logger.error("Ошибка: Необходимы привилегированные интенты. Проверьте настройки интентов в панели разработчика Discord.")
    except Exception as e:
        import traceback
        logger.error(traceback.format_exc())
        logger.error(f"Непредвиденная ошибка при запуске бота: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()
            logger.info("Соединение с Discord закрыто.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную.")
    except Exception as e:
        logger.info(e.with_traceback())
        logger.error(f"Критическая ошибка при выполнении asyncio.run: {e}")
