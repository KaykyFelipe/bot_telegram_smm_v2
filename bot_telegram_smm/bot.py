"""
Bot Telegram SMM - Revenda Automatizada de Serviços de Marketing Digital

Este é o módulo principal do bot que gerencia todas as interações com os usuários
através do Telegram, incluindo navegação por catálogo, processamento de pedidos
e validação de pagamentos via OCR.

IMPORTANTE: Usa ParseMode.HTML para evitar erros com caracteres especiais
nos nomes dos serviços da API (_, *, [, etc.)

Autor: SMM Bot
Versão: 1.1.0
"""

import logging
import html
from datetime import datetime
from typing import Dict, Any

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

import config
import database
import utils
import pricing
from api_client import (
    listar_servicos, 
    criar_pedido_api, 
    consultar_status_api,
    obter_servico,
    obter_categorias_disponiveis,
    obter_servicos_por_categoria,
    consultar_saldo_api,
    APIError
)
from ocr_processor import processar_comprovante

# Configurar logging
logger = logging.getLogger(__name__)

# Estados da conversação
(
    MENU_PRINCIPAL,
    SELECIONAR_CATEGORIA,
    SELECIONAR_SERVICO,
    INSERIR_LINK,
    INSERIR_QUANTIDADE,
    AGUARDANDO_COMPROVANTE,
    AGUARDANDO_APROVACAO
) = range(7)


def escape_html(text: str) -> str:
    """
    Escapa caracteres especiais HTML para evitar erros de parse.
    
    Args:
        text: Texto a ser escapado
        
    Returns:
        str: Texto com caracteres HTML escapados
    """
    if text is None:
        return ""
    return html.escape(str(text))


# ==========================================
# HANDLERS DE COMANDOS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler do comando /start.
    Exibe mensagem de boas-vindas e menu principal.
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Criar ou atualizar usuário no banco
    database.criar_ou_atualizar_usuario(
        chat_id=chat_id,
        username=user.username,
        nome_completo=user.full_name
    )
    
    # Verificar se usuário está bloqueado
    if database.usuario_bloqueado(chat_id):
        await update.message.reply_text(
            "❌ Sua conta está bloqueada. Entre em contato com o suporte."
        )
        return ConversationHandler.END
    
    # Criar teclado do menu principal
    keyboard = [
        [InlineKeyboardButton("📦 Fazer Pedido", callback_data="fazer_pedido")],
        [InlineKeyboardButton("📊 Meus Pedidos", callback_data="meus_pedidos")],
        [InlineKeyboardButton("📋 Serviços", callback_data="listar_servicos")],
        [InlineKeyboardButton("💬 Suporte", callback_data="suporte")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mensagem = """
🎉 <b>Bem-vindo ao SMM Bot!</b>

Somos especializados em serviços de marketing digital para suas redes sociais.

📱 <b>Serviços disponíveis:</b>
• Seguidores
• Curtidas
• Visualizações
• Comentários
• E muito mais!

🔥 <b>Preços competitivos e entrega rápida!</b>

Use os botões abaixo para navegar:
"""
    
    await update.message.reply_text(
        mensagem,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    return MENU_PRINCIPAL


async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler do comando /ajuda."""
    mensagem = """
❓ <b>Central de Ajuda</b>

📌 <b>Comandos disponíveis:</b>

/start - Menu principal
/pedido - Fazer novo pedido
/servicos - Ver todos os serviços
/meuspedidos - Seus pedidos
/status &lt;ID&gt; - Status de um pedido
/ajuda - Esta mensagem
/cancelar - Cancelar operação atual

━━━━━━━━━━━━━━━━━━━━

📖 <b>Como funciona:</b>

1️⃣ Escolha o serviço desejado
2️⃣ Envie o link do perfil/post
3️⃣ Escolha a quantidade
4️⃣ Faça o pagamento via PIX
5️⃣ Envie o comprovante
6️⃣ Aguarde o processamento

━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Dúvidas frequentes:</b>

• Quanto tempo demora?
  → Depende do serviço, geralmente 1-24h

• Posso cancelar?
  → Pedidos pagos não podem ser cancelados

• O perfil precisa estar público?
  → Sim, sempre!
"""
    await update.message.reply_text(mensagem, parse_mode=ParseMode.HTML)


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler do comando /cancelar."""
    # Limpar dados da sessão
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Operação cancelada.\n\nUse /start para voltar ao menu principal."
    )
    
    return ConversationHandler.END


async def status_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler do comando /status <order_id>.
    Consulta o status de um pedido específico.
    """
    chat_id = update.effective_chat.id
    
    # Verificar se foi fornecido um ID
    if not context.args:
        await update.message.reply_text(
            "❓ <b>Como usar:</b>\n<code>/status &lt;ID_DO_PEDIDO&gt;</code>\n\n"
            "Exemplo: <code>/status PED1702849372</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    pedido_id = context.args[0]
    
    # Buscar pedido no banco
    pedido = database.obter_pedido(pedido_id)
    
    if not pedido:
        await update.message.reply_text(
            f"❌ Pedido <code>{escape_html(pedido_id)}</code> não encontrado.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Verificar se o pedido pertence ao usuário (ou é admin)
    if pedido['chat_id'] != chat_id and chat_id != config.ADMIN_ID:
        await update.message.reply_text("❌ Você não tem permissão para ver este pedido.")
        return
    
    # Se tem order_id_api, consultar status na API
    status_api = None
    if pedido.get('order_id_api'):
        try:
            status_api = consultar_status_api(pedido['order_id_api'])
        except APIError as e:
            logger.warning(f"Erro ao consultar status na API: {e}")
    
    # Montar mensagem de status
    emoji = utils.obter_emoji_status(pedido['status'])
    texto_status = utils.obter_texto_status(pedido['status'])
    
    mensagem = f"""
📊 <b>Status do Pedido</b>

🆔 Pedido: <code>{escape_html(pedido['id'])}</code>
💼 Serviço: {escape_html(pedido['servico_nome'])}
📦 Quantidade: {utils.formatar_numero(pedido['quantidade'])}
💰 Valor: {utils.formatar_valor(pedido['valor_final'])}

{emoji} <b>Status:</b> {escape_html(texto_status)}
"""
    
    if status_api:
        if 'start_count' in status_api:
            mensagem += f"\n📈 Iniciado: {status_api.get('start_count', 0)}"
        if 'remains' in status_api:
            mensagem += f"\n📉 Restante: {status_api.get('remains', 0)}"
    
    if pedido.get('data_criacao'):
        mensagem += f"\n\n📅 Criado: {utils.formatar_data(pedido['data_criacao'])}"
    
    await update.message.reply_text(mensagem, parse_mode=ParseMode.HTML)


async def meus_pedidos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler do comando /meuspedidos."""
    chat_id = update.effective_chat.id
    
    pedidos = database.listar_pedidos_usuario(chat_id, limite=10)
    
    if not pedidos:
        await update.message.reply_text(
            "📭 Você ainda não tem pedidos.\n\nUse /start para fazer seu primeiro pedido!"
        )
        return
    
    mensagem = "📋 <b>Seus Últimos Pedidos:</b>\n\n"
    
    for p in pedidos:
        emoji = utils.obter_emoji_status(p['status'])
        texto_status = utils.obter_texto_status(p['status'])
        servico_nome = escape_html(p['servico_nome'][:30]) if p['servico_nome'] else 'N/A'
        mensagem += (
            f"{emoji} <code>{escape_html(p['id'])}</code>\n"
            f"   {servico_nome}\n"
            f"   {utils.formatar_valor(p['valor_final'])} - {escape_html(texto_status)}\n\n"
        )
    
    mensagem += "\n💡 Use <code>/status &lt;ID&gt;</code> para mais detalhes."
    
    await update.message.reply_text(mensagem, parse_mode=ParseMode.HTML)


# ==========================================
# HANDLERS DE CALLBACK (BOTÕES INLINE)
# ==========================================

async def callback_menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para callbacks do menu principal."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "fazer_pedido":
        return await mostrar_categorias(update, context)
    
    elif data == "meus_pedidos":
        return await mostrar_meus_pedidos(update, context)
    
    elif data == "listar_servicos":
        return await mostrar_todos_servicos(update, context)
    
    elif data == "suporte":
        mensagem = """
💬 <b>Suporte</b>

Precisa de ajuda? Entre em contato:

📧 Email: suporte@exemplo.com
📱 Telegram: @suporte

⏰ Horário de atendimento:
Segunda a Sexta: 9h às 18h
"""
        await query.edit_message_text(mensagem, parse_mode=ParseMode.HTML)
        return MENU_PRINCIPAL
    
    elif data == "voltar_menu":
        return await voltar_menu_principal(update, context)
    
    return MENU_PRINCIPAL


async def mostrar_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exibe as categorias de serviços disponíveis."""
    query = update.callback_query
    
    try:
        # Obter categorias que realmente têm serviços
        categorias = obter_categorias_disponiveis()
        
        if not categorias:
            await query.edit_message_text(
                "❌ Nenhum serviço disponível no momento. Tente novamente mais tarde."
            )
            return MENU_PRINCIPAL
        
        # Criar botões apenas para categorias com serviços
        keyboard = []
        for cat in categorias:
            # Verificar se a categoria tem serviços
            servicos_cat = obter_servicos_por_categoria(cat)
            if servicos_cat:
                emoji_cat = config.CATEGORIAS.get(cat, f"📦 {cat.title()}")
                keyboard.append([InlineKeyboardButton(f"{emoji_cat} ({len(servicos_cat)})", callback_data=f"cat_{cat}")])
        
        if not keyboard:
            await query.edit_message_text(
                "❌ Nenhum serviço disponível no momento. Tente novamente mais tarde."
            )
            return MENU_PRINCIPAL
        
        keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu")])
        
        await query.edit_message_text(
            "📂 <b>Selecione uma categoria:</b>\n\nEscolha a rede social para ver os serviços disponíveis:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        
        return SELECIONAR_CATEGORIA
        
    except APIError as e:
        await query.edit_message_text(f"❌ Erro ao carregar serviços: {escape_html(e.message)}")
        return MENU_PRINCIPAL


async def callback_selecionar_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para seleção de categoria."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "voltar_menu":
        return await voltar_menu_principal(update, context)
    
    if data.startswith("cat_"):
        categoria = data[4:]
        context.user_data['categoria'] = categoria
        
        # Obter serviços da categoria
        servicos = obter_servicos_por_categoria(categoria)
        
        if not servicos:
            await query.edit_message_text(
                f"❌ Nenhum serviço disponível nesta categoria."
            )
            return SELECIONAR_CATEGORIA
        
        # Criar botões de serviços (limitar a 20 para não exceder limite do Telegram)
        keyboard = []
        for s in servicos[:20]:
            # Calcular preço com margem
            rate_final = pricing.calcular_rate_final(float(s.get('rate', 0)))
            nome_curto = s.get('nome', s.get('name', 'Serviço'))[:30]
            
            # Limpar nome para evitar problemas
            nome_limpo = nome_curto.replace('_', ' ').replace('*', '').replace('[', '').replace(']', '')
            
            texto_botao = f"{nome_limpo} - R$ {rate_final:.2f}/1k"
            keyboard.append([InlineKeyboardButton(
                texto_botao, 
                callback_data=f"srv_{s.get('service_id', s.get('service'))}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_categorias")])
        
        nome_categoria = config.CATEGORIAS.get(categoria, categoria.title())
        await query.edit_message_text(
            f"📦 <b>Serviços de {escape_html(nome_categoria)}:</b>\n\nSelecione o serviço desejado:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        
        return SELECIONAR_SERVICO
    
    return SELECIONAR_CATEGORIA


async def callback_selecionar_servico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para seleção de serviço."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "voltar_categorias":
        return await mostrar_categorias(update, context)
    
    if data.startswith("srv_"):
        service_id = int(data[4:])
        
        # Obter dados do serviço
        servico = obter_servico(service_id)
        
        if not servico:
            await query.edit_message_text("❌ Serviço não encontrado.")
            return SELECIONAR_SERVICO
        
        # Salvar serviço selecionado
        context.user_data['servico'] = servico
        
        # Responder ao callback
        await query.answer()
        
        # Editar mensagem anterior
        await query.edit_message_text(
            "✅ Serviço selecionado! Agora envie o link.",
            parse_mode=ParseMode.HTML
        )
        
        # Solicitar link em uma nova mensagem
        categoria = servico.get('categoria', servico.get('category', 'instagram'))
        exemplo_links = {
            'instagram': 'https://instagram.com/seu_usuario',
            'tiktok': 'https://www.tiktok.com/@seu_usuario',
            'youtube': 'https://www.youtube.com/@seu_canal',
            'facebook': 'https://www.facebook.com/seu_perfil',
            'twitter': 'https://twitter.com/seu_usuario',
        }
        exemplo = exemplo_links.get(categoria, 'https://instagram.com/seu_usuario')
        
        mensagem = f"""🔗 <b>Envie o link do perfil/post</b>

Por favor, copie e cole o link onde deseja aplicar o serviço:

📌 <b>Exemplo:</b>
<code>{exemplo}</code>

⚠️ <b>Atenção:</b>
• O perfil deve estar PUBLICO
• Copie o link completo da barra de endereço
• Nao use links encurtados
"""
        
        await query.message.reply_text(mensagem, parse_mode=ParseMode.HTML)
        
        return INSERIR_LINK
    
    return SELECIONAR_SERVICO


async def receber_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para receber o link do usuário."""
    link = update.message.text.strip()
    servico = context.user_data.get('servico')
    
    if not servico:
        await update.message.reply_text("❌ Erro: serviço não selecionado. Use /start para recomeçar.")
        return ConversationHandler.END
    
    # Validar URL
    categoria = servico.get('categoria', servico.get('category', ''))
    valido, erro = utils.validar_url(link, categoria)
    
    if not valido:
        await update.message.reply_text(f"❌ {erro}\n\nEnvie um link válido:")
        return INSERIR_LINK
    
    # Salvar link
    context.user_data['link'] = link
    
    # Calcular preço por 1000 com margem
    rate_api = float(servico.get('rate', 0))
    rate_final = pricing.calcular_rate_final(rate_api)
    
    minimo = servico.get('min', 100)
    maximo = servico.get('max', 10000)
    
    # Determinar tipo do serviço
    nome_servico = servico.get('nome', servico.get('name', '')).lower()
    if 'seguidor' in nome_servico:
        tipo = 'seguidores'
    elif 'curtida' in nome_servico or 'like' in nome_servico:
        tipo = 'curtidas'
    elif 'visual' in nome_servico or 'view' in nome_servico:
        tipo = 'visualizações'
    else:
        tipo = 'unidades'
    
    mensagem = f"""
🔢 <b>Quantidade</b>

Quantos {tipo} você deseja?

📊 <b>Limites:</b>
• Mínimo: {utils.formatar_numero(minimo)}
• Máximo: {utils.formatar_numero(maximo)}

💰 <b>Preço por 1000:</b> R$ {rate_final:.2f}
"""
    
    await update.message.reply_text(mensagem, parse_mode=ParseMode.HTML)
    
    return INSERIR_QUANTIDADE


async def receber_quantidade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para receber a quantidade do usuário."""
    try:
        quantidade_texto = update.message.text.strip()
        chat_id = update.effective_chat.id
        
        logger.info(f"[{chat_id}] Recebido quantidade: {quantidade_texto}")
        logger.debug(f"[{chat_id}] user_data keys: {list(context.user_data.keys())}")
        
        # Obter dados da sessão
        servico = context.user_data.get('servico')
        link = context.user_data.get('link')
        
        # Validar dados
        if not servico:
            logger.error(f"[{chat_id}] Serviço não encontrado em user_data")
            await update.message.reply_text(
                "❌ <b>Erro:</b> Serviço não selecionado.\n\n"
                "Use /start para recomeçar o processo.",
                parse_mode=ParseMode.HTML
            )
            return ConversationHandler.END
        
        if not link:
            logger.error(f"[{chat_id}] Link não encontrado em user_data")
            await update.message.reply_text(
                "❌ <b>Erro:</b> Link não fornecido.\n\n"
                "Use /start para recomeçar o processo.",
                parse_mode=ParseMode.HTML
            )
            return ConversationHandler.END
        
        # Obter limites
        minimo = servico.get('min', 100)
        maximo = servico.get('max', 10000)
        
        logger.debug(f"[{chat_id}] Validando: '{quantidade_texto}' (min: {minimo}, max: {maximo})")
        
        # Validar quantidade
        valido, quantidade, erro = utils.validar_quantidade(quantidade_texto, minimo, maximo)
        
        if not valido:
            logger.warning(f"[{chat_id}] Quantidade inválida: {erro}")
            await update.message.reply_text(
                f"❌ <b>Quantidade Inválida</b>\n\n"
                f"{erro}\n\n"
                f"📊 <b>Limites:</b>\n"
                f"• Mínimo: {utils.formatar_numero(minimo)}\n"
                f"• Máximo: {utils.formatar_numero(maximo)}\n\n"
                f"Por favor, envie um número válido:",
                parse_mode=ParseMode.HTML
            )
            return INSERIR_QUANTIDADE
        
        logger.info(f"[{chat_id}] Quantidade válida: {quantidade}")
        
        # Verificar limite de pedidos por hora
        pedidos_recentes = database.contar_pedidos_recentes(chat_id)
        
        if pedidos_recentes >= config.MAX_PEDIDOS_POR_HORA:
            logger.warning(f"[{chat_id}] Limite de pedidos por hora excedido")
            await update.message.reply_text(
                f"⚠️ <b>Limite Atingido</b>\n\n"
                f"Você já fez {pedidos_recentes} pedidos nesta hora.\n"
                f"Limite: {config.MAX_PEDIDOS_POR_HORA} pedidos/hora\n\n"
                f"Aguarde um pouco antes de fazer novos pedidos.",
                parse_mode=ParseMode.HTML
            )
            return ConversationHandler.END
        
        # Calcular preços
        rate_api = float(servico.get('rate', 0))
        preco_api, preco_final, margem = pricing.calcular_preco_por_quantidade(rate_api, quantidade)
        
        logger.info(f"[{chat_id}] Preços calculados: API={preco_api:.2f}, Final={preco_final:.2f}, Margem={margem:.2f}")
        
        # Gerar ID do pedido
        pedido_id = utils.gerar_id_pedido()
        
        # Criar pedido no banco
        database.criar_pedido(
            pedido_id=pedido_id,
            chat_id=chat_id,
            username=update.effective_user.username or '',
            service_id=servico.get('service_id', servico.get('service')),
            servico_nome=servico.get('nome', servico.get('name', 'Serviço')),
            categoria=servico.get('categoria', servico.get('category', '')),
            link=link,
            quantidade=quantidade,
            preco_api=preco_api,
            valor_final=preco_final,
            margem_lucro=margem
        )
        
        logger.info(f"[{chat_id}] Pedido criado no banco: {pedido_id}")
        
        # Salvar pedido na sessão
        context.user_data['pedido_id'] = pedido_id
        context.user_data['valor_final'] = preco_final
        
        # Obter nome do serviço de forma segura
        servico_nome = escape_html(servico.get('nome', servico.get('name', 'Serviço')))
        link_truncado = escape_html(utils.truncar_link(link))
        
        # Exibir resumo do pedido
        mensagem = f"""
📋 <b>RESUMO DO PEDIDO</b>

🆔 Pedido: <code>{pedido_id}</code>
💼 Serviço: {servico_nome}
🔗 Link: {link_truncado}
📦 Quantidade: {utils.formatar_numero(quantidade)}
💰 Valor: R$ {preco_final:.2f}

━━━━━━━━━━━━━━━━━━━━

💳 <b>DADOS PARA PAGAMENTO</b>

📱 Chave PIX: <code>{config.CHAVE_PIX}</code>
💵 Valor exato: <b>R$ {preco_final:.2f}</b>

━━━━━━━━━━━━━━━━━━━━

⚠️ <b>IMPORTANTE:</b>
1️⃣ Faça o PIX com o valor <b>exato</b>
2️⃣ Após pagar, envie o <b>print do comprovante</b>
3️⃣ A validação é automática (2-5 segundos)

⏰ Você tem <b>1 hora</b> para efetuar o pagamento.
"""
        
        await update.message.reply_text(mensagem, parse_mode=ParseMode.HTML)
        
        logger.info(f"[{chat_id}] Resumo do pedido enviado. Aguardando comprovante.")
        
        return AGUARDANDO_COMPROVANTE
        
    except Exception as e:
        logger.error(f"[{chat_id}] Erro em receber_quantidade: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ <b>Erro ao processar quantidade</b>\n\n"
            "Ocorreu um erro inesperado. Use /start para recomeçar.",
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END



async def receber_comprovante(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para receber e processar o comprovante de pagamento."""
    chat_id = update.effective_chat.id
    pedido_id = context.user_data.get('pedido_id')
    
    # Verificar se tem pedido aguardando
    if not pedido_id:
        # Tentar buscar pedido aguardando pagamento
        pedido = database.obter_pedido_aguardando_pagamento(chat_id)
        if pedido:
            pedido_id = pedido['id']
            context.user_data['pedido_id'] = pedido_id
        else:
            await update.message.reply_text(
                "❌ Nenhum pedido aguardando pagamento.\n\nUse /start para fazer um novo pedido."
            )
            return ConversationHandler.END
    
    # Obter pedido do banco
    pedido = database.obter_pedido(pedido_id)
    
    if not pedido:
        await update.message.reply_text("❌ Pedido não encontrado.")
        return ConversationHandler.END
    
    # Verificar tentativas
    tentativas = pedido.get('tentativas_comprovante', 0)
    if tentativas >= config.MAX_TENTATIVAS_COMPROVANTE:
        await update.message.reply_text(
            "❌ Número máximo de tentativas excedido.\n"
            "Entre em contato com o suporte: /ajuda"
        )
        database.atualizar_status_pedido(pedido_id, 'cancelado', motivo_rejeicao='Excedeu tentativas')
        return ConversationHandler.END
    
    # Verificar se é uma foto
    if not update.message.photo:
        await update.message.reply_text(
            "📸 Por favor, envie uma <b>foto</b> do comprovante PIX.",
            parse_mode=ParseMode.HTML
        )
        return AGUARDANDO_COMPROVANTE
    
    # Informar que está processando
    msg_processando = await update.message.reply_text(
        "⏳ <b>Analisando comprovante...</b>\n\nPor favor, aguarde alguns segundos.",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Baixar a foto (maior resolução disponível)
        foto = update.message.photo[-1]
        arquivo = await foto.get_file()
        imagem_bytes = await arquivo.download_as_bytearray()
        
        # Incrementar tentativas
        database.incrementar_tentativas_comprovante(pedido_id)
        tentativas_restantes = config.MAX_TENTATIVAS_COMPROVANTE - tentativas - 1
        
        # Processar comprovante via OCR
        resultado = processar_comprovante(bytes(imagem_bytes), pedido)
        
        # Deletar mensagem de processamento
        await msg_processando.delete()
        
        if resultado['aprovacao_automatica']:
            # Aprovação automática - processar pedido na API
            return await processar_pedido_aprovado(update, context, pedido)
            
        elif resultado['valido']:
            # Enviar para aprovação manual
            database.atualizar_status_pedido(pedido_id, 'aguardando_aprovacao')
            
            await update.message.reply_text(
                "⚠️ <b>Comprovante em Análise</b>\n\n"
                "Seu comprovante foi enviado para verificação manual.\n\n"
                "🕐 Tempo estimado: até 5 minutos\n\n"
                "Você será notificado assim que a análise for concluída.",
                parse_mode=ParseMode.HTML
            )
            
            # Notificar admin
            await notificar_admin_aprovacao(context, pedido, resultado, imagem_bytes)
            
            return AGUARDANDO_APROVACAO
            
        else:
            # Comprovante inválido
            await update.message.reply_text(
                f"❌ <b>Comprovante Inválido</b>\n\n"
                f"Motivo: {escape_html(resultado['motivo'])}\n\n"
                f"Por favor, envie um comprovante válido.\n\n"
                f"⚠️ Tentativas restantes: {tentativas_restantes}",
                parse_mode=ParseMode.HTML
            )
            
            # Log simplificado
            logger.warning(f"Comprovante rejeitado para {pedido_id}: {resultado['motivo']}")

            
            if tentativas_restantes <= 0:
                database.atualizar_status_pedido(pedido_id, 'cancelado', motivo_rejeicao='Comprovantes inválidos')
                return ConversationHandler.END
            
            return AGUARDANDO_COMPROVANTE
            
    except Exception as e:
        logger.error(f"Erro ao processar comprovante: {e}")
        await msg_processando.delete()
        await update.message.reply_text(
            "❌ Erro ao processar a imagem. Por favor, envie novamente uma foto mais nítida."
        )
        return AGUARDANDO_COMPROVANTE


async def processar_pedido_aprovado(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    pedido: Dict
) -> int:
    """Processa um pedido após aprovação do pagamento."""
    try:
        # Criar pedido na API
        resultado_api = criar_pedido_api(
            service_id=pedido['service_id'],
            link=pedido['link'],
            quantidade=pedido['quantidade']
        )
        
        order_id_api = resultado_api.get('order')
        
        # Atualizar pedido no banco
        database.atualizar_status_pedido(
            pedido['id'], 
            'processando',
            order_id_api=order_id_api
        )
        
        # Atualizar estatísticas do usuário
        database.atualizar_estatisticas_usuario(pedido['chat_id'], pedido['valor_final'])
        
        # Enviar confirmação
        await update.message.reply_text(
            f"✅ <b>Pagamento Confirmado!</b> 🎉\n\n"
            f"Seu pedido foi aprovado e está sendo processado.\n\n"
            f"🆔 Pedido: <code>{escape_html(pedido['id'])}</code>\n"
            f"📝 ID na API: <code>{order_id_api}</code>\n\n"
            f"Você receberá uma notificação quando o serviço for concluído.\n\n"
            f"Use /meuspedidos para acompanhar o status.",
            parse_mode=ParseMode.HTML
        )
        
        # Notificar admin
        username = escape_html(pedido.get('username', 'N/A'))
        await context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=f"✅ <b>Novo pedido processado!</b>\n\n"
                 f"🆔 Pedido: <code>{escape_html(pedido['id'])}</code>\n"
                 f"👤 Cliente: @{username}\n"
                 f"💰 Valor: {utils.formatar_valor(pedido['valor_final'])}\n"
                 f"📝 API Order: <code>{order_id_api}</code>",
            parse_mode=ParseMode.HTML
        )
        
        # Limpar dados da sessão
        context.user_data.clear()
        
        return ConversationHandler.END
        
    except APIError as e:
        logger.error(f"Erro ao criar pedido na API: {e}")
        
        # Marcar como pago mas com erro na API
        database.atualizar_status_pedido(pedido['id'], 'erro', motivo_rejeicao=str(e))
        
        await update.message.reply_text(
            f"✅ Pagamento confirmado!\n\n"
            f"⚠️ Houve um erro ao processar seu pedido. "
            f"Nossa equipe foi notificada e resolverá em breve.\n\n"
            f"🆔 Pedido: <code>{escape_html(pedido['id'])}</code>",
            parse_mode=ParseMode.HTML
        )
        
        # Notificar admin sobre o erro
        await context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=f"⚠️ <b>Erro ao processar pedido!</b>\n\n"
                 f"🆔 Pedido: <code>{escape_html(pedido['id'])}</code>\n"
                 f"❌ Erro: {escape_html(e.message)}\n\n"
                 f"Pagamento foi confirmado, verificar manualmente.",
            parse_mode=ParseMode.HTML
        )
        
        return ConversationHandler.END


async def notificar_admin_aprovacao(
    context: ContextTypes.DEFAULT_TYPE,
    pedido: Dict,
    resultado_ocr: Dict,
    imagem_bytes: bytes
) -> None:
    """Envia notificação ao admin para aprovação manual."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{pedido['id']}"),
            InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{pedido['id']}")
        ]
    ]
    
    username = escape_html(pedido.get('username', 'N/A'))
    motivo = escape_html(resultado_ocr['motivo'])
    
    mensagem = (
        f"⚠️ <b>COMPROVANTE PARA ANÁLISE</b>\n\n"
        f"🆔 Pedido: <code>{escape_html(pedido['id'])}</code>\n"
        f"👤 Cliente: @{username} ({pedido['chat_id']})\n"
        f"💰 Valor esperado: {utils.formatar_valor(pedido['valor_final'])}\n"
        f"❓ Motivo: {motivo}\n\n"
        f"📊 <b>Detalhes OCR:</b>\n"
        f"• PIX detectado: {'✅' if resultado_ocr['detalhes']['tem_pix'] else '❌'}\n"
        f"• Valor correto: {'✅' if resultado_ocr['detalhes']['valor_correto'] else '❌'}\n"
        f"• Data válida: {'✅' if resultado_ocr['detalhes']['data_valida'] else '❌'}\n"
        f"• Confirmação: {'✅' if resultado_ocr['detalhes']['tem_confirmacao'] else '❌'}"
    )
    
    if resultado_ocr['detalhes'].get('valor_encontrado'):
        mensagem += f"\n• Valor encontrado: R$ {resultado_ocr['detalhes']['valor_encontrado']:.2f}"
    
    # Enviar foto do comprovante
    await context.bot.send_photo(
        chat_id=config.ADMIN_ID,
        photo=bytes(imagem_bytes),
        caption=mensagem,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def callback_aprovacao_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para aprovação/rejeição de comprovantes pelo admin."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("aprovar_"):
        pedido_id = data[8:]
        pedido = database.obter_pedido(pedido_id)
        
        if not pedido:
            await query.edit_message_caption("❌ Pedido não encontrado.")
            return
        
        try:
            # Criar pedido na API
            resultado_api = criar_pedido_api(
                service_id=pedido['service_id'],
                link=pedido['link'],
                quantidade=pedido['quantidade']
            )
            
            order_id_api = resultado_api.get('order')
            
            # Atualizar pedido
            database.atualizar_status_pedido(pedido_id, 'processando', order_id_api=order_id_api)
            database.atualizar_estatisticas_usuario(pedido['chat_id'], pedido['valor_final'])
            
            # Notificar cliente
            await context.bot.send_message(
                chat_id=pedido['chat_id'],
                text=f"✅ <b>Pagamento Confirmado!</b> 🎉\n\n"
                     f"Seu pedido foi aprovado e está sendo processado.\n\n"
                     f"🆔 Pedido: <code>{escape_html(pedido_id)}</code>\n"
                     f"📝 ID na API: <code>{order_id_api}</code>\n\n"
                     f"Use /meuspedidos para acompanhar o status.",
                parse_mode=ParseMode.HTML
            )
            
            await query.edit_message_caption(
                f"✅ Pedido <code>{escape_html(pedido_id)}</code> aprovado!\nAPI Order: <code>{order_id_api}</code>",
                parse_mode=ParseMode.HTML
            )
            
        except APIError as e:
            database.atualizar_status_pedido(pedido_id, 'erro', motivo_rejeicao=str(e))
            await query.edit_message_caption(
                f"⚠️ Erro ao processar na API: {escape_html(e.message)}\nPedido marcado como erro.",
                parse_mode=ParseMode.HTML
            )
    
    elif data.startswith("rejeitar_"):
        pedido_id = data[9:]
        pedido = database.obter_pedido(pedido_id)
        
        if not pedido:
            await query.edit_message_caption("❌ Pedido não encontrado.")
            return
        
        # Atualizar status
        database.atualizar_status_pedido(pedido_id, 'cancelado', motivo_rejeicao='Rejeitado pelo admin')
        
        # Notificar cliente
        await context.bot.send_message(
            chat_id=pedido['chat_id'],
            text="❌ <b>Comprovante Rejeitado</b>\n\n"
                 "Seu comprovante foi analisado e não foi aprovado.\n"
                 "Entre em contato com o suporte se acredita que houve um erro.\n\n"
                 "/ajuda - Ver opções de suporte",
            parse_mode=ParseMode.HTML
        )
        
        await query.edit_message_caption(
            f"❌ Pedido <code>{escape_html(pedido_id)}</code> rejeitado.",
            parse_mode=ParseMode.HTML
        )


# ==========================================
# HANDLERS ADMINISTRATIVOS
# ==========================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler do comando /admin - Painel administrativo."""
    chat_id = update.effective_chat.id
    
    if chat_id != config.ADMIN_ID:
        await update.message.reply_text("❌ Acesso negado.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Estatísticas", callback_data="admin_stats")],
        [InlineKeyboardButton("⏳ Pendentes", callback_data="admin_pendentes")],
        [InlineKeyboardButton("💰 Saldo API", callback_data="admin_saldo")],
        [InlineKeyboardButton("🔄 Atualizar Serviços", callback_data="admin_atualizar")]
    ]
    
    await update.message.reply_text(
        "🔧 <b>Painel Administrativo</b>\n\nSelecione uma opção:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler do comando /stats - Estatísticas de vendas."""
    chat_id = update.effective_chat.id
    
    if chat_id != config.ADMIN_ID:
        await update.message.reply_text("❌ Acesso negado.")
        return
    
    stats = database.obter_estatisticas_gerais()
    
    mensagem = f"""
📊 <b>Estatísticas Gerais</b>

👥 Total de usuários: {stats['total_usuarios']}
📦 Total de pedidos: {stats['total_pedidos']}

💰 <b>Financeiro:</b>
• Faturamento total: {utils.formatar_valor(stats['faturamento_total'])}
• Lucro total: {utils.formatar_valor(stats['lucro_total'])}

📅 <b>Hoje:</b>
• Pedidos: {stats['pedidos_hoje']}
• Faturamento: {utils.formatar_valor(stats['faturamento_hoje'])}

📋 <b>Por Status:</b>
"""
    
    for status, count in stats.get('pedidos_por_status', {}).items():
        emoji = utils.obter_emoji_status(status)
        texto = utils.obter_texto_status(status)
        mensagem += f"• {emoji} {escape_html(texto)}: {count}\n"
    
    await update.message.reply_text(mensagem, parse_mode=ParseMode.HTML)


async def callback_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para callbacks do painel admin."""
    query = update.callback_query
    await query.answer()
    
    if update.effective_chat.id != config.ADMIN_ID:
        return
    
    data = query.data
    
    if data == "admin_stats":
        stats = database.obter_estatisticas_gerais()
        mensagem = f"""
📊 <b>Estatísticas</b>

👥 Usuários: {stats['total_usuarios']}
📦 Pedidos: {stats['total_pedidos']}
💰 Faturamento: {utils.formatar_valor(stats['faturamento_total'])}
📈 Lucro: {utils.formatar_valor(stats['lucro_total'])}
📅 Hoje: {stats['pedidos_hoje']} pedidos
"""
        await query.edit_message_text(mensagem, parse_mode=ParseMode.HTML)
    
    elif data == "admin_pendentes":
        pendentes = database.obter_pedidos_pendentes_aprovacao()
        if pendentes:
            mensagem = f"⏳ <b>{len(pendentes)} pedido(s) pendente(s):</b>\n\n"
            for p in pendentes[:10]:
                mensagem += f"• <code>{escape_html(p['id'])}</code> - {utils.formatar_valor(p['valor_final'])}\n"
        else:
            mensagem = "✅ Nenhum pedido pendente de aprovação."
        await query.edit_message_text(mensagem, parse_mode=ParseMode.HTML)
    
    elif data == "admin_saldo":
        try:
            saldo = consultar_saldo_api()
            await query.edit_message_text(
                f"💰 <b>Saldo na API:</b> {utils.formatar_valor(saldo)}",
                parse_mode=ParseMode.HTML
            )
        except APIError as e:
            await query.edit_message_text(f"❌ Erro: {escape_html(e.message)}")
    
    elif data == "admin_atualizar":
        try:
            servicos = listar_servicos(usar_cache=False)
            await query.edit_message_text(
                f"✅ Cache atualizado!\n{len(servicos)} serviços carregados.",
                parse_mode=ParseMode.HTML
            )
        except APIError as e:
            await query.edit_message_text(f"❌ Erro: {escape_html(e.message)}")


# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

async def voltar_menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Retorna ao menu principal."""
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("📦 Fazer Pedido", callback_data="fazer_pedido")],
        [InlineKeyboardButton("📊 Meus Pedidos", callback_data="meus_pedidos")],
        [InlineKeyboardButton("📋 Serviços", callback_data="listar_servicos")],
        [InlineKeyboardButton("💬 Suporte", callback_data="suporte")]
    ]
    
    mensagem = """
🎉 <b>Bem-vindo ao SMM Bot!</b>

Somos especializados em serviços de marketing digital para suas redes sociais.

📱 <b>Serviços disponíveis:</b>
• Seguidores
• Curtidas
• Visualizações
• Comentários
• E muito mais!

🔥 <b>Preços competitivos e entrega rápida!</b>

Use os botões abaixo para navegar:
"""
    
    await query.edit_message_text(
        mensagem,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    return MENU_PRINCIPAL


async def mostrar_meus_pedidos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exibe os pedidos do usuário."""
    query = update.callback_query
    chat_id = update.effective_chat.id
    
    pedidos = database.listar_pedidos_usuario(chat_id, limite=10)
    
    if not pedidos:
        await query.edit_message_text(
            "📭 Você ainda não tem pedidos.\n\nUse o botão abaixo para fazer seu primeiro pedido!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Fazer Pedido", callback_data="fazer_pedido")],
                [InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu")]
            ])
        )
        return MENU_PRINCIPAL
    
    mensagem = "📋 <b>Seus Pedidos:</b>\n\n"
    
    for p in pedidos:
        emoji = utils.obter_emoji_status(p['status'])
        texto_status = utils.obter_texto_status(p['status'])
        servico_nome = escape_html(p['servico_nome'][:25]) if p['servico_nome'] else 'N/A'
        mensagem += (
            f"{emoji} <code>{escape_html(p['id'])}</code>\n"
            f"   {servico_nome}...\n"
            f"   {utils.formatar_valor(p['valor_final'])} - {escape_html(texto_status)}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu")]]
    
    await query.edit_message_text(
        mensagem,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    return MENU_PRINCIPAL


async def mostrar_todos_servicos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exibe todos os serviços disponíveis."""
    query = update.callback_query
    
    try:
        servicos = listar_servicos()
        
        if not servicos:
            await query.edit_message_text("❌ Nenhum serviço disponível.")
            return MENU_PRINCIPAL
        
        # Agrupar por categoria
        por_categoria = {}
        for s in servicos:
            cat = s.get('categoria', s.get('category', 'outros'))
            if cat not in por_categoria:
                por_categoria[cat] = []
            por_categoria[cat].append(s)
        
        mensagem = "📋 <b>Serviços Disponíveis:</b>\n\n"
        
        for cat, servs in list(por_categoria.items())[:5]:  # Limitar categorias
            nome_cat = config.CATEGORIAS.get(cat, cat.title())
            mensagem += f"<b>{escape_html(nome_cat)}:</b>\n"
            
            for s in servs[:5]:  # Limitar serviços por categoria
                rate_final = pricing.calcular_rate_final(float(s.get('rate', 0)))
                nome = s.get('nome', s.get('name', 'Serviço'))[:30]
                nome_limpo = escape_html(nome.replace('_', ' '))
                mensagem += f"• {nome_limpo} - R$ {rate_final:.2f}/1k\n"
            
            mensagem += "\n"
        
        keyboard = [
            [InlineKeyboardButton("📦 Fazer Pedido", callback_data="fazer_pedido")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu")]
        ]
        
        await query.edit_message_text(
            mensagem,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        
    except APIError as e:
        await query.edit_message_text(f"❌ Erro ao carregar serviços: {escape_html(e.message)}")
    
    return MENU_PRINCIPAL


async def verificar_pedidos_expirados(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job para verificar e cancelar pedidos expirados."""
    pedidos_expirados = database.obter_pedidos_expirados()
    
    for pedido in pedidos_expirados:
        database.atualizar_status_pedido(
            pedido['id'], 
            'cancelado', 
            motivo_rejeicao='Tempo expirado'
        )
        
        try:
            await context.bot.send_message(
                chat_id=pedido['chat_id'],
                text=f"⏰ <b>Pedido Expirado</b>\n\n"
                     f"O tempo para pagamento do pedido <code>{escape_html(pedido['id'])}</code> expirou.\n\n"
                     f"Se ainda deseja o serviço, faça um novo pedido.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Erro ao notificar expiração: {e}")
    
    if pedidos_expirados:
        logger.info(f"{len(pedidos_expirados)} pedidos expirados cancelados")


# ==========================================
# HANDLERS DE TEXTO PARA ESTADOS
# ==========================================

async def handler_texto_comprovante(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para mensagens de texto no estado AGUARDANDO_COMPROVANTE."""
    await update.message.reply_text(
        "📸 <b>Por favor, envie uma FOTO do comprovante PIX.</b>\n\n"
        "Clique no ícone de clipe/anexo e selecione a imagem do seu comprovante.",
        parse_mode=ParseMode.HTML
    )
    return AGUARDANDO_COMPROVANTE


async def handler_texto_aprovacao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para mensagens de texto no estado AGUARDANDO_APROVACAO."""
    await update.message.reply_text(
        "⏳ <b>Seu comprovante está em análise.</b>\n\n"
        "Nossa equipe está verificando. Você será notificado em breve!",
        parse_mode=ParseMode.HTML
    )
    return AGUARDANDO_APROVACAO


# ==========================================
# FUNÇÃO PRINCIPAL
# ==========================================

def main():
    """Função principal que inicializa e executa o bot."""
    # Configurar logging
    utils.configurar_logging()
    logger.info("Iniciando Bot SMM...")
    
    # Inicializar banco de dados
    database.inicializar_banco()
    logger.info("Banco de dados inicializado")
    
    # Criar aplicação
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Conversation handler para fluxo de pedidos
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU_PRINCIPAL: [
                CallbackQueryHandler(callback_menu_principal)
            ],
            SELECIONAR_CATEGORIA: [
                CallbackQueryHandler(callback_selecionar_categoria)
            ],
            SELECIONAR_SERVICO: [
                CallbackQueryHandler(callback_selecionar_servico)
            ],
            INSERIR_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_link)
            ],
            INSERIR_QUANTIDADE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_quantidade)
            ],
            AGUARDANDO_COMPROVANTE: [
                MessageHandler(filters.PHOTO, receber_comprovante),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler_texto_comprovante)
            ],
            AGUARDANDO_APROVACAO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler_texto_aprovacao)
            ]
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar),
            CommandHandler('start', start)
        ],
        allow_reentry=True
    )
    
    # Adicionar handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('ajuda', ajuda))
    application.add_handler(CommandHandler('help', ajuda))
    application.add_handler(CommandHandler('status', status_pedido))
    application.add_handler(CommandHandler('meuspedidos', meus_pedidos_cmd))
    application.add_handler(CommandHandler('admin', admin_panel))
    application.add_handler(CommandHandler('stats', admin_stats))
    
    # Handler para aprovações do admin
    application.add_handler(CallbackQueryHandler(callback_aprovacao_admin, pattern=r'^(aprovar|rejeitar)_'))
    application.add_handler(CallbackQueryHandler(callback_admin, pattern=r'^admin_'))
    
    # Job para verificar pedidos expirados (a cada 5 minutos)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(verificar_pedidos_expirados, interval=300, first=60)
        logger.info("Job de verificação de pedidos expirados configurado")
    else:
        logger.warning("JobQueue não disponível. Instale com: pip install 'python-telegram-bot[job-queue]'")
    
    logger.info("Bot iniciado com sucesso!")
    
    # Iniciar bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
