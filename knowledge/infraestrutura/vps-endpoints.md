# VPS — Endpoints Internos

## API da VPS (Flask Server)
Base URL interna: `http://localhost:5000`
Base URL externa: `https://sua-vps.dominio.com`

## Autenticação
```
Authorization: Bearer {VPS_AUTH_TOKEN}
```

## Endpoints Disponíveis

### Deploy de Script
```
POST /deploy
```
```python
payload = {
    "filename": "carrinho_abandonado.py",
    "code": "import requests\n...",
}
```

### Executar Comando
```
POST /execute
```
```python
payload = {
    "comando": "python3 /scripts/carrinho_abandonado.py"
}
```

### Agendar Cron
```
POST /cron
```
```python
payload = {
    "comando": "python3 /scripts/carrinho_abandonado.py",
    "schedule": "0 * * * *"
}
```

### Ver Logs
```
GET /logs?arquivo=carrinho_abandonado.log&linhas=50
```

## Estrutura de Pastas na VPS
```
/home/ubuntu/
├── scripts/           ← Scripts Python deployados
├── logs/              ← Logs de execução
└── projetos/          ← Projetos completos com venv
```
