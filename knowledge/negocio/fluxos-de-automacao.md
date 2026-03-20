# Fluxos de Automação — Piranha Global

## Fluxo 1: Recuperação de Carrinho Abandonado
```
[GATILHO] Shopify: checkout criado há 1h sem compra
    ↓
[VERIFICAÇÃO] Cliente tem telefone cadastrado?
    ↓ SIM
[HORÁRIO] Está no horário permitido (08-20h)?
    ↓ SIM
[ENVIO] Evolution API: mensagem WhatsApp personalizada
    ↓
[LOG] Registrar: número, hora, status de envio
    ↓
[AGUARDAR] 24h sem compra?
    ↓ SIM
[SEGUNDO CONTATO] SMS via Telnyx com cupom 10%
```

## Fluxo 2: Ligação Automatizada de Vendas
```
[GATILHO] Lead qualificado no CRM
    ↓
[CRIAR CHAMADA] Ultravox: criar agente com contexto do lead
    ↓
[LIGAR] Telnyx: discar para o número
    ↓
[CONVERSA] Agente IA conduz a ligação
    ↓
[RESULTADO] Marcar no CRM: interessado/não-interessado/callback
    ↓
[FOLLOW-UP] Se interessado: enviar WhatsApp com proposta
```

## Fluxo 3: Notificação de Pedido
```
[GATILHO] Shopify webhook: order/paid
    ↓
[FORMATAR] Dados do pedido → mensagem personalizada
    ↓
[ENVIAR] Evolution API: WhatsApp de confirmação
    ↓
[AGUARDAR] Shopify webhook: order/fulfilled
    ↓
[ENVIAR] WhatsApp: código de rastreio
```

## Regras de Não-Duplicação
- Guardar IDs de checkouts/pedidos já contatados em arquivo JSON ou banco
- Verificar antes de cada envio se já foi contatado
- Janela de cooldown: 24h entre contatos para o mesmo número

## Exemplo de Controle de Duplicatas
```python
import json
from pathlib import Path

CONTACTED_FILE = Path("contacted.json")

def load_contacted() -> set:
    if CONTACTED_FILE.exists():
        return set(json.loads(CONTACTED_FILE.read_text()))
    return set()

def mark_contacted(identifier: str):
    contacted = load_contacted()
    contacted.add(identifier)
    CONTACTED_FILE.write_text(json.dumps(list(contacted)))

def already_contacted(identifier: str) -> bool:
    return identifier in load_contacted()
```
