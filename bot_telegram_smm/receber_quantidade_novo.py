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
