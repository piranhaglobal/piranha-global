"""Formata nomes de produtos técnicos em descrições naturais para voz.

Regra: CATEGORIA + MARCA  →  "máquina de tatuagem da FK Irons"
Evita que o agente pronuncie nomes longos e técnicos que soam robóticos.
Suporte multilingue: pt, es, fr, en.
"""

import re

# ---------------------------------------------------------------------------
# Chaves internas de categoria (idioma-neutras)
# ---------------------------------------------------------------------------

_CAT_MACHINE   = "machine"
_CAT_NEEDLES   = "needles"
_CAT_INK       = "ink"
_CAT_PIERCING  = "piercing"
_CAT_DISPOSABLE = "disposable"
_CAT_SKINCARE  = "skincare"
_CAT_STENCIL   = "stencil"
_CAT_POWER     = "power"
_CAT_ACCESSORIES = "accessories"
_CAT_FURNITURE = "furniture"

# ---------------------------------------------------------------------------
# Mapeamento de categorias por palavras-chave no título
# ---------------------------------------------------------------------------

_CATEGORIAS: list[tuple[str, list[str]]] = [
    (_CAT_MACHINE,    [
        "machine", "máquina", "rotary", "coil", "pen drive", "tattoo pen",
        "adjust", "spektra", "dragonfly", "wireless", "pen x", "pen ii",
        "hawk pen", "hawk thunder", "thunder", "sol nova", "flux", "xion",
        "atom", "ghost", "bishop wand",
    ]),
    (_CAT_NEEDLES,    [
        "needle", "agulha", "cartridge", "cartucho", "needles",
        "equaliser", "equalizer", "neutron", "astral", "stroke",
        "round liner", "round shader", "magnum", "curved magnum", "flat",
        "bugpin", "liner", "shader", "rl", "rs", "rm", "cm", "m1",
        "kwadron", "softedge",
    ]),
    (_CAT_INK,        [
        "ink", "tinta", "pigment", "pigmento", "color", "colour",
        "lining ink", "shading ink", "black lining", "tribal",
        "eternal", "intenze", "dynamic", "radiant", "world famous",
        "kuro sumi", "panthera", "solid ink",
    ]),
    (_CAT_PIERCING,   ["piercing", "jewelry", "jewellery", "joia", "implant", "barbell", "ring"]),
    (_CAT_DISPOSABLE, ["glove", "luva", "mask", "máscara", "barrier", "clip cord", "cover", "sleeve"]),
    (_CAT_SKINCARE,   ["butter", "balm", "lotion", "cream", "soap", "sabão", "aftercare", "healing", "hustle"]),
    (_CAT_STENCIL,    ["stencil", "transfer", "thermal", "freehand", "spirit"]),
    (_CAT_POWER,      ["power supply", "fonte", "power unit"]),
    (_CAT_ACCESSORIES,["grip", "tip", "biqueira", "pedal", "footswitch", "case", "bag", "mala"]),
    (_CAT_FURNITURE,  ["chair", "cadeira", "table", "mesa", "lamp", "luz", "light", "armrest"]),
]

# ---------------------------------------------------------------------------
# Traduções de categoria por idioma
# ---------------------------------------------------------------------------

_TRADUCOES: dict[str, dict[str, str]] = {
    "pt": {
        _CAT_MACHINE:    "máquina de tatuagem",
        _CAT_NEEDLES:    "agulhas",
        _CAT_INK:        "tinta",
        _CAT_PIERCING:   "material de piercing",
        _CAT_DISPOSABLE: "descartáveis",
        _CAT_SKINCARE:   "cuidados com a pele",
        _CAT_STENCIL:    "stencil",
        _CAT_POWER:      "fonte de alimentação",
        _CAT_ACCESSORIES:"acessórios",
        _CAT_FURNITURE:  "mobiliário",
    },
    "es": {
        _CAT_MACHINE:    "máquina de tatuaje",
        _CAT_NEEDLES:    "agujas",
        _CAT_INK:        "tinta",
        _CAT_PIERCING:   "material de piercing",
        _CAT_DISPOSABLE: "desechables",
        _CAT_SKINCARE:   "cuidado de la piel",
        _CAT_STENCIL:    "stencil",
        _CAT_POWER:      "fuente de alimentación",
        _CAT_ACCESSORIES:"accesorios",
        _CAT_FURNITURE:  "mobiliario",
    },
    "fr": {
        _CAT_MACHINE:    "machine à tatouer",
        _CAT_NEEDLES:    "aiguilles",
        _CAT_INK:        "encre",
        _CAT_PIERCING:   "matériel de piercing",
        _CAT_DISPOSABLE: "consommables",
        _CAT_SKINCARE:   "soin de la peau",
        _CAT_STENCIL:    "stencil",
        _CAT_POWER:      "alimentation électrique",
        _CAT_ACCESSORIES:"accessoires",
        _CAT_FURNITURE:  "mobilier",
    },
    "en": {
        _CAT_MACHINE:    "tattoo machine",
        _CAT_NEEDLES:    "needles",
        _CAT_INK:        "ink",
        _CAT_PIERCING:   "piercing supplies",
        _CAT_DISPOSABLE: "disposables",
        _CAT_SKINCARE:   "skincare",
        _CAT_STENCIL:    "stencil",
        _CAT_POWER:      "power supply",
        _CAT_ACCESSORIES:"accessories",
        _CAT_FURNITURE:  "furniture",
    },
}

# Preposição/estrutura "{cat} {prep} {marca}" por idioma
_PREPOSICAO: dict[str, str] = {
    "pt": "da",   # "máquina de tatuagem da FK Irons"
    "es": "de",   # "máquina de tatuaje de FK Irons"
    "fr": "de",   # "machine à tatouer de FK Irons"
    "en": "from", # "tattoo machine from FK Irons"
}

# Fallback "produto da {marca}" por idioma
_PRODUTO_FALLBACK: dict[str, str] = {
    "pt": "produto da {marca}",
    "es": "producto de {marca}",
    "fr": "produit de {marca}",
    "en": "product from {marca}",
}

# Fallback "artigos não especificados" por idioma
_ARTIGOS_FALLBACK: dict[str, str] = {
    "pt": "artigos não especificados",
    "es": "artículos no especificados",
    "fr": "articles non spécifiés",
    "en": "unspecified items",
}

# Conjunção final por idioma
_CONJUNCAO: dict[str, str] = {
    "pt": " e ",
    "es": " y ",
    "fr": " et ",
    "en": " and ",
}

# ---------------------------------------------------------------------------
# Categoria padrão por marca (chaves internas, idioma-neutras)
# ---------------------------------------------------------------------------

_CATEGORIA_POR_MARCA: dict[str, str] = {
    # Máquinas
    "FK Irons": _CAT_MACHINE,
    "Cheyenne": _CAT_MACHINE,
    "Bishop Rotary": _CAT_MACHINE,
    "Microbeau": _CAT_MACHINE,
    "Musotoku": _CAT_MACHINE,
    "Stigma": _CAT_MACHINE,
    "Dragonfly": _CAT_MACHINE,
    "HM Machines": _CAT_MACHINE,
    "Ink Machines": _CAT_MACHINE,
    "Critical": _CAT_MACHINE,
    "Sunskin": _CAT_MACHINE,
    "Bavarian Custom Irons": _CAT_MACHINE,
    "Cyber Tattoo Machines": _CAT_MACHINE,
    "Micky Sharpz": _CAT_MACHINE,
    # Agulhas / cartuchos
    "Kwadron": _CAT_NEEDLES,
    "Hornet": _CAT_NEEDLES,
    "Peak": _CAT_NEEDLES,
    "Inkjecta": _CAT_NEEDLES,
    "Piranha Originals": _CAT_NEEDLES,
    "Silverback": _CAT_NEEDLES,
    # Tintas
    "Eternal Ink": _CAT_INK,
    "Dynamic": _CAT_INK,
    "Intenze": _CAT_INK,
    "Radiant": _CAT_INK,
    "World Famous": _CAT_INK,
    "Kuro Sumi": _CAT_INK,
    "Panthera": _CAT_INK,
    "Solid Ink": _CAT_INK,
    "Perma Blend": _CAT_INK,
    "Inkanto": _CAT_INK,
    "InkTrox": _CAT_INK,
    "Eclipse Tattoo Ink": _CAT_INK,
    "Irezumi": _CAT_INK,
    # Cuidados
    "Hustle Butter": _CAT_SKINCARE,
    "Tattoo Goo": _CAT_SKINCARE,
    "Aloe Tattoo": _CAT_SKINCARE,
    "Easy Tattoo": _CAT_SKINCARE,
    "TattooMed": _CAT_SKINCARE,
    "Inkeeze": _CAT_SKINCARE,
    # Stencil
    "Spirit": _CAT_STENCIL,
    "Clear Cut Stencils": _CAT_STENCIL,
    "InkJet Stencils": _CAT_STENCIL,
}

# ---------------------------------------------------------------------------
# Lista de marcas conhecidas (140 marcas do catálogo Piranha Supplies)
# ---------------------------------------------------------------------------

_MARCAS: list[str] = [
    "A Pound Of Flesh", "Ai-Tenitas", "Aloe Tattoo", "AP Medical", "ArtDriver",
    "Bavarian Custom Irons", "BD Insyte", "Bella", "BIOTAT", "Biotek",
    "Bishop Rotary", "Bode", "Bondhus", "Brother", "Ceia", "Cheyenne",
    "Clear Cut Stencils", "Copic", "Critical", "Cyber Tattoo Machines",
    "Daylight", "DC Invention Company", "Dermaglo", "Dermalogic", "Dettol",
    "DipCap", "Diversos", "Dragon", "DropClean", "Dynamic", "Easy Cleaning",
    "Easy Piercing", "Easy Tattoo", "Eclipse Tattoo Ink", "Ecotat",
    "EGO Pencil Grip", "Eikon", "Electric Dormouse", "Electrum", "Elma",
    "Eternal Ink", "Fisher Space Pen", "FK Irons", "Fraktal", "Glamcor",
    "HM Machines", "Hornet", "Hustle Butter", "Ink Machines", "Inkanto",
    "Inkeeze", "Inkjecta", "InkJet Stencils", "InkTrox", "Intenze",
    "Irezumi", "Kai Medical", "Kosmos", "Kuro Sumi", "Kwadron",
    "Laserlight", "Lauro Paolini", "Lausbube", "Lollifoam", "Mabef",
    "Maimed", "Medical Trading", "META", "Micky Sharpz", "Microbeau",
    "Micromaster", "Mistolin", "Montana Colors", "Morphix", "Musotoku",
    "Nalgene", "Nikko Hurtado", "Nox Violet", "Oil Can Grooming", "OTZI",
    "Ozer", "Panenka", "Panthera", "Peak", "Peli Case", "Pelikan",
    "Perma Blend", "Piranha", "Piranha Global", "Piranha Originals",
    "Pollié", "Posca", "Premier Products", "Protón", "Radiant",
    "Red Apple", "Red Rat Industry", "Reelskin", "Reuzel", "Revolution",
    "Right Stuff", "S8", "Safe Tat", "Saferly", "Search & Rescue",
    "SenseBag", "Sharpie", "Silverback", "Sketch Steam", "SkinProject",
    "Sniper", "Sogeva", "Solid Ink", "Spirit", "Stellar", "Sterilix",
    "Stigma", "Studex", "Sunskin", "Talens", "Tat Soul", "Tat Tech",
    "Tattoo Armour", "Tattoo Goo", "Tattoo Stuff", "TattooMed", "Tesis",
    "The Inked Army", "TIM", "Tombow", "Turanium", "Undone", "Uni-Com",
    "Unigloves", "Unistar", "Uppercut", "Vip Series", "Viscot", "Wildcat",
    "World Famous", "Zinova",
]

# Pré-compilar: marca em minúsculas → nome original (para lookup rápido)
_MARCAS_LOWER: dict[str, str] = {m.lower(): m for m in _MARCAS}


def _identificar_categoria(titulo: str) -> str | None:
    """Devolve a chave interna de categoria com base em palavras-chave no título."""
    titulo_lower = titulo.lower()
    for categoria, keywords in _CATEGORIAS:
        for kw in keywords:
            if kw in titulo_lower:
                return categoria
    return None


def _identificar_marca(titulo: str, vendor: str) -> str | None:
    """
    Devolve o nome da marca.
    Prioridade: campo vendor (se preenchido e reconhecido) > pesquisa no título.
    """
    if vendor:
        vendor_clean = vendor.strip()
        if vendor_clean.lower() in _MARCAS_LOWER:
            return _MARCAS_LOWER[vendor_clean.lower()]
        return vendor_clean

    titulo_lower = titulo.lower()
    marcas_ordenadas = sorted(_MARCAS, key=len, reverse=True)
    for marca in marcas_ordenadas:
        if marca.lower() in titulo_lower:
            return marca

    return None


def _formatar_produto(titulo: str, vendor: str = "", language: str = "pt") -> str:
    """
    Formata um produto individual para voz natural no idioma indicado.

    Exemplos (pt):  "FK Irons One Adjust Tattoo Machine" → "máquina de tatuagem da FK Irons"
    Exemplos (en):  "FK Irons One Adjust Tattoo Machine" → "tattoo machine from FK Irons"
    Exemplos (es):  "Kwadron Cartridge Needles 0.35mm RL" → "agujas de Kwadron"
    """
    lang = language if language in _TRADUCOES else "pt"
    traducoes = _TRADUCOES[lang]
    prep = _PREPOSICAO[lang]

    cat_key = _identificar_categoria(titulo)
    marca = _identificar_marca(titulo, vendor)

    if not cat_key and marca:
        cat_key = _CATEGORIA_POR_MARCA.get(marca)

    categoria = traducoes.get(cat_key, "") if cat_key else ""

    if categoria and marca:
        return f"{categoria} {prep} {marca}"
    if categoria:
        return categoria
    if marca:
        return _PRODUTO_FALLBACK[lang].format(marca=marca)

    # Fallback textual: remover medidas e códigos técnicos
    simplificado = re.sub(r"\d+(\.\d+)?\s*(mm|ml|oz|cm|inch|rl|m1|rs|curved|straight)", "", titulo, flags=re.IGNORECASE)
    simplificado = re.sub(r"\b[A-Z0-9]{4,}\b", "", simplificado)
    simplificado = " ".join(simplificado.split())[:40].strip()
    return simplificado or titulo[:40]


def format_products_for_voice(products: list[dict], language: str = "pt") -> str:
    """
    Converte lista de produtos do checkout num texto natural para o agente de voz.

    Args:
        products: lista de dicts com campos 'title' e opcionalmente 'vendor'
        language: idioma de saída — "pt", "es", "fr" ou "en"

    Returns:
        String legível para voz no idioma indicado.

    Exemplos:
        pt: "máquina de tatuagem da FK Irons e agulhas da Kwadron"
        en: "tattoo machine from FK Irons and needles from Kwadron"
        es: "máquina de tatuaje de FK Irons y agujas de Kwadron"
        fr: "machine à tatouer de FK Irons et aiguilles de Kwadron"
    """
    lang = language if language in _TRADUCOES else "pt"

    if not products:
        return _ARTIGOS_FALLBACK[lang]

    formatados = []
    vistos: set[str] = set()

    for p in products:
        titulo = p.get("title", "").strip()
        vendor = p.get("vendor", "").strip()
        if not titulo:
            continue

        descricao = _formatar_produto(titulo, vendor, lang)

        if descricao not in vistos:
            vistos.add(descricao)
            formatados.append(descricao)

    if not formatados:
        return _ARTIGOS_FALLBACK[lang]

    conj = _CONJUNCAO[lang]
    if len(formatados) == 1:
        return formatados[0]
    return ", ".join(formatados[:-1]) + conj + formatados[-1]
