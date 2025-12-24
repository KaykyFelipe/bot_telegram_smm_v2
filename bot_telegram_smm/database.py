"""
Módulo de Banco de Dados
Gerencia todas as operações com o banco de dados SQLite.
"""

import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

import config

# Configurar logging
logger = logging.getLogger(__name__)


@contextmanager
def get_connection():
    """
    Context manager para conexão com o banco de dados.
    Garante que a conexão seja fechada após o uso.
    
    Yields:
        sqlite3.Connection: Conexão com o banco de dados
        
    Example:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuarios")
    """
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    
    # Ativar WAL mode para melhor concorrência
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')  # 30 segundos
        conn.execute('PRAGMA synchronous=NORMAL')
    except Exception as e:
        logger.warning(f"Não foi possível ativar WAL mode: {e}")
    
    try:
        yield conn
        conn.commit()
    except sqlite3.OperationalError as e:
        if 'database is locked' in str(e):
            logger.warning(f"Banco de dados travado, ignorando erro")
            try:
                conn.rollback()
            except:
                pass
        else:
            try:
                conn.rollback()
            except:
                pass
            logger.error(f"Erro no banco de dados: {e}")
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        logger.error(f"Erro no banco de dados: {e}")
    finally:
        try:
            conn.close()
        except:
            pass


def inicializar_banco():
    """
    Inicializa o banco de dados criando todas as tabelas necessárias.
    Deve ser chamada na inicialização do bot.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                nome_completo TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_gasto REAL DEFAULT 0,
                total_pedidos INTEGER DEFAULT 0,
                bloqueado INTEGER DEFAULT 0,
                motivo_bloqueio TEXT
            )
        ''')
        
        # Tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id TEXT PRIMARY KEY,
                chat_id INTEGER,
                username TEXT,
                service_id INTEGER,
                servico_nome TEXT,
                categoria TEXT,
                link TEXT,
                quantidade INTEGER,
                preco_api REAL,
                valor_final REAL,
                margem_lucro REAL,
                status TEXT DEFAULT 'aguardando_pagamento',
                order_id_api INTEGER,
                comprovante_hash TEXT,
                tentativas_comprovante INTEGER DEFAULT 0,
                motivo_rejeicao TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_pagamento TIMESTAMP,
                data_conclusao TIMESTAMP,
                dados_extras TEXT,
                FOREIGN KEY (chat_id) REFERENCES usuarios(chat_id)
            )
        ''')
        
        # Tabela de cache de serviços
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servicos_cache (
                service_id INTEGER PRIMARY KEY,
                nome TEXT,
                categoria TEXT,
                tipo TEXT,
                rate REAL,
                min INTEGER,
                max INTEGER,
                descricao TEXT,
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de comprovantes (para detecção de duplicatas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comprovantes (
                hash TEXT PRIMARY KEY,
                pedido_id TEXT,
                chat_id INTEGER,
                data_uso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
            )
        ''')
        
        # Tabela de logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tipo TEXT,
                pedido_id TEXT,
                chat_id INTEGER,
                mensagem TEXT,
                dados_extras TEXT
            )
        ''')
        
        # Criar índices para melhor performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_chat_id ON pedidos(chat_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_tipo ON logs(tipo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_pedido_id ON logs(pedido_id)')
        
        logger.info("Banco de dados inicializado com sucesso")


# ==========================================
# FUNÇÕES DE USUÁRIOS
# ==========================================

def criar_ou_atualizar_usuario(chat_id: int, username: str = None, nome_completo: str = None) -> bool:
    """
    Cria um novo usuário ou atualiza os dados de um existente.
    
    Args:
        chat_id: ID do chat do Telegram
        username: Nome de usuário do Telegram (opcional)
        nome_completo: Nome completo do usuário (opcional)
        
    Returns:
        bool: True se criou novo usuário, False se atualizou existente
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Verificar se usuário existe
        cursor.execute('SELECT chat_id FROM usuarios WHERE chat_id = ?', (chat_id,))
        existe = cursor.fetchone()
        
        if existe:
            # Atualizar dados
            cursor.execute('''
                UPDATE usuarios 
                SET username = COALESCE(?, username),
                    nome_completo = COALESCE(?, nome_completo)
                WHERE chat_id = ?
            ''', (username, nome_completo, chat_id))
            return False
        else:
            # Criar novo usuário
            cursor.execute('''
                INSERT INTO usuarios (chat_id, username, nome_completo)
                VALUES (?, ?, ?)
            ''', (chat_id, username, nome_completo))
            logger.info(f"Novo usuário cadastrado: {chat_id} (@{username})")
            return True


def obter_usuario(chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtém os dados de um usuário.
    
    Args:
        chat_id: ID do chat do Telegram
        
    Returns:
        Dict com dados do usuário ou None se não encontrado
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE chat_id = ?', (chat_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def usuario_bloqueado(chat_id: int) -> bool:
    """
    Verifica se um usuário está bloqueado.
    
    Args:
        chat_id: ID do chat do Telegram
        
    Returns:
        bool: True se bloqueado, False caso contrário
    """
    usuario = obter_usuario(chat_id)
    return usuario and usuario.get('bloqueado', 0) == 1


def bloquear_usuario(chat_id: int, motivo: str):
    """
    Bloqueia um usuário.
    
    Args:
        chat_id: ID do chat do Telegram
        motivo: Motivo do bloqueio
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE usuarios 
            SET bloqueado = 1, motivo_bloqueio = ?
            WHERE chat_id = ?
        ''', (motivo, chat_id))
        logger.warning(f"Usuário {chat_id} bloqueado: {motivo}")


def atualizar_estatisticas_usuario(chat_id: int, valor_gasto: float):
    """
    Atualiza as estatísticas de um usuário após um pedido.
    
    Args:
        chat_id: ID do chat do Telegram
        valor_gasto: Valor do pedido
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE usuarios 
            SET total_gasto = total_gasto + ?,
                total_pedidos = total_pedidos + 1
            WHERE chat_id = ?
        ''', (valor_gasto, chat_id))


# ==========================================
# FUNÇÕES DE PEDIDOS
# ==========================================

def criar_pedido(
    pedido_id: str,
    chat_id: int,
    username: str,
    service_id: int,
    servico_nome: str,
    categoria: str,
    link: str,
    quantidade: int,
    preco_api: float,
    valor_final: float,
    margem_lucro: float
) -> str:
    """
    Cria um novo pedido no banco de dados.
    
    Args:
        pedido_id: ID único do pedido
        chat_id: ID do chat do Telegram
        username: Nome de usuário
        service_id: ID do serviço na API
        servico_nome: Nome do serviço
        categoria: Categoria do serviço
        link: Link do perfil/post
        quantidade: Quantidade solicitada
        preco_api: Preço original da API
        valor_final: Preço final com margem
        margem_lucro: Valor da margem de lucro
        
    Returns:
        str: ID do pedido criado
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pedidos (
                id, chat_id, username, service_id, servico_nome, categoria,
                link, quantidade, preco_api, valor_final, margem_lucro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pedido_id, chat_id, username, service_id, servico_nome, categoria,
            link, quantidade, preco_api, valor_final, margem_lucro
        ))
        
        # Log simplificado para evitar travamento do banco
        logger.info(f"Pedido criado: {pedido_id} para usuário {chat_id} - {servico_nome}")
        return pedido_id


def obter_pedido(pedido_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtém os dados de um pedido.
    
    Args:
        pedido_id: ID do pedido
        
    Returns:
        Dict com dados do pedido ou None se não encontrado
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM pedidos WHERE id = ?', (pedido_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def obter_pedido_aguardando_pagamento(chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtém o pedido mais recente aguardando pagamento de um usuário.
    
    Args:
        chat_id: ID do chat do Telegram
        
    Returns:
        Dict com dados do pedido ou None se não encontrado
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM pedidos 
            WHERE chat_id = ? AND status = 'aguardando_pagamento'
            ORDER BY data_criacao DESC
            LIMIT 1
        ''', (chat_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def listar_pedidos_usuario(chat_id: int, limite: int = 10) -> List[Dict[str, Any]]:
    """
    Lista os pedidos de um usuário.
    
    Args:
        chat_id: ID do chat do Telegram
        limite: Número máximo de pedidos a retornar
        
    Returns:
        Lista de dicts com dados dos pedidos
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM pedidos 
            WHERE chat_id = ?
            ORDER BY data_criacao DESC
            LIMIT ?
        ''', (chat_id, limite))
        return [dict(row) for row in cursor.fetchall()]


def atualizar_status_pedido(
    pedido_id: str, 
    status: str, 
    order_id_api: int = None,
    motivo_rejeicao: str = None
):
    """
    Atualiza o status de um pedido.
    
    Args:
        pedido_id: ID do pedido
        status: Novo status
        order_id_api: ID do pedido na API (opcional)
        motivo_rejeicao: Motivo da rejeição (opcional)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        updates = ['status = ?']
        params = [status]
        
        if order_id_api:
            updates.append('order_id_api = ?')
            params.append(order_id_api)
            
        if motivo_rejeicao:
            updates.append('motivo_rejeicao = ?')
            params.append(motivo_rejeicao)
            
        if status == 'pago':
            updates.append('data_pagamento = ?')
            params.append(datetime.now().isoformat())
        elif status in ['concluido', 'cancelado', 'erro']:
            updates.append('data_conclusao = ?')
            params.append(datetime.now().isoformat())
            
        params.append(pedido_id)
        
        query = f"UPDATE pedidos SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        
        logger.info(f"Pedido {pedido_id} atualizado para status: {status}")


def incrementar_tentativas_comprovante(pedido_id: str) -> int:
    """
    Incrementa o contador de tentativas de comprovante.
    
    Args:
        pedido_id: ID do pedido
        
    Returns:
        int: Número atual de tentativas
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pedidos 
            SET tentativas_comprovante = tentativas_comprovante + 1
            WHERE id = ?
        ''', (pedido_id,))
        
        cursor.execute('SELECT tentativas_comprovante FROM pedidos WHERE id = ?', (pedido_id,))
        row = cursor.fetchone()
        return row[0] if row else 0


def registrar_comprovante_hash(pedido_id: str, hash_comprovante: str):
    """
    Registra o hash de um comprovante no pedido.
    
    Args:
        pedido_id: ID do pedido
        hash_comprovante: Hash MD5 do comprovante
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pedidos 
            SET comprovante_hash = ?
            WHERE id = ?
        ''', (hash_comprovante, pedido_id))


def obter_pedidos_expirados() -> List[Dict[str, Any]]:
    """
    Obtém pedidos que expiraram (aguardando pagamento há mais de 1 hora).
    
    Returns:
        Lista de pedidos expirados
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        limite = datetime.now() - timedelta(seconds=config.TEMPO_EXPIRACAO_PEDIDO)
        cursor.execute('''
            SELECT * FROM pedidos 
            WHERE status = 'aguardando_pagamento'
            AND data_criacao < ?
        ''', (limite.isoformat(),))
        return [dict(row) for row in cursor.fetchall()]


def contar_pedidos_recentes(chat_id: int, horas: int = 1) -> int:
    """
    Conta pedidos de um usuário nas últimas X horas.
    
    Args:
        chat_id: ID do chat do Telegram
        horas: Número de horas para considerar
        
    Returns:
        int: Número de pedidos
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        limite = datetime.now() - timedelta(hours=horas)
        cursor.execute('''
            SELECT COUNT(*) FROM pedidos 
            WHERE chat_id = ? AND data_criacao > ?
        ''', (chat_id, limite.isoformat()))
        return cursor.fetchone()[0]


# ==========================================
# FUNÇÕES DE COMPROVANTES (ANTI-FRAUDE)
# ==========================================

def verificar_comprovante_duplicado(hash_comprovante: str) -> Optional[Dict[str, Any]]:
    """
    Verifica se um comprovante já foi usado anteriormente.
    
    Args:
        hash_comprovante: Hash MD5 do comprovante
        
    Returns:
        Dict com dados do uso anterior ou None se não encontrado
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, p.chat_id as pedido_chat_id, p.valor_final
            FROM comprovantes c
            JOIN pedidos p ON c.pedido_id = p.id
            WHERE c.hash = ?
        ''', (hash_comprovante,))
        row = cursor.fetchone()
        return dict(row) if row else None


def registrar_uso_comprovante(hash_comprovante: str, pedido_id: str, chat_id: int):
    """
    Registra o uso de um comprovante.
    
    Args:
        hash_comprovante: Hash MD5 do comprovante
        pedido_id: ID do pedido
        chat_id: ID do chat do Telegram
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO comprovantes (hash, pedido_id, chat_id)
            VALUES (?, ?, ?)
        ''', (hash_comprovante, pedido_id, chat_id))


# ==========================================
# FUNÇÕES DE CACHE DE SERVIÇOS
# ==========================================

def salvar_servicos_cache(servicos: List[Dict[str, Any]]):
    """
    Salva a lista de serviços no cache.
    
    Args:
        servicos: Lista de serviços da API
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Limpar cache antigo
        cursor.execute('DELETE FROM servicos_cache')
        
        # Inserir novos serviços
        for servico in servicos:
            cursor.execute('''
                INSERT INTO servicos_cache (
                    service_id, nome, categoria, tipo, rate, min, max, descricao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                servico.get('service'),
                servico.get('name'),
                servico.get('category', 'outros'),
                servico.get('type'),
                servico.get('rate'),
                servico.get('min'),
                servico.get('max'),
                servico.get('description', '')
            ))
        
        logger.info(f"Cache de serviços atualizado: {len(servicos)} serviços")


def obter_servicos_cache() -> List[Dict[str, Any]]:
    """
    Obtém os serviços do cache.
    
    Returns:
        Lista de serviços ou lista vazia se cache expirado
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Verificar se cache está válido
        cursor.execute('SELECT MAX(ultima_atualizacao) FROM servicos_cache')
        row = cursor.fetchone()
        
        if row and row[0]:
            ultima_atualizacao = datetime.fromisoformat(row[0])
            if datetime.now() - ultima_atualizacao > timedelta(seconds=config.CACHE_SERVICOS_TTL):
                return []  # Cache expirado
        
        cursor.execute('SELECT * FROM servicos_cache ORDER BY categoria, nome')
        return [dict(row) for row in cursor.fetchall()]


def obter_servico_por_id(service_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtém um serviço específico do cache.
    
    Args:
        service_id: ID do serviço
        
    Returns:
        Dict com dados do serviço ou None se não encontrado
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM servicos_cache WHERE service_id = ?', (service_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def obter_categorias() -> List[str]:
    """
    Obtém lista de categorias únicas dos serviços.
    
    Returns:
        Lista de categorias
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT categoria FROM servicos_cache ORDER BY categoria')
        return [row[0] for row in cursor.fetchall()]


def obter_servicos_por_categoria(categoria: str) -> List[Dict[str, Any]]:
    """
    Obtém serviços de uma categoria específica.
    
    Args:
        categoria: Nome da categoria
        
    Returns:
        Lista de serviços da categoria
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM servicos_cache 
            WHERE categoria = ?
            ORDER BY nome
        ''', (categoria,))
        return [dict(row) for row in cursor.fetchall()]


# ==========================================
# FUNÇÕES DE LOGS
# ==========================================

def registrar_log(
    tipo: str, 
    pedido_id: str = None, 
    chat_id: int = None, 
    mensagem: str = '',
    dados_extras: Dict = None
):
    """
    Registra um log no banco de dados.
    
    Args:
        tipo: Tipo do log (pedido_criado, pagamento, erro, fraude, etc)
        pedido_id: ID do pedido relacionado (opcional)
        chat_id: ID do chat do Telegram (opcional)
        mensagem: Mensagem do log
        dados_extras: Dados adicionais em formato dict (opcional)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs (tipo, pedido_id, chat_id, mensagem, dados_extras)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            tipo, 
            pedido_id, 
            chat_id, 
            mensagem, 
            json.dumps(dados_extras) if dados_extras else None
        ))


def obter_logs(
    tipo: str = None, 
    pedido_id: str = None, 
    chat_id: int = None,
    limite: int = 100
) -> List[Dict[str, Any]]:
    """
    Obtém logs com filtros opcionais.
    
    Args:
        tipo: Filtrar por tipo (opcional)
        pedido_id: Filtrar por pedido (opcional)
        chat_id: Filtrar por usuário (opcional)
        limite: Número máximo de logs
        
    Returns:
        Lista de logs
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        query = 'SELECT * FROM logs WHERE 1=1'
        params = []
        
        if tipo:
            query += ' AND tipo = ?'
            params.append(tipo)
        if pedido_id:
            query += ' AND pedido_id = ?'
            params.append(pedido_id)
        if chat_id:
            query += ' AND chat_id = ?'
            params.append(chat_id)
            
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limite)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# ==========================================
# FUNÇÕES DE ESTATÍSTICAS (ADMIN)
# ==========================================

def obter_estatisticas_gerais() -> Dict[str, Any]:
    """
    Obtém estatísticas gerais do sistema.
    
    Returns:
        Dict com estatísticas
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        stats = {}
        
        # Total de usuários
        cursor.execute('SELECT COUNT(*) FROM usuarios')
        stats['total_usuarios'] = cursor.fetchone()[0]
        
        # Total de pedidos
        cursor.execute('SELECT COUNT(*) FROM pedidos')
        stats['total_pedidos'] = cursor.fetchone()[0]
        
        # Pedidos por status
        cursor.execute('''
            SELECT status, COUNT(*) as total 
            FROM pedidos 
            GROUP BY status
        ''')
        stats['pedidos_por_status'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Faturamento total
        cursor.execute('''
            SELECT SUM(valor_final) FROM pedidos 
            WHERE status IN ('pago', 'processando', 'concluido')
        ''')
        stats['faturamento_total'] = cursor.fetchone()[0] or 0
        
        # Lucro total
        cursor.execute('''
            SELECT SUM(margem_lucro) FROM pedidos 
            WHERE status IN ('pago', 'processando', 'concluido')
        ''')
        stats['lucro_total'] = cursor.fetchone()[0] or 0
        
        # Pedidos hoje
        hoje = datetime.now().date().isoformat()
        cursor.execute('''
            SELECT COUNT(*) FROM pedidos 
            WHERE date(data_criacao) = ?
        ''', (hoje,))
        stats['pedidos_hoje'] = cursor.fetchone()[0]
        
        # Faturamento hoje
        cursor.execute('''
            SELECT SUM(valor_final) FROM pedidos 
            WHERE date(data_criacao) = ?
            AND status IN ('pago', 'processando', 'concluido')
        ''', (hoje,))
        stats['faturamento_hoje'] = cursor.fetchone()[0] or 0
        
        return stats


def obter_pedidos_pendentes_aprovacao() -> List[Dict[str, Any]]:
    """
    Obtém pedidos aguardando aprovação manual do admin.
    
    Returns:
        Lista de pedidos pendentes
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM pedidos 
            WHERE status = 'aguardando_aprovacao'
            ORDER BY data_criacao ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]
