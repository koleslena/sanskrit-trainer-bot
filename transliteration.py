from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

def slp_to_deva_iast(text: str) -> str:
    return f"{transliterate(text, sanscript.SLP1, sanscript.DEVANAGARI)} ({transliterate(text, sanscript.SLP1, sanscript.IAST)})"

def normalize_to_slp1(text: str) -> str:
    """
    Определяет (примерно) схему письма и конвертирует её в SLP1.
    Список схем, которые мы поддерживаем DEVANAGARI, IAST, HK (Harvard-Kyoto), SLP1
    """
    if not text:
        return ""
    
    text = text.strip()

    # R как ретрофлексная n 
    slp1_markers = ["aR", "AR", "iR", "IR", "uR", "UR", "oR", "OR", "eR", "ER", "Ra", "RA", "Ri", "RI", "Ru", "RU", "Ro", "RO", "Re", "RE"]
    
    # Если есть f, x, w, q или F, X, Y, O, E, W, Q — это точно SLP1, возвращаем как есть
    if any(m in text for m in "fFxXYOEwWqQ") or any(m in text for m in slp1_markers):
        return text 

    hk_markers = ["kh", "gh", "ch", "jh", "th", "dh", "Th", "Dh", "ph", "bh", "au", "ai", "J", "RR"]
    
    # По умолчанию HK (так как S и z, поменяны в HK и SLP1 и нет возможности их отличить, но чаще все-таки люди используют HK)
    source_scheme = sanscript.HK

    # Пытаемся определить: если есть символы деванагари
    if any('\u0900' <= char <= '\u097F' for char in text):
        source_scheme = sanscript.DEVANAGARI
    # Если есть диакритика (ā, ī, ū, ṃ, ḥ, ṭ, ḍ, ṇ, ś, ṣ) — скорее всего IAST
    elif any(char in "āīūṃḥṭḍṇśṣ" for char in text.lower()):
        source_scheme = sanscript.IAST
    # Если есть характерные придыхания 'h' — скорее всего это HK
    elif any(m in text for m in hk_markers):
        source_scheme = sanscript.HK
    
    return transliterate(text, source_scheme, sanscript.SLP1)