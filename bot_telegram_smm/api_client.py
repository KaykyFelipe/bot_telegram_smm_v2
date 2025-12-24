"""
Cliente da API BaratoInsta
Gerencia todas as interações com a API de serviços SMM.

ATUALIZADO: Categorização automática baseada no nome do serviço,
já que a API retorna todos os serviços em uma única categoria genérica.
"""

import logging
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime

import config
import database

# Configurar logging
logger = logging.getLogger(__name__)


class APIError(Exception):
    """
    Exceção para erros da API.
    
    Attributes:
        message: Mensagem de erro
    """
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


def _detectar_categoria_por_nome(nome_servico: str) -> str:
    """
    Detecta a categoria do serviço baseado no nome.
    
    A API BaratoInsta retorna todos os serviços em uma categoria genérica,
    então precisamos categorizar manualmente pelo nome.
    
    Args:
        nome_servico: Nome do serviço retornado pela API
        
    Returns:
        str: Categoria detectada (instagram, tiktok, youtube, etc.)
    """
    nome_lower = nome_servico.lower()
    
    # Padrões de detecção por rede social (ordem de prioridade)
    padroes = {
        'tiktok': ['tiktok', 'tik tok', 'tiktoker'],
        'youtube': ['youtube', 'youtuber', 'shorts youtube', 'inscrit'],
        'twitter': ['twitter', 'tweet', 'x.com', 'retweet'],
        'facebook': ['facebook', 'fanpage', 'fb '],
        'telegram': ['telegram', 'canal telegram', 'grupo telegram'],
        'spotify': ['spotify', 'playlist spotify', 'ouvintes spotify'],
        'twitch': ['twitch', 'streamer twitch'],
        'kwai': ['kwai'],
        'linkedin': ['linkedin', 'linked in'],
        'instagram': [
            'insta', 'instagram', 'reels', 'igtv', 
            'stories', 'story', 'direct', 'ig '
        ],
    }
    
    # Verificar cada padrão
    for categoria, keywords in padroes.items():
        for keyword in keywords:
            if keyword in nome_lower:
                return categoria
    
    # Se não detectar, verificar palavras genéricas que indicam Instagram
    palavras_instagram = ['seguidor', 'curtida', 'like', 'visualiza', 'comentário']
    for palavra in palavras_instagram:
        if palavra in nome_lower:
            return 'instagram'
    
    return 'outros'


class BaratoInstaAPI:
    """
    Cliente para interação com a API do BaratoInsta.
    """
    
    def __init__(self):
        """Inicializa o cliente da API."""
        self.api_url = config.API_URL
        self.api_key = config.API_KEY_BARATOINSTA
        self.timeout = 30
        self._cache_servicos = []
        self._cache_timestamp = 0
        
    def _fazer_requisicao(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Faz uma requisição à API.
        """
        dados['key'] = self.api_key
        
        try:
            logger.debug(f"Requisição API: {dados.get('action')}")
            
            response = requests.post(
                self.api_url,
                data=dados,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            resultado = response.json()
            logger.debug(f"Resposta API: {type(resultado)}")
            
            # Verificar erro na resposta
            if isinstance(resultado, dict) and resultado.get('error'):
                raise APIError(resultado.get('error'))
                
            return resultado
            
        except requests.exceptions.Timeout:
            logger.error("Timeout na requisição à API")
            raise APIError("Tempo limite excedido. Tente novamente.")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição à API: {e}")
            raise APIError("Erro de conexão com a API. Tente novamente.")
            
        except ValueError as e:
            logger.error(f"Erro ao processar resposta da API: {e}")
            raise APIError("Resposta inválida da API.")
    
    def listar_servicos(self, usar_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Lista todos os serviços disponíveis na API.
        """
        import time
        
        # Verificar cache em memória
        if usar_cache and self._cache_servicos:
            idade_cache = time.time() - self._cache_timestamp
            if idade_cache < config.CACHE_SERVICOS_TTL:
                logger.debug(f"Usando cache de memória ({len(self._cache_servicos)} serviços)")
                return self._cache_servicos
        
        # Buscar da API
        try:
            resultado = self._fazer_requisicao({'action': 'services'})
            
            if isinstance(resultado, list):
                servicos = resultado
            else:
                servicos = resultado.get('services', [])
            
            # Categorizar serviços pelo nome
            servicos_categorizados = self._categorizar_servicos(servicos)
            
            # Salvar no cache de memória
            self._cache_servicos = servicos_categorizados
            self._cache_timestamp = time.time()
            
            logger.info(f"Serviços obtidos da API: {len(servicos_categorizados)}")
            return servicos_categorizados
            
        except APIError:
            # Se falhar, tentar usar cache mesmo expirado
            if self._cache_servicos:
                logger.warning("Usando cache expirado devido a erro na API")
                return self._cache_servicos
            raise
    
    def _categorizar_servicos(self, servicos: List[Dict]) -> List[Dict]:
        """
        Categoriza os serviços baseado no NOME do serviço.
        
        A API BaratoInsta retorna todos os serviços em uma categoria genérica,
        então precisamos detectar a categoria pelo nome.
        """
        servicos_processados = []
        
        for servico in servicos:
            nome = servico.get('name', '')
            
            # Detectar categoria pelo nome
            categoria_detectada = _detectar_categoria_por_nome(nome)
            
            # Criar serviço processado com campos padronizados
            servico_processado = {
                'service_id': servico.get('service'),
                'service': servico.get('service'),
                'nome': nome,
                'name': nome,
                'tipo': servico.get('type', 'Default'),
                'type': servico.get('type', 'Default'),
                'rate': servico.get('rate', '0'),
                'min': servico.get('min', 100),
                'max': servico.get('max', 10000),
                'categoria': categoria_detectada,
                'category': categoria_detectada,
                'categoria_original': servico.get('category', ''),
                'refill': servico.get('refill', False),
                'cancel': servico.get('cancel', False)
            }
            
            servicos_processados.append(servico_processado)
            logger.debug(f"Serviço '{nome[:40]}' -> categoria: {categoria_detectada}")
        
        return servicos_processados
    
    def criar_pedido(
        self, 
        service_id: int, 
        link: str, 
        quantidade: int
    ) -> Dict[str, Any]:
        """
        Cria um novo pedido na API.
        """
        dados = {
            'action': 'add',
            'service': service_id,
            'link': link,
            'quantity': quantidade
        }
        
        resultado = self._fazer_requisicao(dados)
        
        if 'order' not in resultado:
            raise APIError("Resposta inválida: ID do pedido não encontrado")
        
        logger.info(f"Pedido criado na API: {resultado['order']}")
        return resultado
    
    def consultar_status(self, order_id: int) -> Dict[str, Any]:
        """
        Consulta o status de um pedido na API.
        """
        dados = {
            'action': 'status',
            'order': order_id
        }
        
        resultado = self._fazer_requisicao(dados)
        logger.info(f"Status do pedido {order_id}: {resultado.get('status')}")
        return resultado
    
    def consultar_saldo(self) -> float:
        """
        Consulta o saldo disponível na conta da API.
        """
        dados = {'action': 'balance'}
        resultado = self._fazer_requisicao(dados)
        
        saldo = float(resultado.get('balance', 0))
        logger.info(f"Saldo na API: R$ {saldo:.2f}")
        return saldo
    
    def obter_servico(self, service_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém informações de um serviço específico.
        """
        servicos = self.listar_servicos()
        
        for servico in servicos:
            if servico.get('service_id') == service_id or servico.get('service') == service_id:
                return servico
        
        return None


# Instância global do cliente
api_client = BaratoInstaAPI()


# ==========================================
# FUNÇÕES DE CONVENIÊNCIA
# ==========================================

def listar_servicos(usar_cache: bool = True) -> List[Dict[str, Any]]:
    """Wrapper para api_client.listar_servicos()"""
    return api_client.listar_servicos(usar_cache)


def criar_pedido_api(service_id: int, link: str, quantidade: int) -> Dict[str, Any]:
    """Wrapper para api_client.criar_pedido()"""
    return api_client.criar_pedido(service_id, link, quantidade)


def consultar_status_api(order_id: int) -> Dict[str, Any]:
    """Wrapper para api_client.consultar_status()"""
    return api_client.consultar_status(order_id)


def obter_servico(service_id: int) -> Optional[Dict[str, Any]]:
    """Wrapper para api_client.obter_servico()"""
    return api_client.obter_servico(service_id)


def consultar_saldo_api() -> float:
    """Wrapper para api_client.consultar_saldo()"""
    return api_client.consultar_saldo()


def obter_categorias_disponiveis() -> List[str]:
    """
    Obtém lista de categorias com serviços disponíveis.
    
    Returns:
        Lista de categorias ordenadas
    """
    servicos = listar_servicos()
    
    categorias = set()
    for servico in servicos:
        cat = servico.get('categoria', servico.get('category', 'outros'))
        categorias.add(cat)
    
    # Ordenar com categorias principais primeiro
    ordem = ['instagram', 'tiktok', 'youtube', 'twitter', 'facebook', 
             'telegram', 'spotify', 'twitch', 'kwai', 'linkedin', 'outros']
    
    categorias_ordenadas = []
    for cat in ordem:
        if cat in categorias:
            categorias_ordenadas.append(cat)
    
    # Adicionar qualquer categoria não prevista
    for cat in categorias:
        if cat not in categorias_ordenadas:
            categorias_ordenadas.append(cat)
    
    logger.info(f"Categorias disponíveis: {categorias_ordenadas}")
    
    return categorias_ordenadas


def obter_servicos_por_categoria(categoria: str) -> List[Dict[str, Any]]:
    """
    Obtém serviços de uma categoria específica.
    
    Args:
        categoria: Nome da categoria
        
    Returns:
        Lista de serviços da categoria
    """
    servicos = listar_servicos()
    
    filtrados = [
        s for s in servicos 
        if s.get('categoria', s.get('category', '')).lower() == categoria.lower()
    ]
    
    logger.info(f"Categoria '{categoria}': {len(filtrados)} serviços encontrados")
    
    return filtrados
