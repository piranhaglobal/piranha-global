#!/usr/bin/env python3
"""
claude_signal.py — Liga o Claude Code à UI Pixel Agents.

Escreve um evento de log no formato que a squad-server lê via polling,
activando o personagem pixel correspondente no canvas da UI.

Uso:
  python3 squads/piranha-dev/claude_signal.py @architect "A analisar o pedido..."
  python3 squads/piranha-dev/claude_signal.py @researcher "A pesquisar documentação..."
  python3 squads/piranha-dev/claude_signal.py @mapper "A mapear ficheiros e funções..."
  python3 squads/piranha-dev/claude_signal.py @dev "A implementar o código..."
  python3 squads/piranha-dev/claude_signal.py @qa "A rever o código..."
  python3 squads/piranha-dev/claude_signal.py --status completed
  python3 squads/piranha-dev/claude_signal.py --reset
"""

import json
import sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
LOGS_FILE = DATA_DIR / "logs.jsonl"
STATE_FILE = DATA_DIR / "state.json"


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    args = sys.argv[1:]

    if not args:
        print("Uso: python3 claude_signal.py @agente 'acção'")
        print("     python3 claude_signal.py --status completed|running|quality_gate|idle")
        print("     python3 claude_signal.py --reset")
        sys.exit(0)

    # --reset: apaga logs e volta ao estado idle
    if "--reset" in args:
        LOGS_FILE.write_text("", encoding="utf-8")
        _save_state({"status": "idle"})
        print("✓ Pipeline reset — UI limpa")
        return

    # --status STATUS: actualiza estado sem adicionar log
    if "--status" in args:
        idx = args.index("--status")
        status = args[idx + 1] if idx + 1 < len(args) else "running"
        state = _load_state()
        state["status"] = status
        _save_state(state)
        print(f"✓ Status → {status}")
        return

    # --gate PROMPT: abre quality gate aguardando aprovação humana
    if "--gate" in args:
        idx = args.index("--gate")
        prompt = args[idx + 1] if idx + 1 < len(args) else "Aprovar para continuar?"
        state = _load_state()
        state["status"] = "quality_gate"
        state["prompt"] = prompt
        state["decision"] = None
        _save_state(state)
        print(f"✓ Quality gate aberta — '{prompt}'")
        return

    # @agente "acção" — o caso principal
    agent = args[0]
    action = args[1] if len(args) > 1 else "A trabalhar..."

    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "action": action,
    }

    with LOGS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    state = _load_state()
    state["status"] = "running"
    _save_state(state)

    print(f"✓ Signal → {agent}: {action}")


if __name__ == "__main__":
    main()
