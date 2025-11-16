import os
import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import random
import string

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIGURACIÓN ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "7519505004:AAFUmyDOpcGYW9yaAov6HlrgOhYWZ5X5mqo")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6368408762")
IMAGEN_BIENVENIDA = os.getenv("IMAGEN_BIENVENIDA", "https://i.imgur.com/fMLXHgl.jpg")
BOT_USERNAME = os.getenv("BOT_USERNAME", "JackLoppesBot")

# Configuración de referidos
REFERIDOS_NECESARIOS = 5  # Cantidad de referidos para premio
PREMIO_REFERIDO = "30% OFF en Privacy VIP"  # Descripción del premio

# ==================== BASE DE DATOS EXPANDIDA ====================
def init_database():
    """Inicializa la base de datos con todas las tablas necesarias"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Tabla de usuarios ampliada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registration_date TEXT,
            last_interaction TEXT,
            total_interactions INTEGER DEFAULT 0,
            referido_por INTEGER DEFAULT NULL,
            puntos_referido INTEGER DEFAULT 0,
            estado_privacy TEXT DEFAULT 'ninguno',
            FOREIGN KEY (referido_por) REFERENCES users (user_id)
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
    
    # Tabla de referidos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referidor_id INTEGER,
            referido_id INTEGER,
            fecha TEXT,
            recompensa_reclamada INTEGER DEFAULT 0,
            FOREIGN KEY (referidor_id) REFERENCES users (user_id),
            FOREIGN KEY (referido_id) REFERENCES users (user_id)
        )
    ''')
    
    # Tabla de cupones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cupones (
            codigo TEXT PRIMARY KEY,
            user_id INTEGER,
            descuento TEXT,
            usado INTEGER DEFAULT 0,
            fecha_creacion TEXT,
            fecha_expiracion TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Tabla de conversiones (tracking de Privacy)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tipo_plan TEXT,
            cupon_usado TEXT,
            fecha TEXT,
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
    logger.info("✅ Base de datos inicializada con todas las tablas")

def register_user(user_id, username, first_name, last_name, referido_por=None):
    """Registra o actualiza un usuario"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    exists = cursor.fetchone()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not exists:
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, registration_date, last_interaction, total_interactions, referido_por)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        ''', (user_id, username, first_name, last_name, now, now, referido_por))
        
        # Si fue referido, registrar en tabla de referidos
        if referido_por:
            cursor.execute('''
                INSERT INTO referrals (referidor_id, referido_id, fecha)
                VALUES (?, ?, ?)
            ''', (referido_por, user_id, now))
            
            # Sumar punto al referidor
            cursor.execute('UPDATE users SET puntos_referido = puntos_referido + 1 WHERE user_id = ?', (referido_por,))
        
        logger.info(f"✅ Nuevo usuario: {first_name} ({user_id}){' - Referido por: ' + str(referido_por) if referido_por else ''}")
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
    """Registra una interacción"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO interactions (user_id, action_type, action_data, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (user_id, action_type, action_data, now))
    conn.commit()
    conn.close()

def generar_cupon(user_id, descuento, dias_expiracion=30):
    """Genera un cupón único para un usuario"""
    codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    now = datetime.now()
    expira = (now + timedelta(days=dias_expiracion)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO cupones (codigo, user_id, descuento, fecha_creacion, fecha_expiracion)
        VALUES (?, ?, ?, ?, ?)
    ''', (codigo, user_id, descuento, now.strftime('%Y-%m-%d %H:%M:%S'), expira))
    
    conn.commit()
    conn.close()
    return codigo

def get_referidos_count(user_id):
    """Obtiene cantidad de referidos de un usuario"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referidor_id = ?', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_user_stats():
    """Obtiene estadísticas completas"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Total usuarios
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    # Usuarios hoy
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM users WHERE registration_date LIKE ?', (f'{today}%',))
    users_today = cursor.fetchone()[0]
    
    # Usuarios últimos 7 días
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM users WHERE registration_date >= ?', (week_ago,))
    users_week = cursor.fetchone()[0]
    
    # Activos últimos 7 días
    cursor.execute('SELECT COUNT(*) FROM users WHERE last_interaction >= ?', (week_ago,))
    activos_week = cursor.fetchone()[0]
    
    # Botón más clickeado
    cursor.execute('''
        SELECT action_type, COUNT(*) as count 
        FROM interactions 
        WHERE action_type LIKE 'button_%'
        GROUP BY action_type 
        ORDER BY count DESC 
        LIMIT 1
    ''')
    popular = cursor.fetchone()
    popular_action = popular[0].replace('button_', '') if popular else "N/A"
    popular_count = popular[1] if popular else 0
    
    # Total interacciones
    cursor.execute('SELECT COUNT(*) FROM interactions')
    total_interactions = cursor.fetchone()[0]
    
    # Stats de referidos
    cursor.execute('SELECT COUNT(*) FROM referrals')
    total_referidos = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT u.first_name, u.username, COUNT(r.referido_id) as refs
        FROM users u
        LEFT JOIN referrals r ON u.user_id = r.referidor_id
        GROUP BY u.user_id
        ORDER BY refs DESC
        LIMIT 1
    ''')
    top_referidor = cursor.fetchone()
    
    # Tasa de engagement
    engagement = (activos_week / total_users * 100) if total_users > 0 else 0
    
    conn.close()
    
    return {
        'total_users': total_users,
        'users_today': users_today,
        'users_week': users_week,
        'activos_week': activos_week,
        'popular_action': popular_action,
        'popular_count': popular_count,
        'total_interactions': total_interactions,
        'total_referidos': total_referidos,
        'top_referidor': top_referidor,
        'engagement': engagement
    }

def get_all_user_ids():
    """Obtiene todos los IDs de usuarios"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return user_ids

# ==================== TEXTOS MEJORADOS ====================
TEXTO_BIENVENIDA = """✨ *Oi, meu bem!* ✨

Seja muito bem-vindo ao meu cantinho especial 💛

Aqui você encontra:
🔥 Todo o meu conteúdo exclusivo
🌐 Todos os meus links importantes  
💬 Contato direto comigo

👇 *Escolha uma opção abaixo:*"""

TEXTO_PRIVACY_VIP = """💛 *PRIVACY VIP* 💛

🔥 *O conteúdo mais exclusivo e picante!*

✨ O que você encontra:
📸 Fotos sensuais em alta resolução
🎥 Vídeos completos e explícitos
💌 Conteúdo que não posto em outro lugar
⚡ Atualizações quase diárias
🔞 Material adulto sem censura

💰 *Investimento que vale a pena!*

👉 *Assine agora:*
https://privacy.com.br/profile/jackloppes

🎁 *Use o cupón TELEGRAM10 para 10% OFF!*"""

TEXTO_PRIVACY_FREE = """💙 *PRIVACY FREE* 💙

👀 *Quer conhecer meu trabalho antes?*

🎁 Aqui você encontra:
📸 Fotos de preview gratuitas
✨ Conteúdo leve para você ver minha qualidade
🔓 Acesso sem compromisso
💯 Totalmente grátis

*Perfeito para você decidir se quer ir pro VIP depois!*

👉 *Acesse grátis:*
https://privacy.com.br/profile/jackloppesfree"""

TEXTO_BEACONS = """🌐 *TODOS OS MEUS LINKS* 🌐

📱 *Me encontre em todas as redes!*

Neste link você encontra:
• Instagram
• TikTok  
• Twitter
• E muito mais!

*Não perca nenhuma novidade, me siga em todas! 💛*

👉 *Acesse aqui:*
https://beacons.ai/jaqueline_loppes"""

TEXTO_CANAL = """📣 *CANAL OFICIAL DO TELEGRAM* 📣

💛 *Entre agora e fique por dentro de tudo!*

No canal você recebe:
✨ Novidades em primeira mão
🎁 Promoções e cupons exclusivos
📸 Prévias do conteúdo novo
🔥 Avisos de lives e lançamentos
💬 Interação direta

*Não fique de fora!*

👉 *Entre agora:*
https://t.me/jackloppesbr"""

TEXTO_ONLYFANS = """🔥 *ONLYFANS* 🔥

💋 *O lugar do meu conteúdo MAIS picante!*

🔞 O que tem lá:
📸 Fotos e vídeos explícitos
💌 Conteúdo personalizado sob demanda
💬 Chat direto e privado comigo
⭐ Material exclusivo que só existe lá
🎁 Sets completos de fotos

*A plataforma mais completa!*

👉 *Assine agora:*
https://onlyfans.com/jackloppess"""

TEXTO_SOBRE_MIM = """⭐ *SOBRE MIM* ⭐

💛 *Prazer, eu sou a Jack Loppes!*

Um pouco sobre mim:
📸 Criadora de conteúdo adulto
💫 Apaixonada por fotografia sensual
🎥 Produtora de conteúdo há 3 anos
💖 Adoro conectar com pessoas especiais
✨ Sempre buscando criar conteúdo de qualidade

*Meu objetivo é proporcionar o melhor conteúdo para você!*

Aqui neste bot você pode:
• Acessar todos os meus perfis
• Ver ofertas exclusivas
• Falar diretamente comigo
• Ganhar cupons de desconto

*Seja muito bem-vindo! 🌟*"""

TEXTO_ATENDIMENTO = """💬 *ATENDIMENTO PERSONALIZADO* 💬

Oi, meu bem! 💛

*Agora você está falando diretamente comigo!*

Pode me enviar:
• Dúvidas sobre assinaturas
• Pedidos especiais
• Sugestões de conteúdo
• Qualquer outra coisa

Vou responder assim que possível! 😊

*Fique à vontade!* ✨"""

# ==================== FUNCIONES DEL BOT ====================

def crear_menu_principal():
    """Menú principal"""
    keyboard = [
        [InlineKeyboardButton("💛 Privacy VIP", callback_data='privacy_vip')],
        [InlineKeyboardButton("💙 Privacy FREE", callback_data='privacy_free')],
        [InlineKeyboardButton("🌐 Todos os Links", callback_data='beacons')],
        [InlineKeyboardButton("📣 Canal Telegram", callback_data='canal')],
        [InlineKeyboardButton("🔥 OnlyFans", callback_data='onlyfans')],
        [InlineKeyboardButton("💬 Falar Comigo", callback_data='atendimento')],
        [InlineKeyboardButton("⭐ Sobre Mim", callback_data='sobre_mim')],
        [InlineKeyboardButton("🎁 Meus Referidos", callback_data='referidos')]
    ]
    return InlineKeyboardMarkup(keyboard)

def crear_menu_admin():
    """Menú de administración"""
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard Completo", callback_data='admin_dashboard')],
        [InlineKeyboardButton("👥 Lista Usuários", callback_data='admin_users')],
        [InlineKeyboardButton("🎁 Top Referidores", callback_data='admin_referrals')],
        [InlineKeyboardButton("📢 Broadcast", callback_data='admin_broadcast')],
        [InlineKeyboardButton("🔍 Buscar Usuario", callback_data='admin_search')],
        [InlineKeyboardButton("🔙 Fechar", callback_data='admin_close')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start con sistema de referidos"""
    user = update.effective_user
    
    # Detectar si viene de un link de referido
    referido_por = None
    if context.args and context.args[0].startswith('ref_'):
        try:
            referido_por = int(context.args[0].replace('ref_', ''))
        except:
            pass
    
    register_user(user.id, user.username, user.first_name, user.last_name, referido_por)
    log_interaction(user.id, "start", "Comando /start")
    
    # Si fue referido, notificar al referidor
    if referido_por:
        try:
            referidos = get_referidos_count(referido_por)
            mensaje_referidor = f"🎉 *Novo referido!*\n\n{user.first_name} entrou usando seu link!\n\n📊 Total de referidos: *{referidos}*"
            
            if referidos >= REFERIDOS_NECESARIOS:
                mensaje_referidor += f"\n\n🎁 *Você atingiu {REFERIDOS_NECESARIOS} referidos!*\nUse /referidos para resgatar seu prêmio!"
            
            await context.bot.send_message(chat_id=referido_por, text=mensaje_referidor, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error notificando referidor: {e}")
    
    try:
        await update.message.reply_photo(
            photo=IMAGEN_BIENVENIDA,
            caption=TEXTO_BIENVENIDA,
            parse_mode='Markdown',
            reply_markup=crear_menu_principal()
        )
    except Exception as e:
        logger.error(f"Error enviando imagen: {e}")
        await update.message.reply_text(
            TEXTO_BIENVENIDA,
            parse_mode='Markdown',
            reply_markup=crear_menu_principal()
        )

async def referidos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /referidos - Sistema de referidos"""
    user = update.effective_user
    user_id = user.id
    
    referidos = get_referidos_count(user_id)
    link_referido = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    
    mensaje = f"""🎁 *SISTEMA DE REFERIDOS* 🎁

👥 *Seus referidos:* {referidos}
🎯 *Meta:* {REFERIDOS_NECESARIOS} referidos
🏆 *Prêmio:* {PREMIO_REFERIDO}

📊 *Progresso:* {min(referidos, REFERIDOS_NECESARIOS)}/{REFERIDOS_NECESARIOS}

━━━━━━━━━━━━━━━━━━

🔗 *Seu link único:*
`{link_referido}`

💡 *Como funciona:*
1. Compartilhe seu link com amigos
2. Quando entrarem, você ganha pontos
3. Ao atingir {REFERIDOS_NECESARIOS} referidos, recebe o prêmio!

"""
    
    # Si ya alcanzó la meta
    if referidos >= REFERIDOS_NECESARIOS:
        # Verificar si ya reclamó el premio
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT recompensa_reclamada FROM referrals WHERE referidor_id = ? LIMIT 1', (user_id,))
        result = cursor.fetchone()
        
        # Si nunca reclamó, generar cupón
        if result and not result[0]:
            cupon = generar_cupon(user_id, "30% OFF VIP", 60)
            mensaje += f"""
🎉 *PARABÉNS!* 🎉

Você atingiu a meta!

🎁 *Seu cupom:* `{cupon}`
⏰ *Válido por:* 60 dias
💰 *Desconto:* 30% OFF no Privacy VIP

Use este cupom ao assinar! 💛
"""
            # Marcar como reclamado
            cursor.execute('UPDATE referrals SET recompensa_reclamada = 1 WHERE referidor_id = ?', (user_id,))
            conn.commit()
        else:
            mensaje += "\n✅ *Você já resgatou seu prêmio!*\nContinue referindo para ganhar mais no futuro!"
        
        conn.close()
    
    keyboard = [[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data='volver')]]
    
    await update.message.reply_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panel de administración"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Sem permissão.")
        return
    
    await update.message.reply_text(
        "🔐 *PAINEL DE ADMINISTRAÇÃO*\n\nEscolha uma opção:",
        parse_mode='Markdown',
        reply_markup=crear_menu_admin()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja botones"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    register_user(user.id, user.username, user.first_name, user.last_name)
    log_interaction(user.id, f"button_{query.data}", query.data)
    
    # Botones principales
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
    
    elif query.data == 'referidos':
        referidos = get_referidos_count(user.id)
        link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
        msg = f"""🎁 *REFERIDOS*

👥 Total: *{referidos}*
🎯 Meta: {REFERIDOS_NECESARIOS}
🏆 Prêmio: {PREMIO_REFERIDO}

🔗 Seu link:
`{link}`

Compartilhe com amigos! 💛"""
        await query.message.reply_text(msg, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'atendimento':
        context.user_data['atendimento_ativo'] = True
        await query.message.reply_text(TEXTO_ATENDIMENTO, parse_mode='Markdown')
        
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🔔 *Novo Contato*\n\n{user.first_name} (@{user.username or 'N/A'})\nID: `{user.id}`",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error: {e}")
    
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
    
    # Botones admin
    elif query.data == 'admin_dashboard':
        if str(user.id) == ADMIN_CHAT_ID:
            stats = get_user_stats()
            top = stats['top_referidor']
            top_texto = f"{top[0]} (@{top[1]}) - {top[2]} refs" if top else "N/A"
            
            msg = f"""📊 *DASHBOARD COMPLETO*
━━━━━━━━━━━━━━━━━━

👥 *USUÁRIOS*
Total: {stats['total_users']}
Novos hoje: {stats['users_today']}
Novos (7d): {stats['users_week']}
Ativos (7d): {stats['activos_week']}

📈 *ENGAGEMENT*
Taxa: {stats['engagement']:.1f}%
Interações: {stats['total_interactions']}
Botão top: {stats['popular_action']} ({stats['popular_count']}x)

🎁 *REFERIDOS*
Total: {stats['total_referidos']}
Top: {top_texto}

📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            await query.message.reply_text(msg, parse_mode='Markdown')
    
    elif query.data == 'admin_users':
        if str(user.id) == ADMIN_CHAT_ID:
            conn = sqlite3.connect('bot_database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, first_name, username, registration_date FROM users ORDER BY registration_date DESC LIMIT 15')
            users = cursor.fetchall()
            conn.close()
            
            msg = "👥 *ÚLTIMOS 15 USUÁRIOS*\n\n"
            for u in users:
                msg += f"• {u[1]} (@{u[2] or 'N/A'})\n  ID: `{u[0]}`\n"
            
            await query.message.reply_text(msg, parse_mode='Markdown')
    
    elif query.data == 'admin_referrals':
        if str(user.id) == ADMIN_CHAT_ID:
            conn = sqlite3.connect('bot_database.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.first_name, u.username, COUNT(r.referido_id) as refs
                FROM users u
                LEFT JOIN referrals r ON u.user_id = r.referidor_id
                WHERE refs > 0
                GROUP BY u.user_id
                ORDER BY refs DESC
                LIMIT 10
            ''')
            top = cursor.fetchall()
            conn.close()
            
            msg = "🏆 *TOP 10 REFERIDORES*\n\n"
            for i, t in enumerate(top, 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                msg += f"{emoji} {t[0]} (@{t[1] or 'N/A'}) - *{t[2]} refs*\n"
            
            await query.message.reply_text(msg, parse_mode='Markdown')
    
    elif query.data == 'admin_broadcast':
        if str(user.id) == ADMIN_CHAT_ID:
            context.user_data['esperando_broadcast'] = True
            await query.message.reply_text("📢 Envie a mensagem para broadcast.\n\n/cancel para cancelar.", parse_mode='Markdown')
    
    elif query.data == 'admin_close':
        await query.message.delete()

def crear_boton_volver():
    """Botón volver"""
    keyboard = [[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data='volver')]]
    return InlineKeyboardMarkup(keyboard)

async def mensaje_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto"""
    user = update.effective_user
    
    # Broadcast (solo admin)
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
        
        await update.message.reply_text(f"✅ Enviado: {enviados}/{len(user_ids)}")
        return
    
    # Atención humana
    if context.user_data.get('atendimento_ativo', False):
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO human_attention (user_id, message, timestamp)
            VALUES (?, ?, ?)
        ''', (user.id, update.message.text, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"💬 *Mensagem de:*\n{user.first_name} (@{user.username or 'N/A'})\nID: `{user.id}`\n\n*Mensagem:*\n{update.message.text}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error: {e}")
    else:
        await update.message.reply_text(
            "Use /start para ver o menu 😊",
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
    logger.info(f"HTTP Server: {port} ✅")
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
    application.add_handler(CommandHandler("referidos", referidos_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_handler))
    
    logger.info("🤖 Bot 3.0 PRO iniciado! ✅")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
