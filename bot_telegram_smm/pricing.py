"""
Módulo de Precificação
Implementa a lógica de cálculo de preços com margem de lucro.
"""

import logging
from typing import Tuple

import config

# Configurar logging
logger = logging.getLogger(__name__)


def calcular_preco_final(preco_api: float, quantidade: int = None, rate_por_mil: float = None) -> Tuple[float, float, str]:
    """
    Calcula o preço final com margem de lucro aplicada.
    
    A lógica de margem é híbrida:
    - Preço < R$ 20,00: Margem fixa de R$ 4,00
    - Preço >= R$ 20,00 e < R$ 100,00: Margem de 25%
    - Preço >= R$ 100,00: Margem de 20%
    
    Args:
        preco_api: Preço original da API (pode ser o preço total ou rate por 1000)
        quantidade: Quantidade solicitada (opcional, usado se rate_por_mil for fornecido)
        rate_por_mil: Taxa por 1000 unidades (opcional)
        
    Returns:
        Tuple[float, float, str]: (preço_final, margem_lucro, tipo_margem)
        
    Example:
        >>> calcular_preco_final(15.00)
        (19.00, 4.00, 'fixa')
        
        >>> calcular_preco_final(50.00)
        (62.50, 12.50, 'percentual_25')
        
        >>> calcular_preco_final(150.00)
        (180.00, 30.00, 'percentual_20')
        
        >>> calcular_preco_final(rate_por_mil=10.00, quantidade=1000)
        (14.00, 4.00, 'fixa')
    """
    # Calcular preço base se rate_por_mil for fornecido
    if rate_por_mil is not None and quantidade is not None:
        preco_api = (rate_por_mil * quantidade) / 1000
    
    # Aplicar lógica de margem híbrida
    if preco_api < config.LIMITE_MARGEM_FIXA:
        # Margem fixa para preços baixos
        margem = config.MARGEM_FIXA
        tipo_margem = 'fixa'
        
    elif preco_api < config.LIMITE_MARGEM_MEDIA:
        # Margem percentual média (25%)
        margem = preco_api * config.MARGEM_PERCENTUAL_MEDIO
        tipo_margem = 'percentual_25'
        
    else:
        # Margem percentual alta (20%)
        margem = preco_api * config.MARGEM_PERCENTUAL_ALTO
        tipo_margem = 'percentual_20'
    
    preco_final = preco_api + margem
    
    # Arredondar para 2 casas decimais
    preco_final = round(preco_final, 2)
    margem = round(margem, 2)
    
    logger.debug(f"Preço calculado: API={preco_api:.2f}, Margem={margem:.2f} ({tipo_margem}), Final={preco_final:.2f}")
    
    return preco_final, margem, tipo_margem


def calcular_preco_por_quantidade(rate_por_mil: float, quantidade: int) -> Tuple[float, float, float]:
    """
    Calcula o preço para uma quantidade específica.
    
    Args:
        rate_por_mil: Taxa por 1000 unidades (preço da API)
        quantidade: Quantidade desejada
        
    Returns:
        Tuple[float, float, float]: (preco_api, preco_final, margem)
        
    Example:
        >>> calcular_preco_por_quantidade(10.00, 500)
        (5.00, 9.00, 4.00)
        
        >>> calcular_preco_por_quantidade(10.00, 5000)
        (50.00, 62.50, 12.50)
    """
    # Calcular preço proporcional da API
    preco_api = (rate_por_mil * quantidade) / 1000
    preco_api = round(preco_api, 2)
    
    # Calcular preço final com margem
    preco_final, margem, _ = calcular_preco_final(preco_api)
    
    return preco_api, preco_final, margem


def calcular_rate_final(rate_api: float) -> float:
    """
    Calcula a taxa por 1000 com margem aplicada.
    Útil para exibir preços no catálogo.
    
    Args:
        rate_api: Taxa por 1000 da API
        
    Returns:
        float: Taxa por 1000 com margem
        
    Example:
        >>> calcular_rate_final(10.00)
        14.00  # R$ 10 + R$ 4 (margem fixa, pois < R$ 20)
    """
    preco_final, _, _ = calcular_preco_final(rate_api)
    return preco_final


def estimar_lucro(preco_api: float, preco_final: float) -> dict:
    """
    Estima o lucro de uma venda.
    
    Args:
        preco_api: Preço pago à API
        preco_final: Preço cobrado do cliente
        
    Returns:
        Dict com informações de lucro
        
    Example:
        >>> estimar_lucro(10.00, 14.00)
        {'lucro_bruto': 4.00, 'margem_percentual': 40.0}
    """
    lucro_bruto = preco_final - preco_api
    margem_percentual = (lucro_bruto / preco_api * 100) if preco_api > 0 else 0
    
    return {
        'lucro_bruto': round(lucro_bruto, 2),
        'margem_percentual': round(margem_percentual, 1)
    }


def aplicar_desconto(preco: float, percentual: float) -> Tuple[float, float]:
    """
    Aplica um desconto percentual ao preço.
    
    Args:
        preco: Preço original
        percentual: Percentual de desconto (0-100)
        
    Returns:
        Tuple[float, float]: (preco_com_desconto, valor_desconto)
        
    Example:
        >>> aplicar_desconto(100.00, 10)
        (90.00, 10.00)
    """
    if percentual < 0 or percentual > 100:
        raise ValueError("Percentual deve estar entre 0 e 100")
    
    valor_desconto = preco * (percentual / 100)
    preco_com_desconto = preco - valor_desconto
    
    return round(preco_com_desconto, 2), round(valor_desconto, 2)


def formatar_preco_servico(servico: dict) -> str:
    """
    Formata o preço de um serviço para exibição.
    
    Args:
        servico: Dict com dados do serviço (deve conter 'rate')
        
    Returns:
        str: Preço formatado
        
    Example:
        >>> formatar_preco_servico({'rate': 10.00, 'name': 'Seguidores'})
        'R$ 14,00 /1000'
    """
    rate_api = float(servico.get('rate', 0))
    rate_final = calcular_rate_final(rate_api)
    
    return f"R$ {rate_final:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') + " /1000"


def calcular_quantidade_por_valor(rate_por_mil: float, valor_disponivel: float) -> int:
    """
    Calcula a quantidade máxima que pode ser comprada com um valor.
    
    Args:
        rate_por_mil: Taxa por 1000 (com margem já aplicada)
        valor_disponivel: Valor disponível para gastar
        
    Returns:
        int: Quantidade máxima (arredondada para baixo)
        
    Example:
        >>> calcular_quantidade_por_valor(14.00, 50.00)
        3571
    """
    if rate_por_mil <= 0:
        return 0
    
    quantidade = (valor_disponivel * 1000) / rate_por_mil
    return int(quantidade)


# ==========================================
# FUNÇÕES DE RELATÓRIO
# ==========================================

def calcular_resumo_financeiro(pedidos: list) -> dict:
    """
    Calcula um resumo financeiro de uma lista de pedidos.
    
    Args:
        pedidos: Lista de dicts com dados dos pedidos
        
    Returns:
        Dict com resumo financeiro
    """
    total_vendas = sum(p.get('valor_final', 0) for p in pedidos)
    total_custo = sum(p.get('preco_api', 0) for p in pedidos)
    total_lucro = sum(p.get('margem_lucro', 0) for p in pedidos)
    
    margem_media = (total_lucro / total_vendas * 100) if total_vendas > 0 else 0
    
    return {
        'total_vendas': round(total_vendas, 2),
        'total_custo': round(total_custo, 2),
        'total_lucro': round(total_lucro, 2),
        'margem_media': round(margem_media, 1),
        'quantidade_pedidos': len(pedidos)
    }
