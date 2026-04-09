#!/usr/bin/env python3
"""
Visualizador de logs de chamadas — Piranha Supplies Voice.

Uso:
    python logs.py                  # todas as chamadas
    python logs.py --status completed
    python logs.py --status no_answer_1
    python logs.py --id 36031105368169   # detalhe de uma chamada
    python logs.py --today              # apenas chamadas de hoje
"""

import argparse
import json
import sys
from datetime import datetime, date
from pathlib import Path

CALLED_FILE = Path(__file__).parent / "called.json"

# Status com labels e cores ANSI
_STATUS_DISPLAY = {
    "called":           ("\033[33m", "EM CURSO"),
    "completed":        ("\033[32m", "CONCLUÍDA"),
    "no_answer_1":      ("\033[35m", "SEM RESP. (1ª)"),
    "no_answer_final":  ("\033[31m", "SEM RESP. FINAL"),
    "error":            ("\033[31m", "ERRO"),
    "already_called_skip": ("\033[90m", "IGNORADO"),
}
_RESET = "\033[0m"
_BOLD  = "\033[1m"
_DIM   = "\033[2m"


def load(path: Path = CALLED_FILE) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("Erro: called.json corrompido.")
        sys.exit(1)


def fmt_dt(iso: str, short: bool = False) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if short:
            return dt.strftime("%d/%m %H:%M")
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso[:16]


def fmt_duration(start: str, end: str) -> str:
    if not start or not end:
        return "—"
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        secs = int((e - s).total_seconds())
        if secs < 0:
            return "—"
        m, s = divmod(secs, 60)
        return f"{m}m{s:02d}s"
    except ValueError:
        return "—"


def status_label(status: str) -> str:
    color, label = _STATUS_DISPLAY.get(status, ("", status.upper()))
    return f"{color}{label}{_RESET}"


def print_summary(data: dict) -> None:
    total = len(data)
    counts = {}
    for r in data.values():
        s = r.get("status", "?")
        counts[s] = counts.get(s, 0) + 1

    print(f"\n{_BOLD}═══ PIRANHA SUPPLIES VOICE — LOG DE CHAMADAS ═══{_RESET}")
    print(f"  Total registos:  {_BOLD}{total}{_RESET}")
    for status, count in sorted(counts.items()):
        label = status_label(status)
        print(f"  {label:<30} {count}")
    print()


def print_table(records: list[tuple[str, dict]]) -> None:
    if not records:
        print("  Nenhum registo encontrado.\n")
        return

    # Cabeçalho
    print(
        f"  {_BOLD}{'CHECKOUT':<16} {'NOME':<12} {'TELEFONE':<16} {'PRODUTOS':<28} "
        f"{'TOTAL':>7} {'DATA CHAMA.':<14} {'DUR.':<8} {'TENT.':>5} STATUS{_RESET}"
    )
    print("  " + "─" * 118)

    for checkout_id, r in records:
        name    = (r.get("name") or "—")[:11]
        phone   = r.get("phone") or "—"
        status  = status_label(r.get("status", "?"))
        attempts = r.get("attempts", 1)
        ts      = fmt_dt(r.get("timestamp", ""), short=True)
        dur     = fmt_duration(r.get("timestamp"), r.get("completed_at"))

        # Produto(s)
        cd = r.get("checkout_data") or {}
        products = cd.get("products") or []
        prod_str = ", ".join(p.get("title", "?")[:24] for p in products[:2])
        if len(products) > 2:
            prod_str += f" +{len(products)-2}"
        prod_str = prod_str[:27]

        total = f"{cd.get('total_price','?')}€" if cd else "—"

        # Resultado do agente (se disponível)
        result = r.get("call_result")
        result_str = ""
        if result:
            resultado = result.get("resultado", "")
            motivo    = result.get("motivo_principal", "")
            result_str = f"\n  {_DIM}  └─ resultado: {resultado} | motivo: {motivo}{_RESET}"

        print(
            f"  {checkout_id:<16} {name:<12} {phone:<16} {prod_str:<28} "
            f"{total:>7} {ts:<14} {dur:<8} {attempts:>5}   {status}"
            + result_str
        )

    print()


def print_detail(checkout_id: str, r: dict) -> None:
    cd = r.get("checkout_data") or {}
    result = r.get("call_result") or {}

    print(f"\n{_BOLD}═══ DETALHE — Checkout #{checkout_id} ═══{_RESET}\n")

    print(f"  {'Cliente':<18} {r.get('name','—')} ({r.get('phone','—')}) — {cd.get('country_code','?')}")
    print(f"  {'Status':<18} {status_label(r.get('status','?'))}")
    print(f"  {'Tentativas':<18} {r.get('attempts', 1)}")
    print(f"  {'Data abandono':<18} {fmt_dt(cd.get('created_at',''))}")
    print(f"  {'Data chamada':<18} {fmt_dt(r.get('timestamp',''))}")
    print(f"  {'Duração':<18} {fmt_duration(r.get('timestamp'), r.get('completed_at'))}")
    print(f"  {'Twilio SID':<18} {r.get('provider_call_id','—')}")
    print(f"  {'Ultravox ID':<18} {r.get('ultravox_call_id','—')}")

    print(f"\n  {_BOLD}Carrinho{_RESET}")
    print(f"  {'Total':<18} {cd.get('total_price','?')}€")
    products = cd.get("products") or []
    for i, p in enumerate(products, 1):
        print(f"  {'Produto ' + str(i):<18} {p.get('title','?')} — {p.get('price','?')}€")

    if result:
        print(f"\n  {_BOLD}Resultado da chamada (agente){_RESET}")
        print(f"  {'Resultado':<18} {result.get('resultado','—')}")
        print(f"  {'Motivo principal':<18} {result.get('motivo_principal','—')}")
        print(f"  {'Sub-motivo':<18} {result.get('sub_motivo','—')}")
        print(f"  {'Registado em':<18} {fmt_dt(result.get('logged_at',''))}")
    else:
        print(f"\n  {_DIM}Resultado da chamada: não disponível (agente não reportou ou chamada não atendida){_RESET}")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Log de chamadas Piranha Supplies Voice")
    parser.add_argument("--status",  help="Filtrar por status: completed, no_answer_1, no_answer_final, error")
    parser.add_argument("--id",      help="Mostrar detalhe de um checkout específico")
    parser.add_argument("--today",   action="store_true", help="Apenas chamadas de hoje")
    parser.add_argument("--file",    default=str(CALLED_FILE), help="Caminho alternativo para called.json")
    args = parser.parse_args()

    called_file = Path(args.file)

    data = load(called_file)
    if not data:
        print("Nenhum registo encontrado em called.json.")
        return

    # Detalhe de um checkout
    if args.id:
        r = data.get(str(args.id))
        if not r:
            print(f"Checkout {args.id} não encontrado.")
            sys.exit(1)
        print_detail(args.id, r)
        return

    # Resumo geral
    print_summary(data)

    # Filtros
    records = list(data.items())

    if args.today:
        today = date.today().isoformat()
        records = [
            (cid, r) for cid, r in records
            if r.get("timestamp", "").startswith(today)
        ]

    if args.status:
        records = [(cid, r) for cid, r in records if r.get("status") == args.status]

    # Ordenar por data (mais recente primeiro)
    records.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)

    print_table(records)


if __name__ == "__main__":
    main()
