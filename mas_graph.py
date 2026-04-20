import json
import logging

import asyncio

from typing import TypedDict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from db_mock import get_user_weakest_topic, get_question_from_db
from messages import MESSAGES
from transliteration import normalize_to_slp1

logger = logging.getLogger("SanskritMAS.Graph")
logger.propagate = True

# Настройка модели (OpenRouter)
llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    openai_api_key=settings.OPENROUTER_API_KEY,
    openai_api_base=settings.OPENROUTER_URL,
)

# Состояние графа (добавляем 'detected_language')
class AgentState(TypedDict):
    user_id: int
    tg_language: str        # Язык из Telegram (например, 'ru' или 'en') - наш запасной план
    detected_language: str  # Язык, который определила LLM
    user_input: str
    intent: str             # 'test', 'answer', 'help'
    current_topic: Optional[str]
    correct_answer: Optional[str]
    bot_response: str

def route_intent(state: AgentState) -> AgentState:
    """Агент-Роутер: определяет намерение и язык."""
    logger.info(f"🔍 ROUTER: Обработка ввода пользователя: '{state['user_input']}'")

    system_prompt = """You are a smart router for a Sanskrit learning bot.
    Analyze the user input and determine two things:
    1. 'intent': 
       - 'test': user wants to start, practice, continue, or says things like "давай", "еще", "погнали", "начнем", "go", "start", "next".
       - 'help': user asks for instructions or is confused.
       - 'answer': user provides Sanskrit forms (e.g., "devaḥ devau devāḥ").
       IMPORTANT: Sanskrit can be written in:
          1. Devanagari (e.g., गच्छति)
          2. IAST (with diacritics: gacchati, devābhyām)
          3. Harvard-Kyoto (capital letters for long vowels/aspirates: gachati, mAnuSa)
          4. SLP1 (single letters for phonemes: gaccati, Bavati)
          If you see strings of words that look like Sanskrit in ANY of these formats, it's an 'answer'.
    2. 'language': What language is the user speaking? ('ru' or 'en'). 
       WARNING: If the input is purely Sanskrit or just a command like /start, output "unknown".
    
    Output strictly in JSON format: {{"intent": "...", "language": "..."}}"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{text}")
    ])
    
    # Заставляем модель вернуть строгий JSON
    chain = prompt | llm.bind(response_format={"type": "json_object"})
    response = chain.invoke({"text": state["user_input"]})
    
    try:
        # Разбираем JSON
        decision = json.loads(response.content)
        
        state["intent"] = decision.get("intent", "help")

        logger.info(f"   ∟ Решение: intent='{state['intent']}', lang='{state['detected_language']}'")
    except Exception as e:
        logger.error(f"   ∟ Ошибка парсинга роутера: {e}")
        state["intent"] = "help"
    
    # ЛОГИКА ВЫБОРА ЯЗЫКА:
    # Если LLM поняла язык, используем его. 
    # Если там только санскрит ("unknown"), берем язык из Telegram.
    if decision.get("language") in ["ru", "en"]:
        state["detected_language"] = decision["language"]
    else:
        state["detected_language"] = state["tg_language"]
        
    return state

def grader_agent(state: AgentState) -> AgentState:
    """Агент-Проверяющий: отвечает на правильном языке."""
    logger.info("🎓 GRADER: Проверка ответа...")

    user_raw = state["user_input"]
    user_input_slp1 = normalize_to_slp1(user_raw)

    logger.info(f"   ∟ Ввод пользователя нормализован к SLP1: '{user_input_slp1}'")

    correct_slp1 = state["correct_answer"].strip()

    is_perfect = user_input_slp1 == correct_slp1
    logger.info(f"   ∟ Сравнение: {'✅ СОВПАЛО' if is_perfect else '❌ ОШИБКА'}")
    
    # Теперь мы динамически передаем язык, на котором нужно ответить
    target_lang = "Russian" if state["detected_language"] == "ru" else "English"
    
    system_text = f"""You are a strict but supportive Sanskrit tutor. 
        IMPORTANT: You MUST respond entirely in {target_lang}.
        
        EVALUATION RULES:
            1. If the Student's SLP1 matches the Correct SLP1 exactly:
            - Confirm it is 100% correct.
            - Congratulate them briefly.
            2. If there is a mistake:
            - Explicitly state that the answer is incorrect.
            - Provide the CORRECT version in SLP1 or Devanagari.
            - Point out exactly where the mistake is (e.g., "In 2nd person dual, it should be X instead of Y").
            
            Don't be vague. Be precise."""

    human_text = f"Exact Match: {is_perfect}\nStudent Answer (SLP1): {user_input_slp1}\nCorrect Answer (SLP1): {correct_slp1}"

    messages = [
        SystemMessage(content=system_text),
        HumanMessage(content=human_text)
    ]
    
    response = llm.invoke(messages)

    state["bot_response"] = response.content
    
    logger.info("   ∟ Анализ ответа сформирован.")
    return state

def instructor_agent(state: AgentState) -> AgentState:
    """Агент-Инструктор: выдает правила форматирования."""
    lang = state["detected_language"]
    # Определяем название языка для промпта
    full_lang = "Russian" if lang == "ru" else "English"
    
    base_instruction = MESSAGES.get(lang, MESSAGES["en"])["start_help"]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            f"You are a helpful Sanskrit Mentor. Explain how to use the bot. "
            f"Your response MUST be entirely in {full_lang}. " # Жёсткое ограничение языка
            "Greet the student warmly and provide the instruction text below."
        )),
        ("human", "{instruction}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"instruction": base_instruction})
    
    state["bot_response"] = response.content
    return state

def analyst_node(state: AgentState) -> AgentState:
    """Узел Аналитика: определяет тему на основе данных из БД."""
    logger.info(f"📊 ANALYST: Анализ прогресса пользователя {state['user_id']}")
    # В будущем здесь будет запрос к JSONB колонке stats
    user_id = state["user_id"]
    # Используем await в асинхронной обертке или обычный вызов для прототипа
    topic = asyncio.run(get_user_weakest_topic(user_id))
    
    state["current_topic"] = topic
    logger.info(f"   ∟ Выбрана тема для тренировки: {topic}")
    return state

def examiner_node(state: AgentState) -> AgentState:
    """Узел Экзаменатора: формирует само задание на нужном языке."""
    logger.info(f"📝 EXAMINER: Подготовка вопроса по теме '{state['current_topic']}'")

    # 1. Получаем «сырые» данные вопроса из БД
    q_data = asyncio.run(get_question_from_db(state["current_topic"], state["detected_language"]))
    state["correct_answer"] = q_data["correct_answer"]

    logger.debug(f"   ∟ Эталонный ответ (SLP1): {state['correct_answer']}")
    
    # 2. Используем LLM, чтобы красиво оформить вопрос на языке пользователя
    target_lang = "Russian" if state["detected_language"] == "ru" else "English"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a Sanskrit Teacher. Your task is to present a grammar exercise.
        Respond STRICTLY in {target_lang}.
        IMPORTANT RULES:\n
        1. ADRESSING: You are talking to ONE student. Use 'ты' or 'вы' (singular). 
        NEVER say 'students', 'class', or 'дорогие ученики'.\n
        
        2. Exercise context: {{raw_data}}
        
        3. Instructions:
        - If it's conjugation: remind them about the 3x3 grid format. Important! the 3x3 grid format for verb conjugation only!
        - If it's declension: remind them about Singular/Dual/Plural.
        - Be encouraging but professional.""")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"raw_data": q_data["question_data"]})
    
    state["bot_response"] = response.content
    logger.info("   ∟ Вопрос сформирован и отправлен.")
    return state

def examiner_agent_workflow(state: AgentState) -> AgentState:
    """
    Оркестратор процесса постановки вопроса.
    Это 'мини-граф' или последовательность вызовов.
    """
    # 1. Сначала анализируем, что нужно юзеру
    state = analyst_node(state)
    # 2. Потом формируем вопрос
    state = examiner_node(state)
    
    return state