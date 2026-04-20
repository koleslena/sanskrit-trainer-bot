from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

def normalize_to_slp1(text: str) -> str:
    """
    Определяет (примерно) схему письма и конвертирует её в SLP1.
    Список схем, которые мы поддерживаем DEVANAGARI, IAST, HK (Harvard-Kyoto), SLP1
    """
    if not text:
        return ""
    
    text = text.strip()
    
    # Если есть f, x или F, X — это точно SLP1, возвращаем как есть
    if any(m in text for m in "fFxX"):
        return text 

    hk_markers = ["kh", "gh", "ch", "jh", "th", "dh", "ph", "bh"]
    
    # Пытаемся определить: если есть символы деванагари
    if any('\u0900' <= char <= '\u097F' for char in text):
        source_scheme = sanscript.DEVANAGARI
    # Если есть диакритика (ā, ī, ū, ṃ, ḥ, ṭ, ḍ, ṇ, ś, ṣ) — скорее всего IAST
    elif any(char in "āīūṃḥṭḍṇśṣ" for char in text.lower()):
        source_scheme = sanscript.IAST
    # Если есть характерные придыхания 'h' — скорее всего это HK
    elif any(m in text.lower() for m in hk_markers):
        source_scheme = sanscript.HK
    else:
        return text
    
    return transliterate(text, source_scheme, sanscript.SLP1)