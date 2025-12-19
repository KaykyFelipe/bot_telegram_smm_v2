-- ==========================================
-- Bot Telegram SMM - Schema do Banco de Dados
-- ==========================================
-- Este script cria todas as tabelas necessárias para o funcionamento do bot.
-- O banco é criado automaticamente pelo bot, mas este script pode ser usado
-- para referência ou para criar o banco manualmente.

-- Tabela de usuários
CREATE TABLE IF NOT EXISTS usuarios (
    chat_id INTEGER PRIMARY KEY,
    username TEXT,
    nome_completo TEXT,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_gasto REAL DEFAULT 0,
    total_pedidos INTEGER DEFAULT 0,
    bloqueado INTEGER DEFAULT 0,
    motivo_bloqueio TEXT
);

-- Tabela de pedidos
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
);

-- Tabela de cache de serviços da API
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
);

-- Tabela de comprovantes (para detecção de duplicatas)
CREATE TABLE IF NOT EXISTS comprovantes (
    hash TEXT PRIMARY KEY,
    pedido_id TEXT,
    chat_id INTEGER,
    data_uso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
);

-- Tabela de logs
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo TEXT,
    pedido_id TEXT,
    chat_id INTEGER,
    mensagem TEXT,
    dados_extras TEXT
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_pedidos_chat_id ON pedidos(chat_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status);
CREATE INDEX IF NOT EXISTS idx_pedidos_data ON pedidos(data_criacao);
CREATE INDEX IF NOT EXISTS idx_logs_tipo ON logs(tipo);
CREATE INDEX IF NOT EXISTS idx_logs_pedido_id ON logs(pedido_id);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);

-- ==========================================
-- Dados de exemplo (opcional)
-- ==========================================

-- Inserir usuário de teste
-- INSERT INTO usuarios (chat_id, username, nome_completo) 
-- VALUES (123456789, 'usuario_teste', 'Usuário de Teste');

-- ==========================================
-- Consultas úteis
-- ==========================================

-- Ver pedidos pendentes de aprovação
-- SELECT * FROM pedidos WHERE status = 'aguardando_aprovacao';

-- Ver estatísticas de vendas
-- SELECT 
--     COUNT(*) as total_pedidos,
--     SUM(valor_final) as faturamento,
--     SUM(margem_lucro) as lucro
-- FROM pedidos 
-- WHERE status IN ('pago', 'processando', 'concluido');

-- Ver pedidos de hoje
-- SELECT * FROM pedidos WHERE date(data_criacao) = date('now');

-- Ver logs de fraude
-- SELECT * FROM logs WHERE tipo = 'fraude_detectada' ORDER BY timestamp DESC;

-- Limpar pedidos antigos (mais de 30 dias, cancelados)
-- DELETE FROM pedidos 
-- WHERE status = 'cancelado' 
-- AND data_criacao < datetime('now', '-30 days');
