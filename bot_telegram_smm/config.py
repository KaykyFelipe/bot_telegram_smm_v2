"""
Configurações do Bot Telegram SMM
Este arquivo contém todas as configurações necessárias para o funcionamento do bot.
As credenciais sensíveis devem ser configuradas via variáveis de ambiente.
"""

import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# ==========================================
# CONFIGURAÇÕES DO TELEGRAM
# ==========================================

# Token do bot obtido via @BotFather
BOT_TOKEN = os.getenv('BOT_TOKEN', 'seu_token_aqui')

# ID do administrador (para receber notificações e aprovar comprovantes)
ADMIN_ID = int(os.getenv('ADMIN_ID', '123456789'))

# ==========================================
# CONFIGURAÇÕES DA API BARATOINSTA
# ==========================================

# Chave de API do BaratoInsta
API_KEY_BARATOINSTA = os.getenv('API_KEY_BARATOINSTA', 'sua_chave_api')

# URL base da API
API_URL = 'https://baratoinsta.com/api/v2'

# ==========================================
# CONFIGURAÇÕES DE PAGAMENTO PIX
# ==========================================

# Chave PIX para recebimento
CHAVE_PIX = os.getenv('CHAVE_PIX', 'sua-chave@email.com')

# Tipo da chave PIX (email, cpf, telefone, aleatoria)
TIPO_CHAVE_PIX = os.getenv('TIPO_CHAVE_PIX', 'email')

# Nome do beneficiário (aparece no comprovante)
NOME_BENEFICIARIO = os.getenv('NOME_BENEFICIARIO', 'Seu Nome')

# ==========================================
# CONFIGURAÇÕES DE MARGEM DE LUCRO
# ==========================================

# Margem fixa para preços abaixo de R$ 20,00
MARGEM_FIXA = float(os.getenv('MARGEM_FIXA', '4.00'))

# Margem percentual para preços entre R$ 20,00 e R$ 100,00 (25%)
MARGEM_PERCENTUAL_MEDIO = float(os.getenv('MARGEM_PERCENTUAL_MEDIO', '0.25'))

# Margem percentual para preços acima de R$ 100,00 (20%)
MARGEM_PERCENTUAL_ALTO = float(os.getenv('MARGEM_PERCENTUAL_ALTO', '0.20'))

# Limite para aplicar margem fixa
LIMITE_MARGEM_FIXA = float(os.getenv('LIMITE_MARGEM_FIXA', '20.00'))

# Limite para aplicar margem média
LIMITE_MARGEM_MEDIA = float(os.getenv('LIMITE_MARGEM_MEDIA', '100.00'))

# ==========================================
# CONFIGURAÇÕES DE SEGURANÇA
# ==========================================

# Máximo de tentativas de envio de comprovante por pedido
MAX_TENTATIVAS_COMPROVANTE = int(os.getenv('MAX_TENTATIVAS_COMPROVANTE', '3'))

# Máximo de pedidos por usuário por hora
MAX_PEDIDOS_POR_HORA = int(os.getenv('MAX_PEDIDOS_POR_HORA', '5'))

# Tempo de expiração de pedido não pago (em segundos) - 1 hora
TEMPO_EXPIRACAO_PEDIDO = int(os.getenv('TEMPO_EXPIRACAO_PEDIDO', '3600'))

# Tolerância de valor no comprovante (em reais)
TOLERANCIA_VALOR = float(os.getenv('TOLERANCIA_VALOR', '0.10'))

# ==========================================
# CONFIGURAÇÕES DO OCR (TESSERACT)
# ==========================================

# Configuração do Tesseract para português
TESSERACT_CONFIG = '--psm 6 --oem 3 -l por'

# Caminho do executável do Tesseract (deixe vazio para usar o padrão do sistema)
TESSERACT_CMD = os.getenv('TESSERACT_CMD', '')

# ==========================================
# CONFIGURAÇÕES DO BANCO DE DADOS
# ==========================================

# Caminho do arquivo do banco de dados SQLite
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/pedidos.db')

# ==========================================
# CONFIGURAÇÕES DE CACHE
# ==========================================

# Tempo de cache dos serviços da API (em segundos) - 6 horas
CACHE_SERVICOS_TTL = int(os.getenv('CACHE_SERVICOS_TTL', '21600'))

# ==========================================
# CONFIGURAÇÕES DE LOGGING
# ==========================================

# Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Caminho do arquivo de log
LOG_FILE = os.getenv('LOG_FILE', 'data/bot.log')

# ==========================================
# CATEGORIAS DE SERVIÇOS
# ==========================================

# Mapeamento de categorias para exibição amigável
CATEGORIAS = {
    'instagram': '📸 Instagram',
    'tiktok': '🎵 TikTok',
    'youtube': '▶️ YouTube',
    'twitter': '🐦 Twitter/X',
    'facebook': '📘 Facebook',
    'telegram': '✈️ Telegram',
    'spotify': '🎧 Spotify',
    'twitch': '🎮 Twitch',
    'outros': '📦 Outros'
}

# Palavras-chave para categorização automática de serviços
KEYWORDS_CATEGORIAS = {
    'instagram': ['instagram', 'insta', 'ig'],
    'tiktok': ['tiktok', 'tik tok', 'tt'],
    'youtube': ['youtube', 'yt', 'youtuber'],
    'twitter': ['twitter', 'tweet', 'x.com'],
    'facebook': ['facebook', 'fb', 'face'],
    'telegram': ['telegram', 'tg'],
    'spotify': ['spotify'],
    'twitch': ['twitch']
}
