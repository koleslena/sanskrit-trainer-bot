import pytest
from transliteration import normalize_to_slp1


@pytest.mark.parametrize("input_text, expected_slp1", [
    # --- Деванагари ---
    ("गच्छति", "gacCati"),
    ("देव", "deva"),
    ("अश्व", "aSva"),
    
    # --- IAST (с диакритикой) ---
    ("gacchati", "gacCati"),
    ("devābhyām", "devAByAm"),
    ("ṛṣi", "fzi"),
    ("kṛṣṇa", "kfzRa"),
    
    # --- Harvard-Kyoto (HK) ---
    ("bhavati", "Bavati"),  # bh -> B
    ("khadati", "Kadati"),  # kh -> K
    ("phalam", "Palam"),    # ph -> P
    
    # --- SLP1 (Без изменений) ---
    ("gaccati", "gaccati"),
    ("Bavati", "Bavati"),
    ("fzi", "fzi"),
    ("Darma", "Darma"),     # dh -> D
    
    # --- Пустые и краевые случаи ---
    ("", ""),
    ("   ", ""),
])

def test_normalize_to_slp1(input_text, expected_slp1):
    """Тестирование корректности транслитерации в формат SLP1."""
    assert normalize_to_slp1(input_text) == expected_slp1

def test_slp1_specific_markers():
    """Отдельный тест на специфичные для SLP1 гласные."""
    # f = ṛ, F = ṝ
    assert normalize_to_slp1("fzi") == "fzi"
    assert normalize_to_slp1("pitFn") == "pitFn" # pitṝn