from aiogram import types
from database import get_user_stats, get_leaderboard
from utils import format_stats_message, format_leaderboard_message


async def cmd_stats(message: types.Message):
    """Обработчик команды /stats и кнопки 'Моя статистика'"""
    user_id = message.from_user.id
    stats = await get_user_stats(user_id)

    if not stats:
        await message.answer(
            "📭 У вас пока нет статистики.\n"
            "Пройдите квиз хотя бы один раз, чтобы она появилась!"
        )
        return

    stats_message = await format_stats_message(stats)
    await message.answer(stats_message, parse_mode="Markdown")


async def cmd_leaderboard(message: types.Message):
    """Обработчик команды /leaderboard и кнопки 'Лидерборд'"""
    leaderboard = await get_leaderboard(10)

    if not leaderboard:
        await message.answer("📭 Пока нет данных для лидерборда.\nПопробуйте позже!")
        return

    # Исправлено: убран второй аргумент
    leaderboard_message = await format_leaderboard_message(leaderboard)
    await message.answer(leaderboard_message, parse_mode="Markdown")
