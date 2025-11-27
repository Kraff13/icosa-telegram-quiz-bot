from aiogram.types import KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def generate_start_keyboard():
    """Генерация клавиатуры для стартового сообщения"""
    builder = ReplyKeyboardBuilder()
    buttons = [
        KeyboardButton(text="🧠 Начать квиз"),
        KeyboardButton(text="📊 Моя статистика"),
        KeyboardButton(text="🏆 Лидерборд")
    ]
    builder.add(*buttons)
    builder.adjust(2, 1)  # 2 кнопки в первой строке, 1 во второй
    return builder.as_markup(resize_keyboard=True)


def generate_options_keyboard(question_index: int, options: list):
    """Генерация клавиатуры с вариантами ответов"""
    builder = InlineKeyboardBuilder()

    for option_index, option_text in enumerate(options):
        # Формат: "q{question_index}_a{option_index}"
        callback_data = f"q{question_index}_a{option_index}"
        builder.add(InlineKeyboardButton(
            text=option_text,
            callback_data=callback_data
        ))

    builder.adjust(1)
    return builder.as_markup()
