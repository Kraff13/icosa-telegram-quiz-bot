import asyncio
import logging
import os
import signal
import sys

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command

# Импорт пользовательских модулей
from database import create_tables
from handlers.quiz_handlers import cmd_quiz, handle_answer
from handlers.start_handlers import cmd_start, cmd_help
from handlers.stats_handlers import cmd_stats, cmd_leaderboard

# Загрузка переменных окружения
load_dotenv()

# Проверка наличия токена
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    logging.error("API_TOKEN не найден в переменных окружения. Проверьте файл .env")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


async def shutdown() -> None:
    """Корректное завершение работы бота"""
    logger.info("Начало graceful shutdown...")
    try:
        await bot.session.close()
        logger.info("Сессия бота закрыта")
    except Exception as exc_shutdown:
        logger.error(f"Ошибка при закрытии сессии: {exc_shutdown}")
    finally:
        logger.info("Бот остановлен корректно")


def signal_handler(sig_num: int, _frame: object) -> None:
    """
    Обработчик сигналов для graceful shutdown

    Args:
        sig_num: Номер сигнала
        _frame: Фрейм выполнения (не используется)
    """
    logger.info(f"Получен сигнал {sig_num}. Инициируем graceful shutdown...")
    # Устанавливаем флаг для прерывания асинхронных операций
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(shutdown())
        else:
            asyncio.run(shutdown())
    except Exception as exc_signal:
        logger.error(f"Ошибка при обработке сигнала: {exc_signal}")
    finally:
        sys.exit(0)


async def setup_handlers() -> None:
    """Настройка обработчиков команд и кнопок"""
    # Регистрация обработчиков команд
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_quiz, Command("quiz"))
    dp.message.register(cmd_stats, Command("stats"))
    dp.message.register(cmd_leaderboard, Command("leaderboard"))

    # Регистрация обработчиков для кнопок меню
    dp.message.register(cmd_quiz, F.text == "🧠 Начать квиз")
    dp.message.register(cmd_stats, F.text == "📊 Моя статистика")
    dp.message.register(cmd_leaderboard, F.text == "🏆 Лидерборд")

    # Регистрация обработчиков callback-запросов
    dp.callback_query.register(handle_answer, F.data.startswith("q"))

    logger.info("Обработчики успешно зарегистрированы")


async def main() -> None:
    """Основная функция запуска бота"""
    logger.info("Запуск бота Icosa...")

    try:
        # Создание таблиц базы данных
        await create_tables()
        logger.info("Таблицы базы данных созданы/проверены")

        # Настройка обработчиков
        await setup_handlers()

        # Регистрация обработчиков сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        logger.info("Обработчики сигналов зарегистрированы")

        logger.info(f"Бот @{(await bot.me()).username} запущен и готов к работе")
        logger.info("Для остановки нажмите Ctrl+C")

        # Запуск polling
        await dp.start_polling(bot)

    except Exception as exc_main:
        logger.critical(f"Критическая ошибка при запуске бота: {exc_main}", exc_info=True)
        await shutdown()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Работа бота прервана пользователем (Ctrl+C)")
    except Exception as exc_global:
        logger.critical(f"Необработанное исключение: {exc_global}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Программа завершена")
