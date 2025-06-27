from logger import logger
from config import config
import asyncio
import discord
from discord.ext import commands
from factory import ServiceFactory
from database.db import init_db
from app.bot import BoostyQueueBot

async def main():
    """
    Главная асинхронная функция для запуска бота.
    """
    try:
        bot = BoostyQueueBot()
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
    asyncio.run(main())
