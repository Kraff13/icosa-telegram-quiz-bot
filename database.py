# database.py
import aiosqlite
import json

DB_NAME = 'quiz_bot.db'


async def create_tables():
    """Создание всех необходимых таблиц в базе данных"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица для отслеживания текущего состояния квиза
        await db.execute('''
            CREATE TABLE IF NOT EXISTS quiz_state (
                user_id INTEGER PRIMARY KEY,
                question_index INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                selected_questions TEXT DEFAULT '[]'  -- JSON массив с индексами вопросов
            )
        ''')

        # Таблица для хранения статистики пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                last_correct INTEGER DEFAULT 0,
                last_total INTEGER DEFAULT 0,
                total_correct INTEGER DEFAULT 0,
                total_attempts INTEGER DEFAULT 0
            )
        ''')

        await db.commit()


async def reset_quiz_session(user_id: int, selected_questions: list):
    """Сброс сессии квиза с заданными вопросами"""
    selected_questions_json = json.dumps(selected_questions)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO quiz_state (user_id, question_index, correct_answers, selected_questions)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                question_index = excluded.question_index,
                correct_answers = excluded.correct_answers,
                selected_questions = excluded.selected_questions
        ''', (user_id, 0, 0, selected_questions_json))
        await db.commit()


async def get_selected_questions(user_id: int) -> list:
    """Получение списка выбранных вопросов для пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                'SELECT selected_questions FROM quiz_state WHERE user_id = ?',
                (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            if result and result[0]:
                return json.loads(result[0])
            return []


async def update_quiz_index(user_id: int, index: int):
    """Обновление индекса вопроса (без изменения счётчика правильных ответов)"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO quiz_state (user_id, question_index)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET question_index = excluded.question_index
        ''', (user_id, index))
        await db.commit()


async def increment_correct_answer(user_id: int):
    """Увеличение счётчика правильных ответов на 1"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            UPDATE quiz_state 
            SET correct_answers = correct_answers + 1 
            WHERE user_id = ?
        ''', (user_id,))
        await db.commit()


async def get_quiz_session(user_id: int):
    """Получение текущего состояния сессии: индекс вопроса и правильные ответы"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                'SELECT question_index, correct_answers FROM quiz_state WHERE user_id = ?',
                (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            if result:
                return result[0], result[1]
            return 0, 0


async def save_quiz_result(user_id: int, username: str, correct: int, total: int):
    """Сохранение результата прохождения квиза"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,)) as cursor:
            user_exists = await cursor.fetchone()

        if user_exists:
            await db.execute('''
                UPDATE user_stats 
                SET username = ?, 
                    last_correct = ?, 
                    last_total = ?,
                    total_correct = total_correct + ?,
                    total_attempts = total_attempts + 1
                WHERE user_id = ?
            ''', (username, correct, total, correct, user_id))
        else:
            await db.execute('''
                INSERT INTO user_stats (user_id, username, last_correct, last_total, total_correct, total_attempts)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (user_id, username, correct, total, correct))

        await db.commit()


async def get_user_stats(user_id: int):
    """Получение статистики пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()


async def get_leaderboard(limit: int = 10):
    """Получение лидерборда"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('''
            SELECT user_id, username, last_correct, last_total, total_correct, total_attempts
            FROM user_stats
            ORDER BY 
                CASE 
                    WHEN last_total > 0 THEN last_correct * 100.0 / last_total 
                    ELSE 0 
                END DESC,
                last_correct DESC
            LIMIT ?
        ''', (limit,)) as cursor:
            return await cursor.fetchall()
