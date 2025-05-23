from logger import logger
from config import config
import asyncio
import discord

# Определяем необходимые интенты (права) для бота
intents = discord.Intents.default()
intents.message_content = True # Разрешаем боту читать содержимое сообщений
intents.members = True

# Создаем экземпляр клиента Discord
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    """
    Событие, вызываемое при успешном подключении бота к Discord.
    """
    logger.info(f'Бот успешно залогинен как {client.user}')

@client.event
async def on_message(message: discord.Message):
    """
    Событие, вызываемое при получении нового сообщения.
    """
    # Не отвечаем на сообщения от самого себя
    if message.author == client.user:
        return

    logger.info(f"Получено сообщение от {message.author}: {message.content}")

async def main():
    """
    Главная асинхронная функция для запуска бота.
    """
    try:
        logger.info(f"Токен: {config.DISCORD_TOKEN}")
        await client.start(config.DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.error("Ошибка входа: неверный токен. Проверьте конфигурационный файл.")
    except discord.HTTPException as e:
        logger.error(f"Ошибка HTTP при подключении: {e.status} {e.text}")
    except discord.PrivilegedIntentsRequired:
        logger.error("Ошибка: Необходимы привилегированные интенты. Проверьте настройки интентов в панели разработчика Discord.")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при запуске бота: {e}")
    finally:
        if not client.is_closed():
            await client.close()
            logger.info("Соединение с Discord закрыто.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную.")
    except Exception as e:
        logger.error(f"Критическая ошибка при выполнении asyncio.run: {e}")
