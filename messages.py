MESSAGES = {
    "ru": {
        "start_help": (
            "नमस्ते! Это бот-тренажер по морфологии санскрита. 🕉\n\n"
            "Я буду задавать тебе вопросы по склонениям существительных и спряжениям глаголов, "
            "а твоя задача — писать правильные формы.\n\n"
            "**Как отвечать:**\n"
            "1. **Склонения:** вводи 3 формы через пробел (ед.ч. дв.ч. мн.ч.).\n"
            "   *Звательный падеж:*  пишется с частицей he, например: `he deva he devau he devāḥ`\n"
            "   *Пример:* `devaḥ devau devāḥ`\n"
            "2. **Спряжения:** вводи 9 форм через пробел (сетка 3x3: 3-е, 2-е, 1-е лицо).\n"
            "   *Порядок:* (3ед 3дв 3мн) (2ед 2дв 2мн) (1ед 1дв 1мн).\n\n"
            "   *Пример (для bhū):* `bhavati bhavataḥ bhavanti bhavasi bhavathaḥ bhavatha bhavāmi bhavāvaḥ bhavāmaḥ`\n\n"
            "   Для перифрастик перфект: формы (оканчивающиеся на -ām + вспомогательный глагол) должны писаться слитно (например, 'īkṣāñcakre')"
            "**Команды:**\n"
            "/test — получить новое задание.\n"
            "/help — показать эту инструкцию.\n\n"
            "Ты можешь писать на деванагари, IAST или латиницей (HK). Желаю удачи!"
        ),
        "unknown": "Я не совсем вас понял. Введите /test для тренировки или /help для инструкций.",
        "start_test_first": "Пожалуйста, сначала начните тест с помощью команды /test.",
        "task_declension": "Склонение слова '{lemma}' ({category}), падеж: {case}, все 3 числа.",
        "task_conjugation": "Спряжение глагола '{lemma}' ({category}), время: {tense}, 3 лица на 3 числа.",
    },
    "en": {
        "start_help": (
            "नमस्ते! This is a Sanskrit Morphology Trainer bot. 🕉\n\n"
            "I will ask you questions about noun declensions and verb conjugations, "
            "and your task is to provide the correct forms.\n\n"
            "**How to answer:**\n"
            "1. **Declensions:** enter 3 forms separated by space (Sing. Du. Plur.).\n"
            "   *Vocative case:* must be with he, example: `he deva he devau he devāḥ`\n"
            "   *Example:* `devaḥ devau devāḥ`\n"
            "2. **Conjugations:** enter 9 forms separated by space (3x3 grid: 3rd, 2nd, 1st person).\n"
            "   *Order:* (3s 3d 3p) (2s 2d 2p) (1s 1d 1p).\n\n"
            "   *Example (for bhū):* `bhavati bhavataḥ bhavanti bhavasi bhavathaḥ bhavatha bhavāmi bhavāvaḥ bhavāmaḥ`\n\n"
            "   Periphrastic forms (forms ending in -ām) must be ONE word (e.g., 'īkṣāñcakre')."
            "**Commands:**\n"
            "/test — get a new task.\n"
            "/help — show this manual.\n\n"
            "You can use Devanagari, IAST, or Latin (HK/SLP1). Good luck!"
        ),
        "unknown": "I didn't quite get that. Type /test to practice or /help for instructions.",
        "start_test_first": "Please start a test first using /test.",
        "task_declension": "Declension of the word '{lemma}' ({category}), case: {case}, all 3 numbers.",
        "task_conjugation": "Conjugation of the verb '{lemma}', gana: {category}, tense: {tense}, 3 persons by 3 numbers.",
    }
}