"""
Cliente da API BaratoInsta
Gerencia todas as interações com a API de serviços SMM.
"""

import logging
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime

import config
import database

# Configurar logging
logger = logging.getLogger(__name__)


class BaratoInstaAPI:
    """
    Cliente para interação com a API do BaratoInsta.
    
    A API utiliza o padrão comum de APIs SMM Panel com as seguintes ações:
    - services: Lista todos os serviços disponíveis
    - add: Cria um novo pedido
    - status: Consulta o status de um pedido
    - balance: Consulta o saldo da conta
    
    Example:
        >>> api = BaratoInstaAPI()
        >>> servicos = api.listar_servicos()
        >>> pedido = api.criar_pedido(service_id=1, link='https://...', quantidade=1000)
    """
    
    def __init__(self):
        """Inicializa o cliente da API."""
        self.api_url = config.API_URL
        self.api_key = config.API_KEY_BARATOINSTA
        self.timeout = 30  # segundos
        
    def _fazer_requisicao(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Faz uma requisição à API.
        
        Args:
            dados: Dados a serem enviados na requisição
            
        Returns:
            Dict com a resposta da API
            
        Raises:
            APIError: Se houver erro na requisição
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
            logger.debug(f"Resposta API: {resultado}")
            
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
        
        Args:
            usar_cache: Se True, tenta usar o cache antes de consultar a API
            
        Returns:
            Lista de serviços disponíveis
            
        Example:
            >>> api = BaratoInstaAPI()
            >>> servicos = api.listar_servicos()
            >>> print(servicos[0])
            {'service': 1, 'name': 'Seguidores Instagram', 'rate': 10.00, ...}
        """
        # Tentar usar cache
        if usar_cache:
            servicos_cache = database.obter_servicos_cache()
            if servicos_cache:
                logger.info(f"Usando cache: {len(servicos_cache)} serviços")
                return servicos_cache
        
        # Buscar da API
        try:
            resultado = self._fazer_requisicao({'action': 'services'})
            
            if isinstance(resultado, list):
                servicos = resultado
            else:
                servicos = resultado.get('services', [])
            
            # Categorizar serviços
            servicos_categorizados = self._categorizar_servicos(servicos)
            
            # Salvar no cache
            database.salvar_servicos_cache(servicos_categorizados)
            
            logger.info(f"Serviços obtidos da API: {len(servicos_categorizados)}")
            return servicos_categorizados
            
        except APIError:
            # Se falhar, tentar usar cache mesmo expirado
            servicos_cache = database.obter_servicos_cache()
            if servicos_cache:
                logger.warning("Usando cache expirado devido a erro na API")
                return servicos_cache
            raise
    
    def _categorizar_servicos(self, servicos: List[Dict]) -> List[Dict]:
        """
        Categoriza os serviços baseado em palavras-chave.
        
        Args:
            servicos: Lista de serviços da API
            
        Returns:
            Lista de serviços com categoria atualizada
        """
        for servico in servicos:
            nome = servico.get('name', '').lower()
            categoria = servico.get('category', '').lower()
            
            # Tentar identificar categoria por palavras-chave
            categoria_identificada = 'outros'
            
            for cat, keywords in config.KEYWORDS_CATEGORIAS.items():
                if any(kw in nome or kw in categoria for kw in keywords):
                    categoria_identificada = cat
                    break
            
            servico['category'] = categoria_identificada
            
        return servicos
    
    def criar_pedido(
        self, 
        service_id: int, 
        link: str, 
        quantidade: int
    ) -> Dict[str, Any]:
        """
        Cria um novo pedido na API.
        
        Args:
            service_id: ID do serviço
            link: Link do perfil/post
            quantidade: Quantidade desejada
            
        Returns:
            Dict com dados do pedido criado (order_id)
            
        Raises:
            APIError: Se houver erro na criação do pedido
            
        Example:
            >>> api = BaratoInstaAPI()
            >>> resultado = api.criar_pedido(
            ...     service_id=1,
            ...     link='https://instagram.com/usuario',
            ...     quantidade=1000
            ... )
            >>> print(resultado)
            {'order': 12345}
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
        
        Args:
            order_id: ID do pedido na API
            
        Returns:
            Dict com status do pedido
            
        Example:
            >>> api = BaratoInstaAPI()
            >>> status = api.consultar_status(12345)
            >>> print(status)
            {'status': 'In progress', 'start_count': 1500, 'remains': 500}
        """
        dados = {
            'action': 'status',
            'order': order_id
        }
        
        resultado = self._fazer_requisicao(dados)
        logger.info(f"Status do pedido {order_id}: {resultado.get('status')}")
        return resultado
    
    def consultar_status_multiplos(self, order_ids: List[int]) -> Dict[int, Dict]:
        """
        Consulta o status de múltiplos pedidos.
        
        Args:
            order_ids: Lista de IDs de pedidos
            
        Returns:
            Dict mapeando order_id para status
        """
        dados = {
            'action': 'status',
            'orders': ','.join(map(str, order_ids))
        }
        
        resultado = self._fazer_requisicao(dados)
        return resultado
    
    def consultar_saldo(self) -> float:
        """
        Consulta o saldo disponível na conta da API.
        
        Returns:
            float: Saldo disponível
            
        Example:
            >>> api = BaratoInstaAPI()
            >>> saldo = api.consultar_saldo()
            >>> print(saldo)
            150.50
        """
        dados = {'action': 'balance'}
        resultado = self._fazer_requisicao(dados)
        
        saldo = float(resultado.get('balance', 0))
        logger.info(f"Saldo na API: R$ {saldo:.2f}")
        return saldo
    
    def obter_servico(self, service_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém informações de um serviço específico.
        
        Args:
            service_id: ID do serviço
            
        Returns:
            Dict com dados do serviço ou None se não encontrado
        """
        # Primeiro tentar no cache
        servico = database.obter_servico_por_id(service_id)
        if servico:
            return servico
        
        # Se não encontrar, atualizar cache e tentar novamente
        self.listar_servicos(usar_cache=False)
        return database.obter_servico_por_id(service_id)


class APIError(Exception):
    """
    Exceção para erros da API.
    
    Attributes:
        message: Mensagem de erro
    """
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


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
        Lista de categorias
    """
    servicos = listar_servicos()
    categorias = set(s.get('category', 'outros') for s in servicos)
    return sorted(list(categorias))


def obter_servicos_por_categoria(categoria: str) -> List[Dict[str, Any]]:
    """
    Obtém serviços de uma categoria específica.
    
    Args:
        categoria: Nome da categoria
        
    Returns:
        Lista de serviços da categoria
    """
    servicos = listar_servicos()
    return [s for s in servicos if s.get('category', '').lower() == categoria.lower()]
