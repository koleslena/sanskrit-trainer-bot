import json
import logging

import asyncio

from typing import TypedDict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings
from db import get_user_weakest_topic, get_question_from_db
from logic import check_sanskrit_answer
from messages import MESSAGES
from transliteration import normalize_to_slp1, slp_to_deva_iast

logger = logging.getLogger("SanskritMAS.Graph")
logger.propagate = True

# Настройка модели (OpenRouter)
llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    openai_api_key=settings.OPENROUTER_API_KEY,
    openai_api_base=settings.OPENROUTER_URL,
)

# Состояние графа 
class AgentState(TypedDict):
    user_id: int
    tg_language: str        # Язык из Telegram (например, 'ru' или 'en') - наш запасной план
    detected_language: str  # Язык, который определила LLM
    user_input: str
    intent: str             # 'test', 'answer', 'help'
    current_topic: Optional[str]
    last_topic: Optional[str]
    correct_answer: Optional[str]
    bot_response: str
    is_success: bool

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

    correct_slp1 = " ".join(state["correct_answer"]).strip()
    logger.info(f"   ∟ Ответ в SLP1: '{correct_slp1}'")

    correct_for_user = " ".join([slp_to_deva_iast(ans) for ans in state["correct_answer"]])

    is_perfect = True if user_input_slp1 == correct_slp1 else check_sanskrit_answer(user_input_slp1, state["correct_answer"])
    logger.info(f"   ∟ Сравнение: {'✅ СОВПАЛО' if is_perfect else '❌ ОШИБКА'}")
    
    # Теперь мы динамически передаем язык, на котором нужно ответить
    target_lang = "Russian" if state["detected_language"] == "ru" else "English"

    if is_perfect:
        system_text = f"""
                You are a supportive Sanskrit tutor. IMPORTANT: You MUST respond entirely in {target_lang}. 
                The student is CORRECT. 
                Just congratulate them briefly and encourage them.
                Don't be vague. Be precise.
                """
        human_text = "Status: SUCCESS"
    else:
        system_text = f"""You are a strict but helpful Sanskrit tutor. Respond in {target_lang}. 
                The student is WRONG. 
                Your task is to:
                1. Say the answer is incorrect.
                2. Provide this correct version: {correct_for_user}
                3. If it's a verb, remind about periphrastic forms (one word). 
                    - For conjugation (periphrastic forms): Remind that forms ending in -ām must be ONE word (e.g., 'īkṣāñcakre').
                
                DO NOT try to analyze the student's answer. 
                DO NOT explain why it's wrong or right. 

                Do not explain your reasoning. Just provide the feedback.
                Don't be vague. Be precise.
                """
        human_text = "Status: FAILURE"

    messages = [
        SystemMessage(content=system_text),
        HumanMessage(content=human_text)
    ]
    
    response = llm.invoke(messages)

    state["bot_response"] = response.content
    state["is_success"] = is_perfect
    
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

    user_id = state["user_id"]
    
    topic = asyncio.run(get_user_weakest_topic(user_id, state.get("last_topic", "")))
    
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
    tone = "Склоняй слово '...' (род: ...), падеж: ..." if state["detected_language"] == "ru" else "Decline the word '...' (gender: ...), case: ..."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a Sanskrit Teacher. Your task is to present a grammar exercise.
        Respond STRICTLY in {target_lang}.
        IMPORTANT RULES:\n
        1. ADRESSING: You are talking to ONE student. Use 'ты' or 'вы' (singular). 
        NEVER say 'students', 'class', or 'дорогие ученики'.\n

        2. SCRIPT & TRANSLITERATION (CRITICAL):
        - Write ALL Sanskrit words (lemmas, terms) ONLY in Devanagari script (e.g., देव) and IAST transliteration (e.g., deva). 
        - NEVER use plain English/Russian letters for Sanskrit sounds (e.g., DO NOT write 'shabda').
        - Use ONLY the Sanskrit words (lemmas, forms) exactly as provided in the 'raw_data'.
        - DO NOT attempt to transliterate or convert words into Devanagari or IAST yourself.
        - DO NOT change the spelling, accents, or diacritics of the provided Sanskrit words.

        3. NO ANSWERS IN PROMPT (STRICT BAN):
        - DO NOT provide the correct forms or examples of declension/conjugation for the target word.
        - DO NOT list the answers in numbered lists or any other format.
        - Your goal is to ASK the question, not to answer it or show "how it should look".
        
        4. Exercise context: {{raw_data}}
        
        5. Task Presentation:
        - If it's declension: Simply include the word, its GENDER (from raw_data), and the case. 
        Example of tone: {tone}
        - If it's conjugation: Simply state the verb, the tense/mood and gana.
        
        6. Instructions for Student:
        - For declension: Mention the order is Singular, Dual, Plural.
        - For conjugation: Mention the 3x3 grid format. 
        - For conjugation: PERIPHRASTIC FORMS (CRITICAL): Explicitly instruct the student that periphrastic perfect forms (ending in -ām) MUST be written as ONE word, without a space (e.g., 'īkṣāñcakre', NOT 'īkṣām cakre').
        - INPUT FORMAT (CRITICAL): Tell them to enter words in ONE line, separated ONLY by spaces (e.g., devaḥ devau devāḥ). 
            No commas, no numbers, or extra text in their answer—only the words themselves.
        
        7. STYLE:
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