# handlers/quiz_handlers.py
import random
from aiogram import types
from database import (
    get_quiz_session,
    update_quiz_index,
    save_quiz_result,
    reset_quiz_session,
    increment_correct_answer
)
from quiz_data_full import get_random_questions
from keyboards import generate_options_keyboard
from utils import get_user_name, escape_html


async def cmd_quiz(message: types.Message):
    """Обработчик команды /quiz и кнопки 'Начать квиз'"""
    await message.answer("🎯 Отлично! Начинаем квиз.\n\nПервый вопрос:")
    await new_quiz(message)


async def new_quiz(message: types.Message):
    """Начало нового квиза со случайными вопросами и перемешанными вариантами"""
    user_id = message.from_user.id

    # Получаем 10 случайных вопросов
    selected_questions = get_random_questions(10)

    # Сохраняем индексы вопросов
    question_indices = list(range(len(selected_questions)))

    # Сбрасываем сессию с выбранными вопросами
    await reset_quiz_session(user_id, question_indices)

    # Инициализируем кэш для вопросов
    if not hasattr(new_quiz, 'selected_questions_cache'):
        new_quiz.selected_questions_cache = {}

    # Очищаем предыдущие данные для этого пользователя
    if hasattr(new_quiz, 'question_mapping'):
        new_quiz.question_mapping.pop(user_id, None)

    new_quiz.selected_questions_cache[user_id] = selected_questions

    await get_question(message, user_id)


async def get_question(message: types.Message, user_id: int):
    """Получение текущего вопроса с перемешанными вариантами"""
    current_index, correct_count = await get_quiz_session(user_id)

    # Получаем выбранные вопросы для пользователя
    selected_questions = new_quiz.selected_questions_cache.get(user_id, [])

    if not selected_questions or current_index >= len(selected_questions):
        await finish_quiz(message, user_id)
        return

    question = selected_questions[current_index]

    # === НАЧАЛО: ПЕРЕМЕШИВАНИЕ ВАРИАНТОВ ОТВЕТОВ ===
    # Создаём копию вариантов и их оригинальных индексов
    options_with_indices = list(enumerate(question['options']))

    # Перемешиваем варианты в случайном порядке
    random.shuffle(options_with_indices)

    # Извлекаем новые порядки и индексы
    shuffled_options = [option for _, option in options_with_indices]
    original_indices = [original_index for original_index, _ in options_with_indices]

    # Находим новый индекс правильного ответа
    original_correct_index = question['correct_option']
    new_correct_index = original_indices.index(original_correct_index)

    # Сохраняем сопоставление для текущего вопроса
    if not hasattr(new_quiz, 'question_mapping'):
        new_quiz.question_mapping = {}

    if user_id not in new_quiz.question_mapping:
        new_quiz.question_mapping[user_id] = {}

    new_quiz.question_mapping[user_id][current_index] = {
        'original_indices': original_indices,
        'new_correct_index': new_correct_index
    }

    kb = generate_options_keyboard(current_index, shuffled_options)

    await message.answer(
        f"❓ <b>Вопрос {current_index + 1} из {len(selected_questions)}:</b>\n\n{question['question']}",
        reply_markup=kb,
        parse_mode="HTML"
    )


async def handle_answer(callback: types.CallbackQuery):
    """Обработка ответа пользователя с учётом перемешанных вариантов"""
    user_id = callback.from_user.id
    current_index, correct_count = await get_quiz_session(user_id)

    # Получаем выбранные вопросы для пользователя
    selected_questions = new_quiz.selected_questions_cache.get(user_id, [])

    if not selected_questions or current_index >= len(selected_questions):
        await callback.answer("Квиз уже завершен!")
        return

    # Удаляем клавиатуру с вопроса
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    # РАСПАКОВКА CALLBACK_DATA
    try:
        parts = callback.data.split('_')
        received_question_index = int(parts[0][1:])
        selected_option_index = int(parts[1][1:])
    except (ValueError, IndexError):
        await callback.answer("Неверные данные кнопки!")
        return

    # ПРОВЕРКА: это ответ на текущий вопрос?
    if received_question_index != current_index:
        await callback.answer("Этот вопрос уже неактуален!")
        return

    # === НАЧАЛО: ОБРАБОТКА ПЕРЕМЕШАННЫХ ВАРИАНТОВ ===
    # Получаем сопоставление для текущего вопроса
    if (not hasattr(new_quiz, 'question_mapping') or
            user_id not in new_quiz.question_mapping or
            current_index not in new_quiz.question_mapping[user_id]):
        await callback.answer("Ошибка: не найдены данные о вариантах ответов")
        return

    mapping = new_quiz.question_mapping[user_id][current_index]
    new_correct_index = mapping['new_correct_index']
    original_indices = mapping['original_indices']

    # Получаем данные вопроса
    question = selected_questions[current_index]

    # Определяем правильность ответа
    is_correct = (selected_option_index == new_correct_index)

    # Получаем тексты ответов для отображения
    selected_option_text = question['options'][original_indices[selected_option_index]]
    correct_option_text = question['options'][original_indices[new_correct_index]]

    # === КОНЕЦ: ОБРАБОТКА ПЕРЕМЕШАННЫХ ВАРИАНТОВ ===

    # Если ответ правильный — увеличиваем счётчик
    if is_correct:
        await increment_correct_answer(user_id)
        correct_count += 1

    # Отправляем сообщение с ответом пользователя
    status_emoji = "✅" if is_correct else "❌"
    status_text = "Правильно!" if is_correct else f"Неправильно. Правильный ответ: {escape_html(correct_option_text)}"

    await callback.message.answer(
        f"👤 <b>Ваш ответ:</b> {escape_html(selected_option_text)}\n"
        f"{status_emoji} {status_text}",
        parse_mode="HTML"
    )

    # Обновляем индекс вопроса
    next_index = current_index + 1
    await update_quiz_index(user_id, next_index)

    # Если квиз завершен
    if next_index >= len(selected_questions):
        await finish_quiz(callback.message, user_id)
    else:
        # Задаем следующий вопрос
        await get_question(callback.message, user_id)

    await callback.answer()


async def finish_quiz(message: types.Message, user_id: int):
    """Завершение квиза и очистка кэша"""
    _, correct_count = await get_quiz_session(user_id)

    # Получаем выбранные вопросы для подсчёта общего количества
    selected_questions = new_quiz.selected_questions_cache.get(user_id, [])
    total_questions = len(selected_questions) if selected_questions else 10

    username = await get_user_name(message.from_user)

    # Сохраняем результат
    await save_quiz_result(user_id, username, correct_count, total_questions)

    # Отправляем результат
    accuracy = round(correct_count * 100 / total_questions, 1) if total_questions > 0 else 0
    result_emoji = "🏆" if accuracy >= 80 else "🥈" if accuracy >= 60 else "🥉" if accuracy >= 40 else "💪"

    await message.answer(
        f"{result_emoji} <b>Квиз завершён!</b>\n\n"
        f"✅ Правильных ответов: {correct_count} из {total_questions}\n"
        f"📊 Точность: {accuracy}%\n\n"
        f"Посмотреть статистику: /stats или кнопка «📊 Моя статистика»\n"
        f"Пройти снова: нажмите «🧠 Начать квиз»",
        parse_mode="HTML"
    )

    # Очищаем кеш для пользователя
    if hasattr(new_quiz, 'question_mapping') and user_id in new_quiz.question_mapping:
        del new_quiz.question_mapping[user_id]

    if hasattr(new_quiz, 'selected_questions_cache') and user_id in new_quiz.selected_questions_cache:
        del new_quiz.selected_questions_cache[user_id]
