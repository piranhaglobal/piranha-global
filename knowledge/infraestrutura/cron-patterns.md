# Padrões de Agendamento (Cron)

## Formato
```
* * * * * comando
│ │ │ │ │
│ │ │ │ └── Dia da semana (0-7, 0=Dom)
│ │ │ └──── Mês (1-12)
│ │ └────── Dia do mês (1-31)
│ └──────── Hora (0-23)
└────────── Minuto (0-59)
```

## Exemplos Prontos para Piranha Global

| Frequência | Cron | Uso |
|-----------|------|-----|
| A cada hora | `0 * * * *` | Carrinho abandonado |
| A cada 2 horas | `0 */2 * * *` | Verificação de pedidos |
| Diário às 9h | `0 9 * * *` | Relatório matinal |
| Seg-Sex às 8h | `0 8 * * 1-5` | Lembrete de pedidos |
| A cada 30 min | `*/30 * * * *` | Monitoramento |

## Adicionar ao Crontab na VPS
```bash
# Editar crontab
crontab -e

# Adicionar linha:
0 * * * * cd /home/ubuntu/scripts && /usr/bin/python3 carrinho_abandonado.py >> /var/log/carrinho.log 2>&1
```

## Rodar com Python Virtual Environment
```bash
0 * * * * /home/ubuntu/projetos/meu-script/venv/bin/python /home/ubuntu/projetos/meu-script/src/main.py >> /var/log/meu-script.log 2>&1
```

## Verificar Logs do Cron
```bash
# Ubuntu
grep CRON /var/log/syslog | tail -20

# Ver log específico do script
tail -f /var/log/carrinho.log
```
