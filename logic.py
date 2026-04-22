import re


def check_sanskrit_answer(user_input, correct_forms_list):
    """
    user_input: str (напр. "he katamad he katame he katamAni")
    correct_forms_list: list (напр. ["he katamat,he katamad", "he katame", "he katamAni"])
    """
    # 1. Разбиваем ввод пользователя на отдельные слова-ответы
    # Регулярка: ищем слово, перед которым может быть 'he ' (необязательно)
    # Находит: 'he deva', 'he devau', 'devah', 'he  gopala'
    pattern = r'(?:he\s+)?\S+'
    user_blocks = re.findall(pattern, user_input.strip(), re.IGNORECASE)
    
    # Проверка на количество слов (если ввели меньше/больше, чем нужно слотов)
    if len(user_blocks) != len(correct_forms_list):
        return False

    # 2. Сопоставляем каждый ответ пользователя с соответствующим списком вариантов
    for user_word, variants_str in zip(user_blocks, correct_forms_list):
        # Превращаем строку вариантов "he katamat,he katamad" в нормализованный сет {katamat, katamad}
        # Убираем лишние пробелы и разделяем по запятой
        valid_variants = {v.strip() for v in variants_str.split(',')}
        
        # 3. Проверка: входит ли слово пользователя в набор допустимых
        if user_word not in valid_variants:
            return False
            
    return True