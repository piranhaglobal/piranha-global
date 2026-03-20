"""Templates de mensagem WhatsApp — 2 segmentos × 4 idiomas."""


def build_message(
    segment: str,
    language: str,
    customer_name: str,
    consumable_titles: list[str],
) -> str:
    """
    Gera a mensagem final para o cliente no idioma correcto.
    Args:
        segment: "A_B" (comprou consumíveis) | "C" (só não consumíveis)
        language: "pt" | "es" | "fr" | "en"
        customer_name: primeiro nome do cliente
        consumable_titles: títulos dos consumíveis comprados (vazia se seg. C)
    Returns:
        string pronta para envio via Evolution API
    Raises:
        ValueError: segmento ou idioma não suportado
    """
    builders = {
        "A_B": {"pt": _msg_ab_pt, "es": _msg_ab_es, "fr": _msg_ab_fr, "en": _msg_ab_en},
        "C":   {"pt": _msg_c_pt,  "es": _msg_c_es,  "fr": _msg_c_fr,  "en": _msg_c_en},
    }

    if segment not in builders:
        raise ValueError(f"Segmento não suportado: {segment}")
    if language not in builders[segment]:
        raise ValueError(f"Idioma não suportado: {language}")

    if segment == "A_B":
        return builders[segment][language](customer_name, consumable_titles)
    return builders[segment][language](customer_name)


# ─── Segmento A_B — comprou consumíveis ──────────────────────────────────────

def _msg_ab_pt(name: str, titles: list[str]) -> str:
    product_list = _format_product_list(titles)
    return (
        f"Olá {name}! 🦈\n\n"
        f"O ritmo do teu estúdio não pode parar.\n\n"
        f"Já passaram 25 dias desde a tua última encomenda de:\n"
        f"{product_list}\n\n"
        f"Quando os materiais acabam, a agenda pára — e a tua arte fica em suspenso.\n\n"
        f"Repõe o stock em piranhasupplies.com e mantém o fluxo.\n"
        f"Enviamos em 24 horas. 🤘"
    )


def _msg_ab_es(name: str, titles: list[str]) -> str:
    product_list = _format_product_list(titles)
    return (
        f"¡Hola {name}! 🦈\n\n"
        f"El ritmo de tu estudio no puede parar.\n\n"
        f"Han pasado 25 días desde tu último pedido de:\n"
        f"{product_list}\n\n"
        f"Cuando los materiales se acaban, la agenda se detiene — y tu arte queda en suspenso.\n\n"
        f"Repón el stock en piranhasupplies.com y mantén el flujo.\n"
        f"Enviamos en 24 horas. 🤘"
    )


def _msg_ab_fr(name: str, titles: list[str]) -> str:
    product_list = _format_product_list(titles)
    return (
        f"Bonjour {name} ! 🦈\n\n"
        f"Le rythme de ton studio ne peut pas s'arrêter.\n\n"
        f"Cela fait 25 jours depuis ta dernière commande de :\n"
        f"{product_list}\n\n"
        f"Quand les matériaux manquent, l'agenda s'arrête — et ton art reste en suspens.\n\n"
        f"Réapprovisionne ton stock sur piranhasupplies.com et maintiens le flux.\n"
        f"On expédie en 24 heures. 🤘"
    )


def _msg_ab_en(name: str, titles: list[str]) -> str:
    product_list = _format_product_list(titles)
    return (
        f"Hey {name}! 🦈\n\n"
        f"Your studio's rhythm can't stop.\n\n"
        f"It's been 25 days since your last order of:\n"
        f"{product_list}\n\n"
        f"When supplies run out, your schedule stops — and your art is left hanging.\n\n"
        f"Restock at piranhasupplies.com and keep the flow going.\n"
        f"We ship within 24 hours. 🤘"
    )


# ─── Segmento C — só comprou não consumíveis ─────────────────────────────────

def _msg_c_pt(name: str) -> str:
    return (
        f"Olá {name}! 🦈\n\n"
        f"O ritmo de um estúdio bem afinado é tudo.\n\n"
        f"Já tens o equipamento — agora garante que tens os consumíveis certos "
        f"para as tuas próximas sessões.\n\n"
        f"Descobre a nossa colecção em:\n"
        f"piranhasupplies.com/collections/consumables-and-hygiene\n\n"
        f"Enviamos em 24 horas. Mantém a tua arte em evolução. 🤘"
    )


def _msg_c_es(name: str) -> str:
    return (
        f"¡Hola {name}! 🦈\n\n"
        f"El ritmo de un estudio bien afinado lo es todo.\n\n"
        f"Ya tienes el equipo — ahora asegúrate de tener los consumibles correctos "
        f"para tus próximas sesiones.\n\n"
        f"Descubre nuestra colección en:\n"
        f"piranhasupplies.com/collections/consumables-and-hygiene\n\n"
        f"Enviamos en 24 horas. Mantén tu arte en evolución. 🤘"
    )


def _msg_c_fr(name: str) -> str:
    return (
        f"Bonjour {name} ! 🦈\n\n"
        f"Le rythme d'un studio bien réglé, c'est tout.\n\n"
        f"Tu as déjà l'équipement — maintenant assure-toi d'avoir les consommables "
        f"qu'il te faut pour tes prochaines sessions.\n\n"
        f"Découvre notre collection sur :\n"
        f"piranhasupplies.com/collections/consumables-and-hygiene\n\n"
        f"On expédie en 24 heures. Garde ton art en évolution. 🤘"
    )


def _msg_c_en(name: str) -> str:
    return (
        f"Hey {name}! 🦈\n\n"
        f"The rhythm of a well-tuned studio is everything.\n\n"
        f"You've got the gear — now make sure you have the right supplies "
        f"for your next sessions.\n\n"
        f"Explore our collection at:\n"
        f"piranhasupplies.com/collections/consumables-and-hygiene\n\n"
        f"We ship within 24 hours. Keep your art evolving. 🤘"
    )


# ─── Utilitário ──────────────────────────────────────────────────────────────

def _format_product_list(titles: list[str]) -> str:
    """
    Formata lista de produtos como texto para a mensagem.
    Args:
        titles: lista de nomes de produtos
    Returns:
        string com um produto por linha precedido de •
    """
    if not titles:
        return "• (produtos não especificados)"
    return "\n".join(f"• {title}" for title in titles)
