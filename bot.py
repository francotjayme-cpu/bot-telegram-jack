import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIGURACIÓN ====================
# IMPORTANTE: Cambiá estos valores con tus datos reales:
BOT_TOKEN = os.getenv("BOT_TOKEN", "7519505004:AAFUmyDOpcGYW9yaAov6HlrgOhYWZ5X5mqo")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6368408762")
IMAGEN_BIENVENIDA = os.getenv("IMAGEN_BIENVENIDA", "https://imgur.com/a/qkyhr2F")

# ==================== TEXTOS DEL BOT ====================
TEXTO_BIENVENIDA = """oi, meu bem ✨ seja bem-vindo ao meu cantinho
escolhe aqui embaixo o que você quer ver ou saber 💛"""

TEXTO_PRIVACY_VIP = """💛 *Privacy VIP*

Contenido exclusivo, fotos e vídeos inéditos só pra você! 
Acesso ilimitado ao meu melhor conteúdo.

👉 Acesse agora: https://privacy.com.br/profile/jackloppes"""

TEXTO_PRIVACY_FREE = """💙 *Privacy FREE*

Quer dar uma espiada antes? Aqui tem conteúdo gratuito pra você conhecer meu trabalho!

👉 Acesse agora: https://privacy.com.br/profile/jackloppesfree"""

TEXTO_BEACONS = """🌐 *Beacons - Todos meus links*

Todos os meus links em um só lugar! Instagram, TikTok, e muito mais.

👉 Acesse aqui: https://beacons.ai/jaqueline_loppes"""

TEXTO_CANAL = """📣 *Canal do Telegram*

Entre no meu canal oficial! Lá eu posto novidades, avisos e conteúdo exclusivo.

👉 Entre agora: https://t.me/jackloppesbr"""

TEXTO_ONLYFANS = """🔥 *OnlyFans*

Meu conteúdo mais exclusivo e picante está aqui! 
Fotos, vídeos e muito mais esperando por você.

👉 Assine agora: https://onlyfans.com/jackloppess"""

TEXTO_SOBRE_MIM = """⭐ *Sobre mim*

Oi! Eu sou a Jack Loppes 💛

Criadora de conteúdo, apaixonada por fotografia e por conectar com pessoas incríveis como você!

Aqui você encontra meus melhores conteúdos, links e pode falar diretamente comigo.

Seja bem-vindo ao meu cantinho! ✨"""

TEXTO_ATENDIMENTO = """💬 *Atendimento Humano*

Oi! Estou te esperando para conversar 💛

Vou responder sua mensagem em breve. Fique à vontade para me contar o que precisa!"""

# ==================== FUNCIONES DEL BOT ====================

def crear_menu_principal():
    """Crea el teclado inline del menú principal con 7 botones"""
    keyboard = [
        [InlineKeyboardButton("💛 Privacy VIP", callback_data='privacy_vip')],
        [InlineKeyboardButton("💙 Privacy FREE", callback_data='privacy_free')],
        [InlineKeyboardButton("🌐 Beacons", callback_data='beacons')],
        [InlineKeyboardButton("📣 Canal Telegram", callback_data='canal')],
        [InlineKeyboardButton("🔥 OnlyFans", callback_data='onlyfans')],
        [InlineKeyboardButton("💬 Atendimento humano", callback_data='atendimento')],
        [InlineKeyboardButton("⭐ Sobre mim", callback_data='sobre_mim')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Muestra el menú principal con imagen de bienvenida"""
    try:
        # Enviar imagen con el texto de bienvenida y el menú de botones
        await update.message.reply_photo(
            photo=IMAGEN_BIENVENIDA,
            caption=TEXTO_BIENVENIDA,
            reply_markup=crear_menu_principal()
        )
    except Exception as e:
        # Si falla la imagen (URL incorrecta), enviar solo el texto con botones
        logger.error(f"Error al enviar imagen: {e}")
        await update.message.reply_text(
            TEXTO_BIENVENIDA,
            reply_markup=crear_menu_principal()
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los clicks en los botones del menú"""
    query = update.callback_query
    await query.answer()
    
    user_info = f"Usuario: {query.from_user.first_name} (@{query.from_user.username or 'sin username'})\nID: {query.from_user.id}"
    
    # Botón: Privacy VIP
    if query.data == 'privacy_vip':
        await query.message.reply_text(
            TEXTO_PRIVACY_VIP,
            parse_mode='Markdown',
            reply_markup=crear_boton_volver()
        )
    
    # Botón: Privacy FREE
    elif query.data == 'privacy_free':
        await query.message.reply_text(
            TEXTO_PRIVACY_FREE,
            parse_mode='Markdown',
            reply_markup=crear_boton_volver()
        )
    
    # Botón: Beacons
    elif query.data == 'beacons':
        await query.message.reply_text(
            TEXTO_BEACONS,
            parse_mode='Markdown',
            reply_markup=crear_boton_volver()
        )
    
    # Botón: Canal Telegram
    elif query.data == 'canal':
        await query.message.reply_text(
            TEXTO_CANAL,
            parse_mode='Markdown',
            reply_markup=crear_boton_volver()
        )
    
    # Botón: OnlyFans
    elif query.data == 'onlyfans':
        await query.message.reply_text(
            TEXTO_ONLYFANS,
            parse_mode='Markdown',
            reply_markup=crear_boton_volver()
        )
    
    # Botón: Sobre mim
    elif query.data == 'sobre_mim':
        await query.message.reply_text(
            TEXTO_SOBRE_MIM,
            parse_mode='Markdown',
            reply_markup=crear_boton_volver()
        )
    
    # Botón: Atendimento humano (Live Chat)
    elif query.data == 'atendimento':
        # Activar modo atención humana para este usuario
        context.user_data['atendimento_ativo'] = True
        
        # Enviar mensaje al usuario confirmando que será atendido
        await query.message.reply_text(
            TEXTO_ATENDIMENTO,
            parse_mode='Markdown'
        )
        
        # Notificar al admin (a ti) que hay un nuevo contacto esperando
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🔔 *NUEVO CONTACTO - ATENCIÓN HUMANA*\n\n{user_info}\n\nEl usuario solicitó atención humana. Sus próximos mensajes te llegarán directamente aquí.",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error al notificar al admin: {e}")
    
    # Botón: Volver al menú
    elif query.data == 'volver':
        try:
            # Volver al menú principal con imagen
            await query.message.reply_photo(
                photo=IMAGEN_BIENVENIDA,
                caption=TEXTO_BIENVENIDA,
                reply_markup=crear_menu_principal()
            )
        except:
            # Si falla la imagen, solo texto
            await query.message.reply_text(
                TEXTO_BIENVENIDA,
                reply_markup=crear_menu_principal()
            )

def crear_boton_volver():
    """Crea un botón para volver al menú principal"""
    keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data='volver')]]
    return InlineKeyboardMarkup(keyboard)

async def mensaje_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes de texto del usuario"""
    # Si el modo atención humana está activo, reenviar mensajes al admin
    if context.user_data.get('atendimento_ativo', False):
        user_info = f"Usuario: {update.message.from_user.first_name} (@{update.message.from_user.username or 'sin username'})\nID: {update.message.from_user.id}"
        
        try:
            # Reenviar el mensaje al admin (a ti)
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"💬 *MENSAJE DE USUARIO*\n\n{user_info}\n\n*Mensaje:*\n{update.message.text}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error al reenviar mensaje al admin: {e}")
    else:
        # Si no está en modo atención humana, mostrar el menú
        await update.message.reply_text(
            "Para volver al menú principal, usá el comando /start",
            reply_markup=crear_menu_principal()
        )

# ==================== SERVIDOR HTTP PARA RENDER ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    """Servidor HTTP simple para que Render no cierre el servicio"""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot de Telegram funcionando correctamente!')
    
    def log_message(self, format, *args):
        # No mostrar logs del servidor HTTP para no llenar la consola
        pass

def run_http_server():
    """Corre el servidor HTTP en segundo plano"""
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Servidor HTTP corriendo en puerto {port} ✅")
    server.serve_forever()

# ==================== MAIN ====================
def main():
    """Inicia el bot y el servidor HTTP"""
    # Iniciar servidor HTTP en un thread separado (necesario para Render)
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Crear la aplicación del bot
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Agregar manejadores de comandos y mensajes
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_handler))
    
    # Iniciar el bot
    logger.info("Bot de Telegram iniciado correctamente! ✅")
    logger.info("Esperando mensajes...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
