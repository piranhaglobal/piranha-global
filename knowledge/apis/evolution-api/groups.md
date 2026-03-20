# Evolution API — Grupos WhatsApp

## Listar Grupos
```
GET /group/fetchAllGroups/{instance}?getParticipants=false
```

## Enviar Mensagem para Grupo
```python
payload = {
    "number": "120363XXXXXXXXXX@g.us",  # JID do grupo
    "text": "Mensagem para o grupo"
}
# Mesmo endpoint: POST /message/sendText/{instance}
```

## Criar Grupo
```
POST /group/create/{instance}
```

```python
payload = {
    "subject": "Nome do Grupo",
    "participants": ["5511999999999", "5511888888888"]
}
```
