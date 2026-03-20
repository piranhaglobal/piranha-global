# Regras de Mensagem — Piranha Global

## Horários Permitidos para Envio

| Canal | Horário Permitido | Observações |
|-------|------------------|-------------|
| WhatsApp | 08h - 20h | Segunda a Sábado |
| SMS | 08h - 19h | Segunda a Sábado |
| Ligação | 09h - 18h | Segunda a Sexta |

## Tom de Voz
- **Cordial mas direto**: sem excessos de pontuação (!!!!)
- **Personalizado**: sempre use o primeiro nome do cliente
- **Sem pressão**: ofereça, não insista
- **Português informal**: "você" (não "vós"), linguagem do dia a dia

## Templates de Mensagem

### Carrinho Abandonado — WhatsApp
```
Oi {primeiro_nome}!

Notei que você deixou alguns itens no carrinho da [Loja]:

{lista_produtos}

Valor total: R$ {total}

Quer finalizar a compra? Deixei o link aqui embaixo
{link_checkout}

Qualquer dúvida é só responder aqui!
```

### Carrinho Abandonado — SMS
```
[Loja] Oi {primeiro_nome}! Seus itens estão esperando. Total: R$ {total}. Finalize: {link_curto} Responda PARAR para não receber mais.
```

### Confirmação de Pedido — WhatsApp
```
Pedido #{numero} confirmado!

Olá {primeiro_nome}, seu pedido foi recebido com sucesso.

{quantidade} item(s)
Total: R$ {total}
Entrega: {prazo_dias} dias úteis

Acompanhe em: {link_rastreio}
```

## Opt-out / LGPD
- Sempre incluir opção de parar nos SMS ("Responda PARAR")
- Respeitar opt-out imediatamente
- Não enviar para números que bloquearam
- Manter registro de opt-outs em banco de dados
