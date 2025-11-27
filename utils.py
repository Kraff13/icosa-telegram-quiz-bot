# utils.py

import html


def escape_html(text: str) -> str:
    """Экранирование HTML-спецсимволов"""
    return html.escape(text)


async def get_user_name(user):
    """Получение отображаемого имени пользователя"""
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    elif user.username:
        return f"@{user.username}"
    else:
        return f"Пользователь {user.id}"


async def format_stats_message(stats):
    """Форматирование сообщения с личной статистикой"""
    user_id, username, last_correct, last_total, total_correct, total_attempts = stats

    # Защита от деления на ноль
    last_accuracy = round(last_correct * 100 / last_total, 1) if last_total > 0 else 0

    # Общая точность
    total_questions_answered = last_total * total_attempts
    avg_accuracy = round(total_correct * 100 / total_questions_answered, 1) if total_questions_answered > 0 else 0

    # Эмодзи в зависимости от точности
    last_emoji = "🏆" if last_accuracy >= 80 else "🥈" if last_accuracy >= 60 else "🥉" if last_accuracy >= 40 else "💪"
    avg_emoji = "🎯" if avg_accuracy >= 70 else "📊"

    return (
        f"📊 *Ваша статистика:*\n\n"
        f"{last_emoji} *Последний квиз:*\n"
        f"   ✅ Правильных: {last_correct} из {last_total}\n"
        f"   📈 Точность: {last_accuracy}%\n\n"
        f"{avg_emoji} *Общая статистика:*\n"
        f"   🎯 Средняя точность: {avg_accuracy}%\n"
        f"   📊 Всего попыток: {total_attempts}\n"
        f"   ✅ Всего правильных ответов: {total_correct}"
    )


async def format_leaderboard_message(leaderboard):
    """Форматирование сообщения с лидербордом"""
    if not leaderboard:
        return "📭 Пока нет данных для лидерборда.\nПройдите квиз, чтобы попасть в топ!"

    message = "🏆 *Топ-10 игроков:*\n\n"

    for i, row in enumerate(leaderboard, 1):
        # Распаковываем данные из базы
        user_id, username, last_correct, last_total, total_correct, total_attempts = row

        # Рассчитываем точность последнего квиза
        accuracy = round(last_correct * 100 / last_total, 1) if last_total > 0 else 0

        # Эмодзи для мест
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "

        message += f"{medal} {i}. *{username}*\n   ✅ {last_correct}/{last_total} ({accuracy}%)\n\n"

    return message + "\n_Статистика обновляется после каждого прохождения квиза._"
