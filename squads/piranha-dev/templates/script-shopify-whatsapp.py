"""
Template: Script Shopify + WhatsApp
Use como base para scripts de automação.
Substitua [DESCRICAO] e implemente a lógica específica.
"""

import logging
import time
from src.config import Config
from src.clients.shopify import ShopifyClient
from src.clients.evolution import EvolutionClient
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Ponto de entrada principal."""
    logger.info("Iniciando script Piranha Global")

    # Validar configuração
    Config.validate()

    # Inicializar clientes
    shopify = ShopifyClient()
    evolution = EvolutionClient()

    try:
        # [LÓGICA ESPECÍFICA AQUI]
        # Exemplo: buscar dados da Shopify
        dados = shopify.get_abandoned_checkouts(hours=2)
        logger.info(f"Encontrados {len(dados)} registros")

        # Processar cada registro
        for item in dados:
            try:
                # Formatar mensagem
                mensagem = formatar_mensagem(item)

                # Enviar via WhatsApp
                telefone = item.get("phone", "").replace("+", "").replace("-", "").replace(" ", "")
                if telefone:
                    resultado = evolution.send_text(telefone, mensagem)
                    logger.info(f"Mensagem enviada para {telefone}: {resultado}")

                    # Pausa para evitar rate limit
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Erro ao processar item {item.get('id')}: {e}")
                continue  # Não para, processa o próximo

    except Exception as e:
        logger.error(f"Erro crítico: {e}")
        raise


def formatar_mensagem(dados: dict) -> str:
    """Formata a mensagem baseada nos dados."""
    # [CUSTOMIZE AQUI]
    nome = dados.get("customer", {}).get("first_name", "cliente")
    return f"Olá {nome}! Notamos que você deixou itens no carrinho..."


if __name__ == "__main__":
    main()
