import asyncio
from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.enums import ParseMode

import logging
import logger_config

# Импортируем нашу логику и БД
from db_mock import save_user_stats
from mas_graph import AgentState, route_intent, grader_agent, instructor_agent, examiner_agent_workflow
from config import settings
from messages import MESSAGES

logger = logging.getLogger("SanskritMAS.Bot")
logger.propagate = True

bot = Bot(
    token=settings.BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
router = Router()

# Временное хранилище "текущего вопроса" (в реальном проекте - Redis или БД)
user_sessions = {}

@router.message(Command("start", "help"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    prev_lang = user_sessions.get(user_id, {}).get("detected_language")
    lang = prev_lang or (message.from_user.language_code or "en")
    
    # Инициализируем состояние и зовем Инструктора
    state = AgentState(
        user_id=message.from_user.id, 
        tg_language=lang,
        detected_language=lang,
        user_input="help", 
        intent="", 
        current_topic=None, 
        correct_answer=None, 
        bot_response="")
    state = instructor_agent(state)
    
    await message.answer(state["bot_response"])

@router.message(Command("test"))
async def cmd_test(message: types.Message):
    user_id = message.from_user.id
    # Берем язык из истории сессии или из настроек TG
    prev_lang = user_sessions.get(user_id, {}).get("detected_language")
    lang = prev_lang or (message.from_user.language_code or "en")

    # Инициализируем состояние
    state = AgentState(
        user_id=user_id,
        tg_language=lang,
        detected_language=lang,
        user_input="START_TEST_COMMAND", # Сигнал для роутера
        intent="test",
        current_topic=None,
        correct_answer=None,
        bot_response=""
    )

    # Прогоняем через цепочку агентов
    # Аналитик и Экзаменатор заполнят тему и текст вопроса
    loop = asyncio.get_event_loop()
    state = await loop.run_in_executor(None, examiner_agent_workflow, state)

    # Сохраняем обновленное состояние в сессию (чтобы Grader знал правильный ответ)
    user_sessions[user_id] = state

    await message.answer(state["bot_response"])

@router.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id

    prev_lang = user_sessions.get(user_id, {}).get("detected_language")
    lang = prev_lang or (message.from_user.language_code or "en")
    
    # Собираем начальное состояние
    state = AgentState(
        user_id=user_id,
        tg_language=lang,
        detected_language=lang,
        user_input=message.text,
        intent="",
        current_topic=user_sessions.get(user_id, {}).get("current_topic"),
        correct_answer=user_sessions.get(user_id, {}).get("correct_answer"),
        bot_response=""
    )

    # 1. Роутер определяет намерение
    # Запускаем в run_in_executor, чтобы LLM не блокировала асинхронность
    loop = asyncio.get_event_loop()
    state = await loop.run_in_executor(None, route_intent, state)

    # 2. Направляем к нужному агенту
    if state["intent"] == "help":
        state = await loop.run_in_executor(None, instructor_agent, state)

    elif state["intent"] == "test":
        # Если юзер текстом попросил "хочу тест"
        state = await loop.run_in_executor(None, examiner_agent_workflow, state)
        user_sessions[user_id] = state # Обновляем сессию для проверки ответа
        
    elif state["intent"] == "answer":
        if not state["correct_answer"]:
            state["bot_response"] = MESSAGES.get(lang, MESSAGES["en"])["start_test_first"]
        else:
            # Зовем Проверяющего
            state = await loop.run_in_executor(None, grader_agent, state)
            
            # (Опционально) Анализатор оценивает успех по ответу LLM и пишет в БД
            is_success = "correct" in state["bot_response"].lower() or "правильно" in state["bot_response"].lower()
            await save_user_stats(user_id, state["current_topic"], is_success)
            
            # Очищаем сессию после ответа
            user_sessions.pop(user_id, None)
    else:
        state["bot_response"] = MESSAGES.get(lang, MESSAGES["en"])["unknown"]

    await message.answer(state["bot_response"])

async def main():
    dp = Dispatcher()
    dp.include_router(router)
    logger.info("Sanskrit MAS Bot is running...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
