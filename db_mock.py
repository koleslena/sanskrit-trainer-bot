import random
import logging

from messages import MESSAGES

logger = logging.getLogger("SanskritMAS.DB")

async def get_user_weakest_topic(user_id: int) -> str:
    # Заглушка: возвращаем случайную тему для теста
    topics = ["a_stems", "i_stems", "present_tense", "past_tense"]
    return random.choice(topics)

async def get_question_from_db(topic: str, lang: str = "en") -> dict:
    """
    Возвращает структуру вопроса, адаптированную под язык.
    """
    msg = MESSAGES.get(lang, MESSAGES["en"])
    
    if topic in ["a_stems", "i_stems"]:
        lemma = "deva"
        category = "основа на -a" if lang == "ru" else "-a stem"
        case = "Творительный (Instrumental)"
        
        question_text = msg["task_declension"].format(
            lemma=lemma, 
            category=category, 
            case=case
        )
        
        return {
            "question_data": question_text,
            "correct_answer": "devena devAByAm devaiH"
        }
        
    else:
        lemma = "gam"
        category = "1-й класс" if lang == "ru" else "1st class"
        tense = "Настоящее (Present)"
        
        question_text = msg["task_conjugation"].format(
            lemma=lemma, 
            category=category, 
            tense=tense
        )
        
        return {
            "question_data": question_text,
            # "correct_answer": "gacchati gacchataḥ gacchanti gacchasi gacchathaḥ gacchatha gacchāmi gacchāvaḥ gacchāmaḥ"
            "correct_answer": "gacCati gacCataH gacCanti gacCasi gacCaTaH gacCaTa gacCAmi gacCAvaH gacCAmaH"
        }
    

async def save_user_stats(user_id: int, topic: str, is_correct: bool):
    # Заглушка для сохранения статистики в БД
    logger.info(f"[DB] Статистика сохранена: юзер {user_id}, тема {topic}, успех: {is_correct}")