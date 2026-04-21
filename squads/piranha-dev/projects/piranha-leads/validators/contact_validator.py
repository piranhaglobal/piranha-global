"""
Validação de contactos — website, email e telefone.
Nunca gera nem inventa dados. Apenas verifica se o que existe é real.
"""

import re
import socket
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# Prefixos de países europeus válidos → comprimento esperado do número completo (com prefixo)
_COUNTRY_PREFIXES = {
    "+351": (13, 13),  # PT: +351 + 9 dígitos = 13
    "+34":  (12, 12),  # ES: +34 + 9 dígitos = 12 (ex: +34626373074)
    "+33":  (11, 12),  # FR: +33 + 9 dígitos = 12
    "+39":  (12, 13),  # IT: variável
    "+49":  (12, 14),  # DE: variável
    "+44":  (12, 13),  # GB: +44 + 10 dígitos = 13
    "+31":  (11, 12),  # NL: +31 + 9 dígitos
    "+32":  (11, 12),  # BE: variável
    "+41":  (11, 12),  # CH: +41 + 9 dígitos
    "+43":  (11, 13),  # AT: variável
    "+48":  (12, 12),  # PL: +48 + 9 dígitos = 12
    "+420": (12, 12),  # CZ: +420 + 9 dígitos = 12
    "+36":  (11, 12),  # HU: variável
    "+40":  (11, 12),  # RO: variável
    "+30":  (12, 12),  # GR: +30 + 10 dígitos = 12
    "+46":  (11, 12),  # SE: variável
    "+47":  (10, 11),  # NO: variável
    "+45":  (10, 10),  # DK: +45 + 8 dígitos = 10
    "+358": (11, 13),  # FI: variável
    "+353": (11, 12),  # IE: variável
}

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

# Domínios de plataforma que não têm email real associado ao negócio
_PLATFORM_DOMAINS = {
    "sentry.io", "wixpress.com", "example.com", "squarespace.com",
    "wordpress.com", "shopify.com", "instagram.com", "facebook.com",
    "google.com", "w3.org", "schema.org", "apple.com",
}

# Domínios que são links de redes sociais (não são websites do negócio)
_SOCIAL_DOMAINS = {
    "instagram.com", "www.instagram.com",
    "facebook.com", "www.facebook.com",
    "tiktok.com", "www.tiktok.com",
    "linktr.ee", "linktree.com",
    "beacons.ai",
}


# ── Website ──────────────────────────────────────────────────────────────────

def validate_website(url: str | None) -> dict:
    """
    Verifica se o website existe e responde.
    Retorna: {valid: bool, status_code: int|None, reason: str}
    """
    if not url:
        return {"valid": False, "status_code": None, "reason": "empty"}

    # Detectar links de redes sociais usados como website
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower().lstrip("www.")
        if domain in _SOCIAL_DOMAINS:
            return {"valid": False, "status_code": None, "reason": "social_link_not_website"}
    except Exception:
        pass

    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=8,
            allow_redirects=True,
        )
        if resp.status_code in (200, 201, 301, 302, 303, 307, 308):
            return {"valid": True, "status_code": resp.status_code, "reason": "ok"}
        return {"valid": False, "status_code": resp.status_code, "reason": f"http_{resp.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"valid": False, "status_code": None, "reason": "connection_error"}
    except requests.exceptions.Timeout:
        return {"valid": False, "status_code": None, "reason": "timeout"}
    except Exception as e:
        return {"valid": False, "status_code": None, "reason": str(e)[:60]}


# ── Email ─────────────────────────────────────────────────────────────────────

def validate_email(email: str | None) -> dict:
    """
    Verifica se o email tem formato válido e se o domínio tem registo MX.
    Nunca envia nenhum email.
    Retorna: {valid: bool, reason: str}
    """
    if not email:
        return {"valid": False, "reason": "empty"}

    # Formato básico
    if not _EMAIL_REGEX.match(email):
        return {"valid": False, "reason": "invalid_format"}

    domain = email.split("@")[-1].lower()

    # Rejeitar domínio exacto e qualquer subdomínio de plataformas conhecidas
    if domain in _PLATFORM_DOMAINS or any(domain.endswith("." + d) for d in _PLATFORM_DOMAINS):
        return {"valid": False, "reason": "platform_domain"}

    # Verificar MX record (o domínio aceita emails?)
    try:
        import dns.resolver
        dns.resolver.resolve(domain, "MX")
        return {"valid": True, "reason": "mx_ok"}
    except Exception:
        pass

    # Fallback: verificar se o domínio resolve (pelo menos existe)
    try:
        socket.gethostbyname(domain)
        return {"valid": True, "reason": "dns_ok_no_mx"}
    except socket.gaierror:
        return {"valid": False, "reason": "domain_not_found"}


# ── Telefone ──────────────────────────────────────────────────────────────────

def validate_phone(phone: str | None) -> dict:
    """
    Verifica se o telefone tem formato E.164 com prefixo europeu válido.
    Retorna: {valid: bool, reason: str, country: str|None}
    """
    if not phone:
        return {"valid": False, "reason": "empty", "country": None}

    normalized = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    if not normalized.startswith("+"):
        return {"valid": False, "reason": "missing_country_prefix", "country": None}

    # Verificar prefixo de país
    matched_prefix = None
    matched_range = None
    for prefix, length_range in _COUNTRY_PREFIXES.items():
        if normalized.startswith(prefix):
            # Prefixo mais longo ganha (ex: +353 antes de +35)
            if matched_prefix is None or len(prefix) > len(matched_prefix):
                matched_prefix = prefix
                matched_range = length_range

    if not matched_prefix:
        return {"valid": False, "reason": "unknown_country_prefix", "country": None}

    min_len, max_len = matched_range
    if not (min_len <= len(normalized) <= max_len):
        return {
            "valid": False,
            "reason": f"wrong_length_{len(normalized)}_expected_{min_len}-{max_len}",
            "country": matched_prefix,
        }

    # Apenas dígitos após o prefixo
    digits_after = normalized[len(matched_prefix):]
    if not digits_after.isdigit():
        return {"valid": False, "reason": "non_digit_chars", "country": matched_prefix}

    return {"valid": True, "reason": "ok", "country": matched_prefix}


# ── Validação completa de um lead ─────────────────────────────────────────────

def validate_lead_contacts(lead: dict, verbose: bool = False) -> dict:
    """
    Valida website, email e telefone de um lead.
    Retorna dict com resultados e campos limpos (None se inválido).
    Nunca inventa dados — apenas confirma ou limpa o que existe.
    """
    results = {}

    website = lead.get("website")
    email = lead.get("email")
    phone = lead.get("phone")

    w = validate_website(website)
    results["website"] = w
    clean_website = website if w["valid"] else None
    if not w["valid"] and website:
        if verbose:
            print(f"  ✗ website inválido [{w['reason']}]: {website}")

    e = validate_email(email)
    results["email"] = e
    clean_email = email if e["valid"] else None
    if not e["valid"] and email:
        if verbose:
            print(f"  ✗ email inválido [{e['reason']}]: {email}")

    p = validate_phone(phone)
    results["phone"] = p
    clean_phone = phone if p["valid"] else None
    if not p["valid"] and phone:
        if verbose:
            print(f"  ✗ telefone inválido [{p['reason']}]: {phone}")

    return {
        "results": results,
        "clean": {
            "website": clean_website,
            "email": clean_email,
            "phone": clean_phone,
        },
    }
