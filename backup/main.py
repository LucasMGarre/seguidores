import logging
import asyncio
import requests
from cpf_validator import validar_cpf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Configurações
TELEGRAM_TOKEN = "6538720415:AAH7qKixZw7DB58CVdHsowQcjrPo2HDCW3s"
API_KEY = "3fa7663e054e9339dfb1d09ddaf44bf5"
API_URL = "https://borafama.com/api/v2"

# Configurações LiraPay
LIRAPAY_API_KEY = "sk_64b9f1333cc59f8b0ae5e9e152c301a606c5f18003aea8fea7a197e0b8f5e38405413ed53623f9e9d93714ef9784122e98fe8681b35d4b5baf604bb0ad8d8a52"
LIRAPAY_API_URL = "https://api.lirapaybr.com"

# Estados da conversa
AGUARDANDO_LINK, AGUARDANDO_CPF, AGUARDANDO_QUANTIDADE_CUSTOM, AGUARDANDO_PAGAMENTO = range(4)

# Gerenciador de pagamentos
from payment_manager import PaymentManager
payment_manager = PaymentManager(LIRAPAY_API_KEY, LIRAPAY_API_URL)

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Catálogo de produtos
PRODUTOS = {
    'seguidores_br_mix': [
        {'qtd': 500, 'preco': 18.00, 'texto': '500 Seguidores BR/Mix - R$ 18'},
        {'qtd': 1000, 'preco': 34.00, 'texto': '1000 Seguidores BR/Mix - R$ 34'},
        {'qtd': 2000, 'preco': 47.00, 'texto': '2000 Seguidores BR/Mix - R$ 47'},
        {'qtd': 3000, 'preco': 60.00, 'texto': '3000 Seguidores BR/Mix - R$ 60'},
        {'qtd': 4000, 'preco': 75.00, 'texto': '4000 Seguidores BR/Mix - R$ 75'},
        {'qtd': 5000, 'preco': 100.00, 'texto': '5000 Seguidores BR/Mix - R$ 100'},
        {'qtd': 10000, 'preco': 170.00, 'texto': '10000 Seguidores BR/Mix - R$ 170'},
    ],
    'seguidores_mundiais': [
        {'qtd': 500, 'preco': 4.50, 'texto': '500 Seguidores Mundiais - R$ 4,50'},
        {'qtd': 1000, 'preco': 7.50, 'texto': '1000 Seguidores Mundiais - R$ 7,50'},
        {'qtd': 2000, 'preco': 14.50, 'texto': '2000 Seguidores Mundiais - R$ 14,50'},
        {'qtd': 5000, 'preco': 29.50, 'texto': '5000 Seguidores Mundiais - R$ 29,50'},
        {'qtd': 10000, 'preco': 43.90, 'texto': '10000 Seguidores Mundiais - R$ 43,90'},
    ],
    'seguidores_100_br': [
        {'qtd': 1000, 'preco': 60.00, 'texto': '1000 Seguidores 100% BR - R$ 60'},
        {'qtd': 2000, 'preco': 110.00, 'texto': '2000 Seguidores 100% BR - R$ 110'},
        {'qtd': 4000, 'preco': 185.00, 'texto': '4000 Seguidores 100% BR - R$ 185'},
        {'qtd': 5000, 'preco': 220.00, 'texto': '5000 Seguidores 100% BR - R$ 220'},
    ],
    'curtidas_br': [
        {'qtd': 100, 'preco': 5.00, 'texto': '100 Curtidas BR - R$ 5'},
        {'qtd': 500, 'preco': 12.50, 'texto': '500 Curtidas BR - R$ 12,50'},
        {'qtd': 1000, 'preco': 20.50, 'texto': '1000 Curtidas BR - R$ 20,50'},
        {'qtd': 2000, 'preco': 33.50, 'texto': '2000 Curtidas BR - R$ 33,50'},
        {'qtd': 5000, 'preco': 60.00, 'texto': '5000 Curtidas BR - R$ 60,00'},
        {'qtd': 10000, 'preco': 100.00, 'texto': '10000 Curtidas BR - R$ 100,00'},
    ],
    'visualizacoes': [
        {'qtd': 250, 'preco': 5.00, 'texto': '250 Visualizações - R$ 5'},
        {'qtd': 500, 'preco': 10.00, 'texto': '500 Visualizações - R$ 10'},
        {'qtd': 1000, 'preco': 20.00, 'texto': '1000 Visualizações - R$ 20'},
        {'qtd': 2000, 'preco': 30.00, 'texto': '2000 Visualizações - R$ 30'},
        {'qtd': 3000, 'preco': 40.00, 'texto': '3000 Visualizações - R$ 40'},
        {'qtd': 4000, 'preco': 50.00, 'texto': '4000 Visualizações - R$ 50'},
        {'qtd': 5000, 'preco': 60.00, 'texto': '5000 Visualizações - R$ 60'},
        {'qtd': 10000, 'preco': 100.00, 'texto': '10000 Visualizações - R$ 100'},
        {'qtd': 20000, 'preco': 200.00, 'texto': '20000 Visualizações - R$ 200'},
    ],
}

# Funções da API
def get_services():
    """Busca lista de serviços da API"""
    try:
        response = requests.post(API_URL, data={
            'key': API_KEY,
            'action': 'services'
        })
        return response.json()
    except Exception as e:
        logger.error(f"Erro ao buscar serviços: {e}")
        return None

def create_order(service_id, link, quantity):
    """Cria um pedido na API"""
    try:
        response = requests.post(API_URL, data={
            'key': API_KEY,
            'action': 'add',
            'service': service_id,
            'link': link,
            'quantity': quantity
        })
        return response.json()
    except Exception as e:
        logger.error(f"Erro ao criar pedido: {e}")
        return None

def get_order_status(order_id):
    """Verifica status de um pedido"""
    try:
        response = requests.post(API_URL, data={
            'key': API_KEY,
            'action': 'status',
            'order': order_id
        })
        return response.json()
    except Exception as e:
        logger.error(f"Erro ao verificar status: {e}")
        return None

def get_balance():
    """Verifica saldo da conta"""
    try:
        response = requests.post(API_URL, data={
            'key': API_KEY,
            'action': 'balance'
        })
        return response.json()
    except Exception as e:
        logger.error(f"Erro ao verificar saldo: {e}")
        return None

# Handlers do Bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Menu principal"""
    keyboard = [
        [InlineKeyboardButton("📱 Seguidores BR/Mix", callback_data='cat_seguidores_br_mix')],
        [InlineKeyboardButton("🌎 Seguidores Mundiais", callback_data='cat_seguidores_mundiais')],
        [InlineKeyboardButton("🇧🇷 Seguidores 100% BR Real", callback_data='cat_seguidores_100_br')],
        [InlineKeyboardButton("❤️ Curtidas Brasileiras", callback_data='cat_curtidas_br')],
        [InlineKeyboardButton("👁️ Visualizações (Reels/Stories)", callback_data='cat_visualizacoes')],
        [InlineKeyboardButton("📊 Verificar Pedido", callback_data='verificar_pedido')],
        [InlineKeyboardButton("ℹ️ Informações", callback_data='info')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mensagem = (
        "🎯 BEM-VINDO AO BOT DE VENDAS INSTAGRAM!\n\n"
        "✅ Entrega rápida e segura\n"
        "✅ Suporte 24/7\n"
        "✅ Serviços de qualidade\n\n"
        "Escolha uma categoria abaixo:"
    )
    
    if update.message:
        await update.message.reply_text(mensagem, reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_text(mensagem, reply_markup=reply_markup)

async def mostrar_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra produtos de uma categoria"""
    query = update.callback_query
    await query.answer()
    
    categoria = query.data.replace('cat_', '')
    
    if categoria not in PRODUTOS:
        await query.message.edit_text("❌ Categoria não encontrada!")
        return
    
    produtos = PRODUTOS[categoria]
    
    # Título da categoria
    titulos = {
        'seguidores_br_mix': '📱 Seguidores BR/Mix',
        'seguidores_mundiais': '🌎 Seguidores Mundiais',
        'seguidores_100_br': '🇧🇷 Seguidores 100% BR Real',
        'curtidas_br': '❤️ Curtidas Brasileiras',
        'visualizacoes': '👁️ Visualizações (Reels/Stories/IGTV)',
    }
    
    # Criar botões para cada produto
    keyboard = []
    for i, produto in enumerate(produtos):
        keyboard.append([InlineKeyboardButton(
            produto['texto'], 
            callback_data=f'prod_{categoria}_{i}'
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data='voltar_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(
        f"{titulos[categoria]}\n\nSelecione o pacote desejado:",
        reply_markup=reply_markup,
    )

async def selecionar_produto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Produto selecionado - solicitar link"""
    query = update.callback_query
    await query.answer()
    
    # Parse: prod_categoria_indice
    dados = query.data.replace('prod_', '').split('_')
    indice = int(dados[-1])
    categoria = '_'.join(dados[:-1])
    
    produto = PRODUTOS[categoria][indice]
    
    # Salvar no contexto
    context.user_data['produto_selecionado'] = produto
    context.user_data['categoria'] = categoria
    
    keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data='voltar_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        f"📦 PRODUTO SELECIONADO:\n{produto['texto']}\n\n"
        f"💰 VALOR: R$ {produto['preco']:.2f}\n\n"
        f"🔗 Agora envie o LINK do seu perfil/post do Instagram:\n"
        f"(Ex: https://instagram.com/seu_perfil)",
        reply_markup=reply_markup
    )
    
    return AGUARDANDO_LINK

async def process_confirmed_payment(application, user_id, transaction_id, amount):
    """Processa o pedido após confirmação do pagamento"""
    try:
        # Buscar dados do usuário do contexto global
        user_data = application.user_data.get(user_id, {})
        produto = user_data.get('produto_selecionado')
        categoria = user_data.get('categoria')
        link = user_data.get('instagram_link')
        
        service_ids = {
            'seguidores_br_mix': 398,
            'seguidores_mundiais': 399,
            'seguidores_100_br': 400,
            'curtidas_br': 227,
            'visualizacoes': 107,
        }
        
        service_id = service_ids.get(categoria, 1)
        
        # Criar pedido na API do borafama
        resultado = create_order(service_id, link, produto['qtd'])
        
        if resultado and 'order' in resultado:
            order_id = resultado['order']
            mensagem = (
                f"✅ Pagamento confirmado e pedido criado!\n\n"
                f"ID do Pedido: {order_id}\n"
                f"Produto: {produto['texto']}\n"
                f"Link: {link}\n"
                f"Valor: R$ {produto['preco']:.2f}\n\n"
                f"Status: Em processamento\n\n"
                f"Use /verificar {order_id} para acompanhar seu pedido!"
            )
        else:
            mensagem = (
                f"❌ *Erro ao processar pedido após pagamento*\n\n"
                f"Por favor, entre em contato com o suporte.\n"
                f"ID Transação: {transaction_id}"
            )
        
        # Envia mensagem para o usuário
        await application.bot.send_message(
            chat_id=user_id,
            text=mensagem
        )
        
    except Exception as e:
        logger.error(f"Erro ao processar pedido após pagamento: {e}")
        await application.bot.send_message(
            chat_id=user_id,
            text="❌ Ocorreu um erro ao processar seu pedido. Por favor, contate o suporte."
        )

async def receber_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o link e solicita CPF"""
    link = update.message.text.strip()
    
    # Validação básica do link
    if 'instagram.com' not in link.lower():
        await update.message.reply_text(
            "❌ Link inválido! Por favor, envie um link do Instagram.\n"
            "Exemplo: https://instagram.com/seu_perfil"
        )
        return AGUARDANDO_LINK
    
    produto = context.user_data.get('produto_selecionado')
    
    if not produto:
        await update.message.reply_text("❌ Erro: produto não encontrado. Use /start para começar novamente.")
        return ConversationHandler.END
    
    # Salvar link
    context.user_data['instagram_link'] = link
    
    keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data='voltar_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 Para finalizar, envie seu CPF:\n"
        "(Somente números, ex: 12345678900)",
        reply_markup=reply_markup
    )
    
    return AGUARDANDO_CPF
    
    if payment and 'pix' in payment:
        # Guardar ID da transação
        context.user_data['transaction_id'] = payment['id']
        
        mensagem = (
            f"🛍️ PEDIDO INICIADO!\n\n"
            f"📦 Produto: {produto['texto']}\n"
            f"🔗 Link: {link}\n"
            f"💰 Valor: R$ {produto['preco']:.2f}\n\n"
            f"📱 PAGAMENTO PIX\n"
            f"Copie a chave PIX abaixo ou escaneie o QR Code:\n\n"
            f"{payment['pix']['payload']}\n\n"
            f"⏳ Aguardando pagamento...\n"
            f"O pedido será processado automaticamente após a confirmação."
        )
        
        keyboard = [[InlineKeyboardButton("❌ Cancelar Pedido", callback_data='cancelar_pedido')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Se houver QR Code, enviar como imagem
        if 'qrcode_image' in payment['pix']:
            try:
                await update.message.reply_photo(
                    photo=payment['pix']['qrcode_image'],
                    caption=mensagem,
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Erro ao enviar QR Code: {e}")
                await update.message.reply_text(
                    mensagem,
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text(
                mensagem,
                reply_markup=reply_markup
            )
        
        return AGUARDANDO_PAGAMENTO
        
    else:
        mensagem = (
            "❌ Erro ao gerar pagamento\n\n"
            "Por favor, tente novamente ou entre em contato com o suporte."
        )
        
        keyboard = [[InlineKeyboardButton("🏠 Voltar ao Menu", callback_data='voltar_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(mensagem, reply_markup=reply_markup)
        return ConversationHandler.END

async def verificar_pedido_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia verificação de pedido"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data='voltar_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "🔍 Verificar Status do Pedido\n\n"
        "Digite o ID do seu pedido:",
        reply_markup=reply_markup
    )

async def verificar_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /verificar [order_id]"""
    if len(context.args) == 0:
        await update.message.reply_text(
            "❌ Uso correto: /verificar [ID_DO_PEDIDO]\n"
            "Exemplo: /verificar 12345"
        )
        return
    
    order_id = context.args[0]
    await update.message.reply_text("⏳ Verificando pedido...")
    
    status = get_order_status(order_id)
    
    if status and 'status' in status:
        emoji_status = {
            'Pending': '⏳',
            'In progress': '🔄',
            'Completed': '✅',
            'Partial': '⚠️',
            'Canceled': '❌',
        }
        
        status_emoji = emoji_status.get(status['status'], '❓')
        
        mensagem = (
            f"{status_emoji} Status do Pedido #{order_id}\n\n"
            f"📊 Status: {status['status']}\n"
            f"📈 Início: {status.get('start_count', 'N/A')}\n"
            f"⏰ Restante: {status.get('remains', 'N/A')}\n"
        )
    else:
        mensagem = f"❌ Pedido #{order_id} não encontrado ou erro ao verificar."
    
    keyboard = [[InlineKeyboardButton("🏠 Menu Principal", callback_data='voltar_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(mensagem, reply_markup=reply_markup)

async def mostrar_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra informações"""
    query = update.callback_query
    await query.answer()
    
    mensagem = (
        "ℹ️ *Informações Importantes*\n\n"
        "✅ *Garantia:* Todos os serviços possuem garantia\n"
        "✅ *Entrega:* Início em até 24 horas\n"
        "✅ *Qualidade:* Perfis reais e ativos\n"
        "✅ *Suporte:* Disponível 24/7\n\n"
        "📱 *Plataformas:*\n"
        "• Instagram\n"
        "• Twitter\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Twitch\n"
        "• Telegram\n\n"
        "💬 Dúvidas? Entre em contato - (11) 91319-4768!"

    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data='voltar_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(mensagem, reply_markup=reply_markup)

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela a operação atual"""
    await update.message.reply_text("❌ Operação cancelada. Use /start para começar novamente.")
    return ConversationHandler.END

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para todos os botões"""
    query = update.callback_query
    
    if query.data == 'voltar_menu':
        await start(update, context)
    elif query.data.startswith('cat_'):
        await mostrar_categoria(update, context)
    elif query.data.startswith('prod_'):
        await selecionar_produto(update, context)
    elif query.data == 'verificar_pedido':
        await verificar_pedido_start(update, context)
    elif query.data == 'info':
        await mostrar_info(update, context)

async def cancelar_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela o pedido atual"""
    query = update.callback_query
    await query.answer()
    
    # Remove da lista de monitoramento se existir
    transaction_id = context.user_data.get('transaction_id')
    if transaction_id:
        payment_manager.pending_payments.pop(transaction_id, None)
    
    # Limpa dados do pedido
    context.user_data.clear()
    
    await query.message.edit_text(
        "❌ Pedido cancelado. Use /start para fazer um novo pedido.",
        reply_markup=None
    )
    return ConversationHandler.END

async def start_payment_monitor(application):
    """Monitora pagamentos pendentes"""
    while True:
        try:
            await payment_manager.monitor_pending_payments(
                lambda user_id, tx_id, amount: process_confirmed_payment(application, user_id, tx_id, amount)
            )
        except Exception as e:
            logger.error(f"Erro no monitor de pagamentos: {e}")
        await asyncio.sleep(30)

async def receber_cpf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o CPF e gera pagamento"""
    cpf = ''.join(filter(str.isdigit, update.message.text.strip()))
    
    # Validar CPF
    if not validar_cpf(cpf):
        await update.message.reply_text(
            "❌ CPF inválido! Por favor, envie um CPF válido.\n"
            "Exemplo: 12345678900"
        )
        return AGUARDANDO_CPF
    
    produto = context.user_data.get('produto_selecionado')
    link = context.user_data.get('instagram_link')
    
    # Salvar CPF
    context.user_data['cpf'] = cpf
    
    # Gerar pagamento PIX
    payment = payment_manager.create_pix_payment(
        amount=produto['preco'],
        user_id=update.effective_user.id,
        description=f"Compra de {produto['texto']}",
        cpf=cpf
    )
    
    if payment and 'pix' in payment:
        # Guardar ID da transação
        context.user_data['transaction_id'] = payment['id']
        
        mensagem = (
            f"🛍️ PEDIDO INICIADO!\n\n"
            f"📦 Produto: {produto['texto']}\n"
            f"🔗 Link: {link}\n"
            f"📋 CPF: {cpf}\n"
            f"💰 Valor: R$ {produto['preco']:.2f}\n\n"
            f"📱 PAGAMENTO PIX\n"
            f"Copie a chave PIX abaixo ou escaneie o QR Code:\n\n"
            f"{payment['pix']['payload']}\n\n"
            f"⏳ Aguardando pagamento...\n"
            f"O pedido será processado automaticamente após a confirmação."
        )
        
        keyboard = [[InlineKeyboardButton("❌ Cancelar Pedido", callback_data='cancelar_pedido')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Se houver QR Code, enviar como imagem
        if 'qrcode_image' in payment['pix']:
            try:
                await update.message.reply_photo(
                    photo=payment['pix']['qrcode_image'],
                    caption=mensagem,
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Erro ao enviar QR Code: {e}")
                await update.message.reply_text(
                    mensagem,
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text(
                mensagem,
                reply_markup=reply_markup
            )
        
        return AGUARDANDO_PAGAMENTO
        
    else:
        mensagem = (
            "❌ Erro ao gerar pagamento\n\n"
            "Por favor, tente novamente ou entre em contato com o suporte."
        )
        
        keyboard = [[InlineKeyboardButton("🏠 Voltar ao Menu", callback_data='voltar_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(mensagem, reply_markup=reply_markup)
        return ConversationHandler.END

async def main():
    """Função principal"""
    # Criar aplicação
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Conversation handler para compra
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(selecionar_produto, pattern='^prod_')],
        states={
            AGUARDANDO_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_link),
                CallbackQueryHandler(button_callback, pattern='^voltar_menu$')
            ],
            AGUARDANDO_CPF: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_cpf),
                CallbackQueryHandler(button_callback, pattern='^voltar_menu$')
            ],
            AGUARDANDO_PAGAMENTO: [
                CallbackQueryHandler(cancelar_pedido, pattern='^cancelar_pedido$'),
                CallbackQueryHandler(button_callback, pattern='^voltar_menu$')
            ],
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar),
            CallbackQueryHandler(button_callback, pattern='^voltar_menu$')
        ],
        name="compra_conversation"
    )
    
    # Adicionar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("verificar", verificar_comando))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Iniciar bot
    logger.info("🤖 Bot iniciado!")
    
    # Iniciar monitor de pagamentos em background
    monitor_task = asyncio.create_task(start_payment_monitor(application))
    
    # Inicializar e rodar o bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    try:
        # Manter o bot rodando
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Encerrando bot...")
    finally:
        # Limpar recursos ao encerrar
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # Parar o bot corretamente
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        raise