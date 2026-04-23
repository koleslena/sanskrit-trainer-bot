import random
import logging
import json
import psycopg2
from psycopg2.extras import RealDictCursor

from config import settings
from messages import MESSAGES
from transliteration import slp_to_deva_iast

MAX_SCORE = 5

logger = logging.getLogger("SanskritMAS.DB")

def get_connection():
    return psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST, 
        port=settings.DB_PORT
    )

async def get_user_weakest_topic(user_id: int, last_topic: str) -> str:
    """
    Выбирает самую слабую тему пользователя или назначает новую,
    если данных недостаточно.
    """
    
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Пытаемся получить данные пользователя
            cur.execute("SELECT current_score, passed FROM tg_users WHERE user_id = %s", (user_id,))
            user_data = cur.fetchone()

            # Проверяем, есть ли данные и не пуст ли словарь score
            passed = user_data['passed'] if user_data and user_data['passed'] else []
            scores = user_data['current_score'] if user_data and user_data['current_score'] else {}

            logger.info(f"DEBUG: У пользователя {len(scores)} тем. Последняя тема была: {last_topic}")

            # 2. Логика выбора 
            if len(scores) >= 5:
                # Случай А: Тем 5 или больше — выбираем тему с минимальным скором (Взвешенный Рандом (Weighted Random))
                # scores — это словарь вида {"plat": 10, "deva": 5, ...}
                pool_dict = {topic: score for topic, score in scores.items() if topic != last_topic}

                # Разделяем ключи (названия тем) и значения (баллы) в списки
                topics = list(pool_dict.keys())
                current_scores = list(pool_dict.values())
                
                # Вычисляем веса (инверсия баллов)
                # Находим максимальный балл в текущем пуле. 
                max_score = max(current_scores)
                
                # Формула: (Максимальный балл - текущий балл) + 1
                # Если баллы [10, 5, 2], то веса будут:
                # Для 10: (10 - 10) + 1 = 1 (самый низкий шанс)
                # Для 5:  (10 - 5) + 1  = 6 (средний шанс)
                # Для 2:  (10 - 2) + 1  = 9 (самый высокий шанс)
                weights = [(max_score - score) + 1 for score in current_scores]
                
                # 3. Делаем взвешенный случайный выбор
                # random.choices возвращает список, поэтому берем первый элемент [0]
                next_topic_name = random.choices(topics, weights=weights, k=1)[0]

                logger.info(f"DEBUG: У пользователя {len(scores)} тем. Выбрана взвешенным рандомом: {next_topic_name}")
                return next_topic_name
            else:
                # Случай Б: Данных нет или тем < 5 — выбираем новую случайную тему
                # Объединяем имена из обеих таблиц и исключаем те, что уже есть в scores и passed
                passed_and_current_topics = tuple(list(scores.keys()) + passed,)
                
                query = """
                    WITH random_subanta AS (
                        SELECT name FROM subanta 
                        WHERE name NOT IN %s 
                        ORDER BY RANDOM() 
                        LIMIT 10
                    ),
                    random_tinanta AS (
                        SELECT name FROM tinanta 
                        WHERE name NOT IN %s 
                        ORDER BY RANDOM() 
                        LIMIT 10
                    )
                    SELECT name FROM (
                        SELECT name FROM random_subanta
                        UNION ALL
                        SELECT name FROM random_tinanta
                    ) AS candidates
                    ORDER BY RANDOM()
                    LIMIT 1;
                """
                
                # Если список пуст, передаем кортеж с пустой строкой для корректности SQL
                if not passed_and_current_topics:
                    passed_and_current_topics = ('',)

                cur.execute(query, (passed_and_current_topics, passed_and_current_topics))
                new_topic_row = cur.fetchone()

                if new_topic_row:
                    return new_topic_row['name']
                else:
                    # Если вдруг все темы мира уже изучены (маловероятно)
                    return random.choice(passed_and_current_topics) if passed_and_current_topics else None

    except Exception as e:
        logger.error(f"❌ Ошибка при выборе темы: {e}")
        return None
    finally:
        conn.close()

# Словарик соответствия падежей (для субант)
CASE_MAP = {
    "1": {"ru": "Именительный", "en": "Nominative"},
    "2": {"ru": "Винительный", "en": "Accusative"},
    "3": {"ru": "Творительный", "en": "Instrumental"},
    "4": {"ru": "Дательный", "en": "Dative"},
    "5": {"ru": "Отложительный", "en": "Ablative"},
    "6": {"ru": "Родительный", "en": "Genitive"},
    "7": {"ru": "Местный", "en": "Locative"},
    "8": {"ru": "Звательный", "en": "Vocative"}
}

async def get_question_from_db(topic: str, lang: str = "en") -> dict:
    """
    Возвращает структуру вопроса, адаптированную под язык.
    """
    
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # --- 1. ОПРЕДЕЛЯЕМ ТИП ТЕМЫ ---
            # Темы субант начинаются с цифры (падежа), например "1_a_P"
            if topic[0].isdigit():
                case_num = topic[0]
                
                # Достаем случайное слово из zabda для этой основы
                cur.execute("SELECT word, subs FROM zabda WHERE stem = %s ORDER BY RANDOM() LIMIT 1", (topic,))
                word_data = cur.fetchone()
                
                # Достаем описание категории
                cur.execute("SELECT description FROM subanta WHERE name = %s", (topic,))
                cat_data = cur.fetchone()
                
                if not word_data or not cat_data:
                    return None

                category = cat_data['description'][lang]
                case_name = CASE_MAP.get(case_num, {}).get(lang, "")
                
                question_text = MESSAGES[lang]["task_declension"].format(
                    lemma=slp_to_deva_iast(word_data['word']),
                    category=category,
                    case=case_name
                )
                
                # Правильные ответы для конкретного падежа 
                correct_answer = word_data['subs']

            else:
                # Тема глагола (например, "plat", "plit")
                cur.execute("SELECT word, tins, gana, pada FROM dhatu WHERE tin = %s ORDER BY RANDOM() LIMIT 1", (topic,))
                word_data = cur.fetchone()
                
                cur.execute("SELECT description FROM tinanta WHERE name = %s", (topic,))
                cat_data = cur.fetchone()

                if not word_data or not cat_data:
                    return None

                # Вытаскиваем описание времени (tense)
                # В tinanta description лежит JSON: {"ru": "Настоящее время (...)", "en": "..."}
                full_desc = cat_data['description'][lang]

                word_desc = f"{word_data['gana']}{word_data['pada']}"
                
                question_text = MESSAGES[lang]["task_conjugation"].format(
                    lemma=slp_to_deva_iast(word_data['word']),
                    category=word_desc, 
                    tense=full_desc
                )
                
                # Правильные ответы для конкретного лакара
                correct_answer = word_data['tins']

            logger.info(f"📝 Вопрос сформирован. Тема: {topic}, Вопрос: {question_text}")
            return {
                "question_data": question_text,
                "correct_answer": correct_answer
            }

    except Exception as e:
        logger.error(f"❌ Ошибка получения вопроса: {e}")
        return None
    finally:
        conn.close()
    

async def save_user_stats(user_id: int, topic: str, is_correct: bool):
    """
    Обновляет статистику пользователя:
    - Правильно: +1 к баллу. Если балл > MAX_SCORE -> в 'passed', удаляем из 'current_score'.
    - Неправильно: -1 к баллу (минимум 0).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Пытаемся создать пользователя, если его нет (UPSERT)
            # Если пользователь уже есть, ничего не делаем, просто идем дальше
            cur.execute("""
                INSERT INTO tg_users (user_id, current_score, passed)
                VALUES (%s, '{}'::jsonb, '[]'::jsonb)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))

            # 2. Теперь гарантированно получаем данные пользователя
            cur.execute("SELECT current_score, passed FROM tg_users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()

            # Инициализируем словари (в БД они хранятся как JSONB)
            # row[0] - current_score (dict), row[1] - passed (list)
            scores = row[0] if row[0] else {}
            passed = row[1] if row[1] else []

            # 3. Обновляем скор
            current_val = scores.get(topic, 0)
            
            if is_correct:
                new_val = current_val + 1
                
                # Если набрали больше MAX_SCORE баллов
                if new_val > MAX_SCORE:
                    # Убираем из текущих, добавляем в пройденные
                    if topic in scores:
                        del scores[topic]
                    if topic not in passed:
                        passed.append(topic)
                    logger.info(f"🏆 Тема '{topic}' пройдена и перенесена в список 'passed'!")
                else:
                    scores[topic] = new_val
            else:
                # Если неправильно, уменьшаем (но не ниже 0, чтобы не уходить в бесконечный минус)
                scores[topic] = max(0, current_val - 1)

            # 4. Сохраняем обновленные данные обратно в БД
            cur.execute(
                """
                UPDATE tg_users 
                SET current_score = %s, passed = %s 
                WHERE user_id = %s
                """,
                (json.dumps(scores), json.dumps(passed), user_id)
            )
            
            conn.commit()
            logger.info(f"📈 Статистика обновлена для {user_id}. Тема: {topic}, Скор: {scores.get(topic, 'Passed')}")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения статистики: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()