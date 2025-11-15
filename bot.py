import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIGURACIÓN ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "7519505004:AAFUmyDOpcGYW9yaAov6HlrgOhYWZ5X5mqo")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6368408762")
IMAGEN_BIENVENIDA = os.getenv("IMAGEN_BIENVENIDA", "https://i.imgur.com/fMLXHgl.jpeg")

# ==================== BASE DE DATOS ====================
def init_database():
    """Inicializa la base de datos SQLite"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registration_date TEXT,
            last_interaction TEXT,
            total_interactions INTEGER DEFAULT 0
        )
    ''')
    
    # Tabla de interacciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT,
            action_data TEXT,
            timestamp TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Tabla de mensajes de atención humana
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS human_attention (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            timestamp TEXT,
            responded INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Base de datos inicializada ✅")

def register_user(user_id, username, first_name, last_name):
    """Registra o actualiza un usuario en la base de datos"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    exists = cursor.fetchone()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not exists:
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, registration_date, last_interaction, total_interactions)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (user_id, username, first_name, last_name, now, now))
        logger.info(f"Nuevo usuario registrado: {first_name} ({user_id})")
    else:
        cursor.execute('''
            UPDATE users 
            SET last_interaction = ?, total_interactions = total_interactions + 1,
                username = ?, first_name = ?, last_name = ?
            WHERE user_id = ?
        ''', (now, username, first_name, last_name, user_id))
    
    conn.commit()
    conn.close()

def log_interaction(user_id, action_type, action_data=""):
    """Registra una interacción del usuario"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO interactions (user_id, action_type, action_data, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (user_id, action_type, action_data, now))
    
    conn.commit()
    conn.close()

def get_user_stats():
    """Obtiene estadísticas de usuarios"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Total usuarios
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    # Usuarios hoy
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM users WHERE registration_date LIKE ?', (f'{today}%',))
    users_today = cursor.fetchone()[0]
    
    # Interacción más popular
    cursor.execute('''
        SELECT action_type, COUNT(*) as count 
        FROM interactions 
        GROUP BY action_type 
        ORDER BY count DESC 
        LIMIT 1
    ''')
    popular = cursor.fetchone()
    popular_action = popular[0] if popular else "N/A"
    popular_count = popular[1] if popular else 0
    
    # Total interacciones
    cursor.execute('SELECT COUNT(*) FROM interactions')
    total_interactions = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_users': total_users,
        'users_today': users_today,
        'popular_action': popular_action,
        'popular_count': popular_count,
        'total_interactions': total_interactions
    }

def get_all_user_ids():
    """Obtiene todos los IDs de usuarios para broadcast"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return user_ids

# ==================== TEXTOS DEL BOT ====================
TEXTO_BIENVENIDA = """✨ *Oi, meu bem!* ✨

Seja bem-vindo ao meu cantinho especial 💛

Aqui você encontra todo o meu conteúdo exclusivo, links importantes e pode falar diretamente comigo.

👇 *Escolha uma opção abaixo:*"""

TEXTO_PRIVACY_VIP = """💛 *PRIVACY VIP* 💛

🔥 *Conteúdo 100% exclusivo só pra você!*

📸 Fotos inéditas e sensuais
🎥 Vídeos completos e picantes
💌 Acesso ilimitado ao melhor conteúdo
⚡ Atualizações diárias

👉 *Assine agora:*
https://privacy.com.br/profile/jackloppes"""

TEXTO_PRIVACY_FREE = """💙 *PRIVACY FREE* 💙

👀 *Quer dar uma espiada antes de assinar?*

Aqui tem conteúdo gratuito para você conhecer meu trabalho e ver a qualidade do que eu produzo!

🎁 Acesso grátis
📸 Fotos de preview
✨ Sem compromisso

👉 *Acesse aqui:*
https://privacy.com.br/profile/jackloppesfree"""

TEXTO_BEACONS = """🌐 *TODOS MEUS LINKS* 🌐

📱 Instagram, TikTok, Twitter e muito mais!

Todos os meus perfis em um só lugar para você me acompanhar em todas as redes sociais.

👉 *Acesse aqui:*
https://beacons.ai/jaqueline_loppes"""

TEXTO_CANAL = """📣 *CANAL OFICIAL DO TELEGRAM* 📣

💛 Entre no meu canal e fique por dentro de tudo!

✨ Novidades em primeira mão
🎁 Promoções exclusivas
📸 Prévias de conteúdo
🔥 Avisos importantes

👉 *Entre agora:*
https://t.me/jackloppesbr"""

TEXTO_ONLYFANS = """🔥 *ONLYFANS* 🔥

💋 *O meu conteúdo mais exclusivo e picante!*

🔞 Fotos e vídeos explícitos
💌 Conteúdo personalizado
💬 Chat direto comigo
⭐ Material que você não encontra em outro lugar

👉 *Assine agora:*
https://onlyfans.com/jackloppess"""

TEXTO_SOBRE_MIM = """⭐ *SOBRE MIM* ⭐

💛 *Oi! Eu sou a Jack Loppes*

📸 Criadora de conteúdo adulto
💫 Apaixonada por fotografia sensual
💖 Adoro conectar com pessoas especiais

✨ Aqui você encontra meus melhores conteúdos, pode acessar todos os meus links e falar diretamente comigo quando precisar!

*Seja muito bem-vindo ao meu cantinho!* 🌟"""

TEXTO_ATENDIMENTO = """💬 *ATENDIMENTO HUMANO ATIVADO* 💬

Oi, meu bem! 💛

Agora você está falando diretamente comigo. Pode me enviar sua mensagem que vou responder em breve!

Fique à vontade para perguntar o que precisar. 😊"""

# ==================== FUNCIONES DEL BOT ====================

def crear_menu_principal():
    """Crea el menú principal con botones inline"""
    keyboard = [
        [InlineKeyboardButton("💛 Privacy VIP", callback_data='privacy_vip')],
        [InlineKeyboardButton("💙 Privacy FREE", callback_data='privacy_free')],
        [InlineKeyboardButton("🌐 Todos meus Links", callback_data='beacons')],
        [InlineKeyboardButton("📣 Canal Telegram", callback_data='canal')],
        [InlineKeyboardButton("🔥 OnlyFans", callback_data='onlyfans')],
        [InlineKeyboardButton("💬 Falar Comigo", callback_data='atendimento')],
        [InlineKeyboardButton("⭐ Sobre Mim", callback_data='sobre_mim')]
    ]
    return InlineKeyboardMarkup(keyboard)

def crear_menu_admin():
    """Crea el menú de administración"""
    keyboard = [
        [InlineKeyboardButton("📊 Estatísticas", callback_data='admin_stats')],
        [InlineKeyboardButton("👥 Lista de Usuários", callback_data='admin_users')],
        [InlineKeyboardButton("📢 Enviar Mensagem em Massa", callback_data='admin_broadcast')],
        [InlineKeyboardButton("🔙 Fechar", callback_data='admin_close')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Menú principal"""
    user = update.effective_user
    register_user(user.id, user.username, user.first_name, user.last_name)
    log_interaction(user.id, "start", "Comando /start")
    
    try:
        await update.message.reply_photo(
            photo=IMAGEN_BIENVENIDA,
            caption=TEXTO_BIENVENIDA,
            parse_mode='Markdown',
            reply_markup=crear_menu_principal()
        )
    except Exception as e:
        logger.error(f"Error al enviar imagen: {e}")
        await update.message.reply_text(
            TEXTO_BIENVENIDA,
            parse_mode='Markdown',
            reply_markup=crear_menu_principal()
        )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /admin - Panel de administración"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Você não tem permissão para usar este comando.")
        return
    
    await update.message.reply_text(
        "🔐 *PAINEL DE ADMINISTRAÇÃO*\n\nEscolha uma opção:",
        parse_mode='Markdown',
        reply_markup=crear_menu_admin()
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /stats - Mostrar estadísticas"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_CHAT_ID:
        return
    
    stats = get_user_stats()
    
    mensaje = f"""📊 *ESTATÍSTICAS DO BOT*

👥 *Total de Usuários:* {stats['total_users']}
🆕 *Novos Hoje:* {stats['users_today']}
🔥 *Ação Mais Popular:* {stats['popular_action']} ({stats['popular_count']} vezes)
💬 *Total de Interações:* {stats['total_interactions']}

📅 *Atualizado:* {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los clicks en botones"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    register_user(user.id, user.username, user.first_name, user.last_name)
    log_interaction(user.id, f"button_{query.data}", query.data)
    
    # Botones del menú principal
    if query.data == 'privacy_vip':
        await query.message.reply_text(TEXTO_PRIVACY_VIP, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'privacy_free':
        await query.message.reply_text(TEXTO_PRIVACY_FREE, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'beacons':
        await query.message.reply_text(TEXTO_BEACONS, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'canal':
        await query.message.reply_text(TEXTO_CANAL, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'onlyfans':
        await query.message.reply_text(TEXTO_ONLYFANS, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'sobre_mim':
        await query.message.reply_text(TEXTO_SOBRE_MIM, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'atendimento':
        context.user_data['atendimento_ativo'] = True
        await query.message.reply_text(TEXTO_ATENDIMENTO, parse_mode='Markdown')
        
        # Notificar al admin
        try:
            user_info = f"👤 *Novo Contato*\n\n" \
                       f"Nome: {user.first_name} {user.last_name or ''}\n" \
                       f"Username: @{user.username or 'sem username'}\n" \
                       f"ID: `{user.id}`\n\n" \
                       f"💬 Usuário solicitou atendimento humano."
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=user_info, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error notificando admin: {e}")
    
    elif query.data == 'volver':
        try:
            await query.message.reply_photo(
                photo=IMAGEN_BIENVENIDA,
                caption=TEXTO_BIENVENIDA,
                parse_mode='Markdown',
                reply_markup=crear_menu_principal()
            )
        except:
            await query.message.reply_text(TEXTO_BIENVENIDA, parse_mode='Markdown', reply_markup=crear_menu_principal())
    
    # Botones de admin
    elif query.data == 'admin_stats':
        if str(user.id) == ADMIN_CHAT_ID:
            stats = get_user_stats()
            mensaje = f"""📊 *ESTATÍSTICAS DO BOT*

👥 Total: {stats['total_users']} usuários
🆕 Hoje: {stats['users_today']} novos
🔥 Mais popular: {stats['popular_action']}
💬 Interações: {stats['total_interactions']}"""
            await query.message.reply_text(mensaje, parse_mode='Markdown')
    
    elif query.data == 'admin_users':
        if str(user.id) == ADMIN_CHAT_ID:
            conn = sqlite3.connect('bot_database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, first_name, username, registration_date FROM users ORDER BY registration_date DESC LIMIT 20')
            users = cursor.fetchall()
            conn.close()
            
            mensaje = "👥 *ÚLTIMOS 20 USUÁRIOS*\n\n"
            for u in users:
                mensaje += f"• {u[1]} (@{u[2] or 'N/A'}) - ID: `{u[0]}`\n"
            
            await query.message.reply_text(mensaje, parse_mode='Markdown')
    
    elif query.data == 'admin_broadcast':
        if str(user.id) == ADMIN_CHAT_ID:
            context.user_data['esperando_broadcast'] = True
            await query.message.reply_text(
                "📢 *MENSAGEM EM MASSA*\n\nEnvie a mensagem que deseja enviar para todos os usuários.\n\n⚠️ Para cancelar, envie /cancel",
                parse_mode='Markdown'
            )
    
    elif query.data == 'admin_close':
        await query.message.delete()

def crear_boton_volver():
    """Botón para volver al menú"""
    keyboard = [[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data='volver')]]
    return InlineKeyboardMarkup(keyboard)

async def mensaje_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto"""
    user = update.effective_user
    
    # Broadcast mode (solo admin)
    if context.user_data.get('esperando_broadcast', False) and str(user.id) == ADMIN_CHAT_ID:
        context.user_data['esperando_broadcast'] = False
        
        mensaje_broadcast = update.message.text
        user_ids = get_all_user_ids()
        
        await update.message.reply_text(f"📤 Enviando para {len(user_ids)} usuários...")
        
        enviados = 0
        for uid in user_ids:
            try:
                await context.bot.send_message(chat_id=uid, text=mensaje_broadcast, parse_mode='Markdown')
                enviados += 1
            except Exception as e:
                logger.error(f"Error enviando a {uid}: {e}")
        
        await update.message.reply_text(f"✅ Mensagem enviada para {enviados}/{len(user_ids)} usuários!")
        return
    
    # Atención humana
    if context.user_data.get('atendimento_ativo', False):
        # Guardar mensaje en BD
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO human_attention (user_id, message, timestamp)
            VALUES (?, ?, ?)
        ''', (user.id, update.message.text, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        
        # Reenviar al admin
        try:
            user_info = f"💬 *Mensagem de:*\n{user.first_name} (@{user.username or 'N/A'})\nID: `{user.id}`\n\n*Mensagem:*\n{update.message.text}"
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=user_info, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error reenviando mensaje: {e}")
    else:
        await update.message.reply_text(
            "Use /start para ver o menu principal 😊",
            reply_markup=crear_menu_principal()
        )

# ==================== SERVIDOR HTTP ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot Online!')
    
    def log_message(self, format, *args):
        pass

def run_http_server():
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Servidor HTTP: puerto {port} ✅")
    server.serve_forever()

# ==================== MAIN ====================
def main():
    """Inicia el bot"""
    init_database()
    
    # Servidor HTTP
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Bot
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_handler))
    
    logger.info("🤖 Bot 2.0 iniciado! ✅")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
