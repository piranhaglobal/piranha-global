# Evolution API — Overview

## O que é
API para gerenciar instâncias WhatsApp e enviar mensagens programaticamente.
Auto-hospedada na sua VPS.

## Base URL
```
http://{EVOLUTION_API_URL}
```
Exemplo: `http://sua-vps.dominio.com:8080`

## Autenticação
**Header obrigatório:**
```
apikey: {EVOLUTION_API_KEY}
Content-Type: application/json
```

## Versão
Evolution API v2.x (instância baseada no Baileys/WhatsApp Web)

## Pré-requisito
- Instância criada e conectada ao WhatsApp
- QR Code escaneado pelo celular
- Status da instância: `open` (conectada)

## Documentação Oficial
https://doc.evolution-api.com

## Rate Limits
- Sem limite documentado, mas recomendado: max 60 msg/minuto por instância
- Pause de 1-2 segundos entre mensagens para evitar ban
