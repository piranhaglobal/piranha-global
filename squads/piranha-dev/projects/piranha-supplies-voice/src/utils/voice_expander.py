"""
voice_expander.py — Expande abreviações técnicas em texto natural para voz.

Aplicado às descrições de produtos antes de entrarem no {{productDetails}}
do system prompt, garantindo que o agente pronuncia correctamente unidades,
medidas e termos técnicos do catálogo Piranha Supplies.

Exemplos (PT):
    "3.5mm stroke"    →  "três vírgula cinco milímetros de curso"
    "9-14V"           →  "nove a catorze volts"
    "6.5–8V"          →  "seis vírgula cinco a oito volts"
    "147g"            →  "cento e quarenta e sete gramas"
    "1750mAh"         →  "mil setecentos e cinquenta miliampere-hora"
    "25–150 Hz"       →  "vinte e cinco a cento e cinquenta hertz"
    "4h battery"      →  "quatro horas battery"
    "100%"            →  "cem por cento"
    "BLDC motor"      →  "motor sem escovas"
    "3rl–9rl"         →  "três a nove round liner"
    "5W motor"        →  "cinco watts motor"

Regras de segurança:
    - "2G", "3G" (uppercase G) = designação de produto → nunca expande
    - "pH" = química → mantido intacto
    - "DC", "ISO" = siglas reconhecidas → mantidas intactas
    - Substituições aplicadas em ordem específica para evitar conflitos
      (ex: mAh antes de h, Hz antes de h, ml antes de m, kg antes de g)
"""

import re

# ---------------------------------------------------------------------------
# Conversão de números para palavras (PT)
# ---------------------------------------------------------------------------

_UNITS_PT = [
    "zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete",
    "oito", "nove", "dez", "onze", "doze", "treze", "catorze", "quinze",
    "dezasseis", "dezassete", "dezoito", "dezanove",
]
_TENS_PT = ["", "", "vinte", "trinta", "quarenta", "cinquenta",
            "sessenta", "setenta", "oitenta", "noventa"]
_HUNDREDS_PT = ["", "cento", "duzentos", "trezentos", "quatrocentos",
                "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]


def _int_to_pt(n: int) -> str:
    """Converte inteiro não-negativo (0–9999) para palavras em português europeu."""
    if n == 0:
        return "zero"
    if n == 100:
        return "cem"
    parts = []
    if n >= 1000:
        t = n // 1000
        r = n % 1000
        parts.append("mil" if t == 1 else f"{_int_to_pt(t)} mil")
        if r:
            parts.append(_int_to_pt(r))
        return " e ".join(parts)
    if n >= 100:
        h, r = n // 100, n % 100
        parts.append(_HUNDREDS_PT[h])
        if r:
            parts.append(_int_to_pt(r))
        return " e ".join(parts)
    if n >= 20:
        t, u = n // 10, n % 10
        return _TENS_PT[t] if u == 0 else f"{_TENS_PT[t]} e {_UNITS_PT[u]}"
    return _UNITS_PT[n]


def _num_to_pt(s: str) -> str:
    """
    Converte string numérica (inteiro ou decimal) para palavras em PT.
    Exemplos:
        "3"    → "três"
        "3.5"  → "três vírgula cinco"
        "0.30" → "zero vírgula trinta"
        "150"  → "cento e cinquenta"
    """
    s = s.strip().replace(",", ".")
    if "." in s:
        int_part, dec_part = s.split(".", 1)
        int_word = _int_to_pt(int(int_part)) if int_part else "zero"
        # Decimal digits lidos como número: ".5" → "cinco", ".30" → "trinta"
        dec_word = _int_to_pt(int(dec_part)) if dec_part.lstrip("0") else "zero"
        return f"{int_word} vírgula {dec_word}"
    return _int_to_pt(int(s))


def _range_to_pt(s: str) -> str:
    """
    Converte string de range numérico para palavras em PT.
    Exemplo: "9-14" → "nove a catorze"
             "6.5–8" → "seis vírgula cinco a oito"
    """
    parts = re.split(r"\s*[-–]\s*", s.strip())
    return " a ".join(_num_to_pt(p) for p in parts)


# ---------------------------------------------------------------------------
# Códigos de agulhas de tatuagem
# ---------------------------------------------------------------------------

_NEEDLE_CODES = {
    "RL":  "Round Liner",
    "RS":  "Round Shader",
    "RM":  "Round Magnum",
    "CM":  "Curved Magnum",
    "M1":  "Magnum",
    "MG":  "Magnum",
    "MGT": "Magnum Tight",
    "FT":  "Flat",
    "SC":  "Soft Edge Curved Magnum",
}

# ---------------------------------------------------------------------------
# Substituições por idioma
# Cada entrada: (regex_pattern, replacement_or_callable)
# Ordem é crítica — patterns mais específicos primeiro.
# ---------------------------------------------------------------------------

def _build_rules_pt() -> list:
    """Regras de expansão para português europeu."""

    rules = []

    # 1. BLDC — "BLDC motor" → "motor sem escovas" (evita duplicar a palavra "motor")
    #           "BLDC" isolado → "motor sem escovas"
    rules.append((
        re.compile(r'\bBLDC\s+motor\b', re.IGNORECASE),
        "motor sem escovas",
    ))
    rules.append((
        re.compile(r'\bBLDC\b'),
        "motor sem escovas",
    ))

    # 2. mAh → "miliampere-hora" (antes de m, A, h)
    def _mah_repl(m):
        num = m.group(1)
        word = _num_to_pt(num) if _is_simple_num(num) else num
        return f"{word} miliampere-hora"
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*mAh\b'),
        _mah_repl,
    ))

    # 3. Hz com range → "X a Y hertz" (antes de h)
    def _hz_range_repl(m):
        num = m.group(1)
        sep = m.group(2) if m.lastindex >= 2 else None
        if sep:
            word = _range_to_pt(num + sep + m.group(3))
        else:
            word = _num_to_pt(num) if _is_simple_num(num) else num
        return f"{word} hertz"
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*[Hh]z\b'),
        lambda m: f"{_range_to_pt(m.group(1) + '-' + m.group(3))} hertz",
    ))
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*[Hh]z\b'),
        lambda m: f"{_num_to_pt(m.group(1))} hertz",
    ))

    # 4. Voltagem com range: "9-14V", "6.5–8V"
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*V\b'),
        lambda m: f"{_range_to_pt(m.group(1) + '-' + m.group(3))} volts",
    ))
    # Voltagem simples: "12V"
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*V\b'),
        lambda m: f"{_num_to_pt(m.group(1))} volts",
    ))

    # 5. Watts: "5W"
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*W\b'),
        lambda m: f"{_num_to_pt(m.group(1))} watts",
    ))

    # 6. Milímetros com range: "2.5-4mm", "25-28mm", "0-6mm"
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*mm\b'),
        lambda m: f"{_range_to_pt(m.group(1) + '-' + m.group(3))} milímetros",
    ))
    # Milímetros simples: "3.5mm", "0.30mm", "25mm"
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*mm\b'),
        lambda m: f"{_num_to_pt(m.group(1))} milímetros",
    ))

    # 7. Centímetros: "25cm", "10.9cm"
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*cm\b'),
        lambda m: f"{_num_to_pt(m.group(1))} centímetros",
    ))

    # 8. Mililitros: "15 ml", "220ml" (ml antes de m)
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*m[Ll]\b'),
        lambda m: f"{_num_to_pt(m.group(1))} mililitros",
    ))

    # 9. Litros: "1L", "3L" — mas cuidado com "316L" (aço cirúrgico)
    # Só expande quando é um número isolado antes de L
    rules.append((
        re.compile(r'\b([1-9]\d*(?:[.,]\d+)?)\s*[Ll]\b(?!\w)'),
        lambda m: f"{_num_to_pt(m.group(1))} litros" if int(re.sub(r'[.,]\d+', '', m.group(1))) < 100 else m.group(0),
    ))

    # 10. Quilogramas: "1.5kg" (antes de g)
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*kg\b'),
        lambda m: f"{_num_to_pt(m.group(1))} quilogramas",
    ))

    # 11. Gramas: apenas "g" minúsculo — exclui "2G" de produto (uppercase)
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*g\b(?!\w)'),
        lambda m: f"{_num_to_pt(m.group(1))} gramas",
    ))

    # 12. Horas: "4h", "10h" (após Hz e mAh já tratados)
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*h\b(?!\w)'),
        lambda m: f"{_num_to_pt(m.group(1))} horas",
    ))

    # 13. Percentagem: "100%", "30%"
    rules.append((
        re.compile(r'\b(\d+(?:[.,]\d+)?)\s*%'),
        lambda m: f"{_num_to_pt(m.group(1))} por cento",
    ))

    # 14. Códigos de agulha
    # Range onde o código aparece em ambos os lados: "3rl–9rl" → "três a nove Round Liner"
    needle_pattern = "|".join(re.escape(k) for k in _NEEDLE_CODES)
    rules.append((
        re.compile(rf'\b(\d{{1,2}})\s*({needle_pattern})\s*[-–]\s*(\d{{1,2}})\s*({needle_pattern})\b', re.IGNORECASE),
        lambda m: f"{_range_to_pt(m.group(1) + '-' + m.group(3))} {_NEEDLE_CODES.get(m.group(2).upper(), m.group(2).upper())}",
    ))
    # Range onde o código aparece apenas no fim: "3–9RL" → "três a nove Round Liner"
    rules.append((
        re.compile(rf'\b(\d{{1,2}})\s*[-–]\s*(\d{{1,2}})\s*({needle_pattern})\b', re.IGNORECASE),
        lambda m: f"{_range_to_pt(m.group(1) + '-' + m.group(2))} {_NEEDLE_CODES.get(m.group(3).upper(), m.group(3).upper())}",
    ))
    # Código simples: "3RL" → "três Round Liner"
    rules.append((
        re.compile(rf'\b(\d{{1,2}})\s*({needle_pattern})\b', re.IGNORECASE),
        lambda m: f"{_int_to_pt(int(m.group(1)))} {_NEEDLE_CODES.get(m.group(2).upper(), m.group(2).upper())}",
    ))

    return rules


def _build_rules_es() -> list:
    """Regras para espanhol — expande unidades, mantém números como dígitos."""
    return [
        (re.compile(r'\bmotor\s+BLDC\b', re.IGNORECASE), "motor sin escobillas"),
        (re.compile(r'\bBLDC\s+motor\b', re.IGNORECASE), "motor sin escobillas"),
        (re.compile(r'\bBLDC\b'), "motor sin escobillas"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*mAh\b'), lambda m: f"{m.group(1)} miliamperios-hora"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*[Hh]z\b'), lambda m: f"{m.group(1)}–{m.group(3)} hercios"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*[Hh]z\b'), lambda m: f"{m.group(1)} hercios"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*V\b'), lambda m: f"{m.group(1)}–{m.group(3)} voltios"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*V\b'), lambda m: f"{m.group(1)} voltios"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*W\b'), lambda m: f"{m.group(1)} vatios"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*mm\b'), lambda m: f"{m.group(1)}–{m.group(3)} milímetros"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*mm\b'), lambda m: f"{m.group(1)} milímetros"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*cm\b'), lambda m: f"{m.group(1)} centímetros"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*m[Ll]\b'), lambda m: f"{m.group(1)} mililitros"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*kg\b'), lambda m: f"{m.group(1)} kilogramos"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*g\b(?!\w)'), lambda m: f"{m.group(1)} gramos"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*h\b(?!\w)'), lambda m: f"{m.group(1)} horas"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*%'), lambda m: f"{m.group(1)} por ciento"),
    ]


def _build_rules_fr() -> list:
    """Regras para francês."""
    return [
        (re.compile(r'\bBLDC\s+motor\b', re.IGNORECASE), "moteur sans balais"),
        (re.compile(r'\bBLDC\b'), "moteur sans balais"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*mAh\b'), lambda m: f"{m.group(1)} milliampères-heure"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*[Hh]z\b'), lambda m: f"{m.group(1)}–{m.group(3)} hertz"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*[Hh]z\b'), lambda m: f"{m.group(1)} hertz"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*V\b'), lambda m: f"{m.group(1)}–{m.group(3)} volts"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*V\b'), lambda m: f"{m.group(1)} volts"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*W\b'), lambda m: f"{m.group(1)} watts"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*mm\b'), lambda m: f"{m.group(1)}–{m.group(3)} millimètres"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*mm\b'), lambda m: f"{m.group(1)} millimètres"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*cm\b'), lambda m: f"{m.group(1)} centimètres"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*m[Ll]\b'), lambda m: f"{m.group(1)} millilitres"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*kg\b'), lambda m: f"{m.group(1)} kilogrammes"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*g\b(?!\w)'), lambda m: f"{m.group(1)} grammes"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*h\b(?!\w)'), lambda m: f"{m.group(1)} heures"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*%'), lambda m: f"{m.group(1)} pour cent"),
    ]


def _build_rules_en() -> list:
    """Regras para inglês."""
    return [
        (re.compile(r'\bBLDC\b'), "brushless DC"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*mAh\b'), lambda m: f"{m.group(1)} milliamp-hours"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*[Hh]z\b'), lambda m: f"{m.group(1)} to {m.group(3)} hertz"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*[Hh]z\b'), lambda m: f"{m.group(1)} hertz"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*V\b'), lambda m: f"{m.group(1)} to {m.group(3)} volts"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*V\b'), lambda m: f"{m.group(1)} volts"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*W\b'), lambda m: f"{m.group(1)} watts"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*([-–])\s*(\d+(?:[.,]\d+)?)\s*mm\b'), lambda m: f"{m.group(1)} to {m.group(3)} millimeters"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*mm\b'), lambda m: f"{m.group(1)} millimeters"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*cm\b'), lambda m: f"{m.group(1)} centimeters"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*m[Ll]\b'), lambda m: f"{m.group(1)} milliliters"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*kg\b'), lambda m: f"{m.group(1)} kilograms"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*g\b(?!\w)'), lambda m: f"{m.group(1)} grams"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*h\b(?!\w)'), lambda m: f"{m.group(1)} hours"),
        (re.compile(r'\b(\d+(?:[.,]\d+)?)\s*%'), lambda m: f"{m.group(1)} percent"),
    ]


def _is_simple_num(s: str) -> bool:
    """Verifica se a string é um número simples (inteiro ou decimal)."""
    try:
        float(s.replace(",", "."))
        return True
    except ValueError:
        return False


# Compilar regras uma vez — reutilizadas em todas as chamadas
_RULES: dict[str, list] = {
    "pt": _build_rules_pt(),
    "es": _build_rules_es(),
    "fr": _build_rules_fr(),
    "en": _build_rules_en(),
}


def expand_for_voice(text: str, language: str = "pt") -> str:
    """
    Expande abreviações técnicas num texto de produto para pronúncia natural.

    Args:
        text: descrição limpa do produto (sem HTML)
        language: idioma do agente — "pt", "es", "fr" ou "en"

    Returns:
        texto com abreviações expandidas para o idioma indicado
    """
    if not text:
        return text

    rules = _RULES.get(language, _RULES["pt"])
    result = text

    for pattern, replacement in rules:
        if callable(replacement):
            result = pattern.sub(replacement, result)
        else:
            result = pattern.sub(replacement, result)

    return result
