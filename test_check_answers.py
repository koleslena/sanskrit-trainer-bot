import pytest

from logic import check_sanskrit_answer

@pytest.fixture
def correct_declension():
    """Фикстура с эталонными формами (вариантность в первом слоте)"""
    return ["he katamat,he katamad", "he katame", "he katamAni"]

@pytest.mark.parametrize("user_input, expected_result", [
    # Позитивные сценарии
    ("he katamad he katame he katamAni", True),   # Вариант 1
    ("he katamat he katame he katamAni", True),   # Вариант 2
    ("  he katamat   he katame he katamAni  ", True), # Лишние пробелы по краям
    
    # Негативные сценарии
    ("he katamad he katame", False),              # Недостаточно слов
    ("he katamad he katame he katamAni extra", False), # Лишние слова
    ("he katamad he wrong he katamAni", False),   # Ошибка в одном слове
    ("he katamad he katame he katamani", False),   # Ошибка в регистре (если не нормализовали)
    ("", False),                                  # Пустая строка
])

def test_check_sanskrit_answer_variants(user_input, expected_result, correct_declension):
    """Тестирование функции проверки ответов с учетом вариантности и ошибок"""
    assert check_sanskrit_answer(user_input, correct_declension) == expected_result

def test_check_sanskrit_answer_no_input():
    """Критический случай: пустой ввод и пустой список форм"""
    assert check_sanskrit_answer("", []) == True

@pytest.fixture
def correct_lit_periphrastic():
    """Данные для перифрастического перфекта (3 варианта на каждый слот)"""
    return [
        "IkzAYcakre,IkzAmAsa,IkzAmbaBUva", 
        "IkzAYcakrAte,IkzAmAsatuH,IkzAmbaBUvatuH", 
        "IkzAYcakrire,IkzAmAsuH,IkzAmbaBUvuH",
        "IkzAYcakfze,IkzAmAsiTa,IkzAmbaBUviTa",
        "IkzAYcakrATe,IkzAmAsaTuH,IkzAmbaBUvaTuH",
        "IkzAYcakfQve,IkzAmAsa,IkzAmbaBUva",
        "IkzAYcakre,IkzAmAsa,IkzAmbaBUva",
        "IkzAYcakfvahe,IkzAmAsiva,IkzAmbaBUviva",
        "IkzAYcakfmahe,IkzAmAsima,IkzAmbaBUvima"
    ]

@pytest.mark.parametrize("user_input, expected_result", [
    # 1. Тест: первая форма через 'cakre', остальные тоже корректны
    ("IkzAYcakre IkzAYcakrAte IkzAYcakrire IkzAYcakfze IkzAYcakrATe IkzAYcakfQve IkzAYcakre IkzAYcakfvahe IkzAYcakfmahe", True),
    
    # 2. Тест: первая форма через 'baBUva' (тоже верный вариант)
    ("IkzAmbaBUva IkzAYcakrAte IkzAYcakrire IkzAYcakfze IkzAYcakrATe IkzAYcakfQve IkzAYcakre IkzAYcakfvahe IkzAYcakfmahe", True),
    
    # 3. Тест: если формы записаны с пробелом внутри (например, IkzAm baBUva)
    # Наш новый паттерн (\\S+Am\\s+\\S+) это обработает с ошибкой потому что надо писать слитно
    ("IkzAm baBUva IkzAYcakrAte IkzAYcakrire IkzAYcakfze IkzAYcakrATe IkzAYcakfQve IkzAYcakre IkzAYcakfvahe IkzAYcakfmahe", False),
    
    # 4. Тест: ошибка в одной из форм
    ("wrong_word IkzAYcakrAte IkzAYcakrire IkzAYcakfze IkzAYcakrATe IkzAYcakfQve IkzAYcakre IkzAYcakfvahe IkzAYcakfmahe", False),
    
    # 5. Тест: недостаточное количество форм (нужно 9 для глагола)
    ("IkzAYcakre IkzAYcakrAte", False),
])

def test_periphrastic_lit(user_input, expected_result, correct_lit_periphrastic):
    assert check_sanskrit_answer(user_input, correct_lit_periphrastic) == expected_result