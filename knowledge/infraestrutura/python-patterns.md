# Padrões Python — Piranha Global

## Requirements.txt Padrão
```
anthropic==0.34.0
requests==2.31.0
python-dotenv==1.0.0
schedule==1.2.2
flask==3.0.0
flask-cors==4.0.0
```

## Estrutura Mínima de Script
```python
#!/usr/bin/env python3
"""Descrição do que o script faz."""

import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Script iniciado")
    # lógica aqui
    logger.info("Script concluído")

if __name__ == "__main__":
    main()
```

## Retry com Backoff Exponencial
```python
import time
import functools

def retry(max_attempts=3, delay=2, backoff=2):
    """Decorator para retry automático."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    wait = delay * (backoff ** attempt)
                    logger.warning(f"Tentativa {attempt+1} falhou: {e}. Aguardando {wait}s...")
                    time.sleep(wait)
        return wrapper
    return decorator

# Uso:
@retry(max_attempts=3, delay=2)
def minha_funcao_que_pode_falhar():
    pass
```
