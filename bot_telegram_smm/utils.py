"""
Módulo de Utilitários
Funções auxiliares utilizadas em todo o projeto.
"""

import re
import hashlib
import logging
import time
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urlparse

import config

# Configurar logging
logger = logging.getLogger(__name__)


def gerar_id_pedido() -> str:
    """
    Gera um ID único para o pedido.
    Formato: PED + timestamp em segundos
    
    Returns:
        str: ID único do pedido (ex: PED1702849372)
        
    Example:
        >>> gerar_id_pedido()
        'PED1702849372'
    """
    timestamp = int(time.time())
    return f"PED{timestamp}"


def calcular_hash_imagem(imagem_bytes: bytes) -> str:
    """
    Calcula o hash MD5 de uma imagem para detecção de duplicatas.
    
    Args:
        imagem_bytes: Bytes da imagem
        
    Returns:
        str: Hash MD5 da imagem
        
    Example:
        >>> calcular_hash_imagem(b'imagem_bytes')
        'a1b2c3d4e5f6...'
    """
    return hashlib.md5(imagem_bytes).hexdigest()


def validar_url(url: str, plataforma: str = None) -> Tuple[bool, str]:
    """
    Valida se uma URL é válida e corresponde à plataforma esperada.
    
    Args:
        url: URL a ser validada
        plataforma: Plataforma esperada (instagram, tiktok, youtube, etc)
        
    Returns:
        Tuple[bool, str]: (é_válida, mensagem_erro)
        
    Example:
        >>> validar_url('https://instagram.com/usuario', 'instagram')
        (True, '')
        >>> validar_url('url_invalida', 'instagram')
        (False, 'URL inválida')
    """
    # Verificar se é uma URL válida
    try:
        resultado = urlparse(url)
        if not all([resultado.scheme, resultado.netloc]):
            return False, "URL inválida. Envie uma URL completa (ex: https://instagram.com/usuario)"
    except Exception:
        return False, "URL inválida. Envie uma URL completa."
    
    # Verificar protocolo
    if resultado.scheme not in ['http', 'https']:
        return False, "URL deve começar com http:// ou https://"
    
    # Validar plataforma específica
    if plataforma:
        dominios_validos = {
            'instagram': ['instagram.com', 'www.instagram.com', 'instagr.am'],
            'tiktok': ['tiktok.com', 'www.tiktok.com', 'vm.tiktok.com'],
            'youtube': ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com'],
            'twitter': ['twitter.com', 'www.twitter.com', 'x.com', 'www.x.com'],
            'facebook': ['facebook.com', 'www.facebook.com', 'fb.com', 'm.facebook.com'],
            'telegram': ['t.me', 'telegram.me'],
            'spotify': ['spotify.com', 'open.spotify.com'],
            'twitch': ['twitch.tv', 'www.twitch.tv']
        }
        
        dominios = dominios_validos.get(plataforma.lower(), [])
        if dominios and resultado.netloc.lower() not in dominios:
            return False, f"URL deve ser do {plataforma.capitalize()}"
    
    return True, ""


def validar_quantidade(quantidade: str, minimo: int, maximo: int) -> Tuple[bool, int, str]:
    """
    Valida se a quantidade está dentro dos limites permitidos.
    
    Args:
        quantidade: Quantidade informada (string)
        minimo: Quantidade mínima permitida
        maximo: Quantidade máxima permitida
        
    Returns:
        Tuple[bool, int, str]: (é_válida, quantidade_int, mensagem_erro)
        
    Example:
        >>> validar_quantidade('1000', 100, 10000)
        (True, 1000, '')
        >>> validar_quantidade('50', 100, 10000)
        (False, 0, 'Quantidade mínima: 100')
    """
    try:
        qtd = int(quantidade.strip().replace('.', '').replace(',', ''))
    except ValueError:
        return False, 0, "Por favor, envie apenas números."
    
    if qtd < minimo:
        return False, 0, f"Quantidade mínima: {minimo:,}".replace(',', '.')
    
    if qtd > maximo:
        return False, 0, f"Quantidade máxima: {maximo:,}".replace(',', '.')
    
    return True, qtd, ""


def formatar_valor(valor: float) -> str:
    """
    Formata um valor monetário no padrão brasileiro.
    
    Args:
        valor: Valor a ser formatado
        
    Returns:
        str: Valor formatado (ex: R$ 1.234,56)
        
    Example:
        >>> formatar_valor(1234.56)
        'R$ 1.234,56'
    """
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def formatar_numero(numero: int) -> str:
    """
    Formata um número com separador de milhares.
    
    Args:
        numero: Número a ser formatado
        
    Returns:
        str: Número formatado (ex: 1.234)
        
    Example:
        >>> formatar_numero(1234)
        '1.234'
    """
    return f"{numero:,}".replace(',', '.')


def extrair_username_instagram(url: str) -> Optional[str]:
    """
    Extrai o nome de usuário de uma URL do Instagram.
    
    Args:
        url: URL do Instagram
        
    Returns:
        str ou None: Nome de usuário ou None se não encontrado
        
    Example:
        >>> extrair_username_instagram('https://instagram.com/usuario')
        'usuario'
    """
    patterns = [
        r'instagram\.com/([a-zA-Z0-9_.]+)',
        r'instagr\.am/([a-zA-Z0-9_.]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            username = match.group(1)
            # Remover partes extras da URL
            username = username.split('/')[0].split('?')[0]
            return username
    
    return None


def extrair_plataforma_url(url: str) -> Optional[str]:
    """
    Identifica a plataforma de uma URL.
    
    Args:
        url: URL a ser analisada
        
    Returns:
        str ou None: Nome da plataforma ou None se não identificada
        
    Example:
        >>> extrair_plataforma_url('https://instagram.com/usuario')
        'instagram'
    """
    try:
        dominio = urlparse(url).netloc.lower()
    except Exception:
        return None
    
    plataformas = {
        'instagram': ['instagram.com', 'instagr.am'],
        'tiktok': ['tiktok.com', 'vm.tiktok.com'],
        'youtube': ['youtube.com', 'youtu.be'],
        'twitter': ['twitter.com', 'x.com'],
        'facebook': ['facebook.com', 'fb.com'],
        'telegram': ['t.me', 'telegram.me'],
        'spotify': ['spotify.com', 'open.spotify.com'],
        'twitch': ['twitch.tv']
    }
    
    for plataforma, dominios in plataformas.items():
        for d in dominios:
            if d in dominio:
                return plataforma
    
    return None


def formatar_data(data: str) -> str:
    """
    Formata uma data ISO para o padrão brasileiro.
    
    Args:
        data: Data em formato ISO (YYYY-MM-DD HH:MM:SS)
        
    Returns:
        str: Data formatada (DD/MM/YYYY HH:MM)
        
    Example:
        >>> formatar_data('2024-01-15 14:30:00')
        '15/01/2024 14:30'
    """
    try:
        dt = datetime.fromisoformat(data.replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return data


def tempo_decorrido(data: str) -> str:
    """
    Calcula o tempo decorrido desde uma data.
    
    Args:
        data: Data em formato ISO
        
    Returns:
        str: Tempo decorrido em formato legível
        
    Example:
        >>> tempo_decorrido('2024-01-15 14:30:00')
        'há 2 horas'
    """
    try:
        dt = datetime.fromisoformat(data.replace('Z', '+00:00'))
        agora = datetime.now()
        diff = agora - dt
        
        segundos = diff.total_seconds()
        
        if segundos < 60:
            return "agora mesmo"
        elif segundos < 3600:
            minutos = int(segundos / 60)
            return f"há {minutos} minuto{'s' if minutos > 1 else ''}"
        elif segundos < 86400:
            horas = int(segundos / 3600)
            return f"há {horas} hora{'s' if horas > 1 else ''}"
        else:
            dias = int(segundos / 86400)
            return f"há {dias} dia{'s' if dias > 1 else ''}"
    except Exception:
        return ""


def sanitizar_texto(texto: str, max_length: int = 100) -> str:
    """
    Remove caracteres especiais e limita o tamanho de um texto.
    
    Args:
        texto: Texto a ser sanitizado
        max_length: Tamanho máximo permitido
        
    Returns:
        str: Texto sanitizado
    """
    # Remover caracteres de controle
    texto = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', texto)
    # Limitar tamanho
    if len(texto) > max_length:
        texto = texto[:max_length] + '...'
    return texto


def obter_emoji_status(status: str) -> str:
    """
    Retorna o emoji correspondente a um status de pedido.
    
    Args:
        status: Status do pedido
        
    Returns:
        str: Emoji correspondente
    """
    emojis = {
        'aguardando_pagamento': '⏳',
        'aguardando_aprovacao': '🔍',
        'pago': '💰',
        'processando': '⚙️',
        'em_progresso': '🔄',
        'concluido': '✅',
        'cancelado': '❌',
        'erro': '⚠️',
        'reembolsado': '💸'
    }
    return emojis.get(status, '📋')


def obter_texto_status(status: str) -> str:
    """
    Retorna o texto amigável correspondente a um status de pedido.
    
    Args:
        status: Status do pedido
        
    Returns:
        str: Texto do status
    """
    textos = {
        'aguardando_pagamento': 'Aguardando Pagamento',
        'aguardando_aprovacao': 'Em Análise',
        'pago': 'Pago',
        'processando': 'Processando',
        'em_progresso': 'Em Progresso',
        'concluido': 'Concluído',
        'cancelado': 'Cancelado',
        'erro': 'Erro',
        'reembolsado': 'Reembolsado'
    }
    return textos.get(status, status.replace('_', ' ').title())


def configurar_logging():
    """
    Configura o sistema de logging do bot.
    """
    # Criar formatador
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para arquivo
    file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configurar logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduzir verbosidade de bibliotecas externas
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    
    logger.info("Sistema de logging configurado")


def truncar_link(link: str, max_length: int = 40) -> str:
    """
    Trunca um link para exibição.
    
    Args:
        link: Link a ser truncado
        max_length: Tamanho máximo
        
    Returns:
        str: Link truncado
    """
    if len(link) <= max_length:
        return link
    return link[:max_length-3] + '...'


def escape_markdown(texto: str) -> str:
    """
    Escapa caracteres especiais do Markdown V2 do Telegram.
    
    Args:
        texto: Texto a ser escapado
        
    Returns:
        str: Texto com caracteres escapados
    """
    caracteres_especiais = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in caracteres_especiais:
        texto = texto.replace(char, f'\\{char}')
    return texto
