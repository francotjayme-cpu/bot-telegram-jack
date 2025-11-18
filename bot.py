"""
BOT DE TELEGRAM - JACK LOPPES
Estrategia Vainilla - Novia Virtual
Versión Optimizada y Limpia
"""

import os
import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import random
import asyncio
import requests

# Importar configuración (si usás archivo separado, sino usa las variables de abajo)
try:
    from config import *
except ImportError:
    # Si no existe config.py, usar configuración inline
    BOT_TOKEN = os.getenv("BOT_TOKEN", "7519505004:AAFUmyDOpcGYW9yaAov6HlrgOhYWZ5X5mqo")
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6368408762")
    IMAGEN_BIENVENIDA = os.getenv("IMAGEN_BIENVENIDA", "AgACAgEAAxkBAAE98RdpGrNPkBPmP7N9CjA0tIg4DGGMngACSwtrG_9m0UT4aLfg05fqLgEAAwIAA3kAAzYE")
    BOT_USERNAME = os.getenv("BOT_USERNAME", "JackLoppesBot")
    REFERIDOS_NECESARIOS = 5
    PREMIO_REFERIDO = "Acesso especial a conteúdo exclusivo"
    FUNNEL_DAYS = [0, 1, 3, 5, 7]
    INACTIVE_DAYS = 3
    LOST_DAYS = 7
    DAILY_CONTENT_HOURS = [21, 22, 23, 0, 1]
    
    # Importar textos desde config.py si existe
    exec(open('config.py').read()) if os.path.exists('config.py') else None

# Configurar logging con más detalle
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== BASE DE DATOS ====================

def init_database():
    """Inicializa la base de datos SQLite con todas las tablas necesarias"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Usuarios
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
            segment TEXT DEFAULT 'nuevo',
            FOREIGN KEY (referido_por) REFERENCES users (user_id)
        )
    ''')
    
    # Interacciones
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
    
    # Referidos
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
    
    # Funnel
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funnel_status (
            user_id INTEGER,
            day_number INTEGER,
            sent INTEGER DEFAULT 0,
            sent_date TEXT,
            PRIMARY KEY (user_id, day_number),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Contenido diario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_url TEXT,
            caption TEXT,
            sent_count INTEGER DEFAULT 0,
            last_sent TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Base de datos inicializada")

def register_user(user_id, username, first_name, last_name, referido_por=None):
    """Registra o actualiza un usuario"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    exists = cursor.fetchone()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not exists:
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, registration_date, last_interaction, total_interactions, referido_por, segment)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, 'nuevo')
        ''', (user_id, username, first_name, last_name, now, now, referido_por))
        
        # Inicializar funnel
        for day in FUNNEL_DAYS:
            cursor.execute('INSERT INTO funnel_status (user_id, day_number, sent) VALUES (?, ?, 0)', (user_id, day))
        
        # Registrar referido
        if referido_por:
            cursor.execute('INSERT INTO referrals (referidor_id, referido_id, fecha) VALUES (?, ?, ?)', 
                         (referido_por, user_id, now))
            cursor.execute('UPDATE users SET puntos_referido = puntos_referido + 1 WHERE user_id = ?', (referido_por,))
        
        logger.info(f"✅ Nuevo usuario: {first_name} ({user_id})")
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
    cursor.execute('INSERT INTO interactions (user_id, action_type, action_data, timestamp) VALUES (?, ?, ?, ?)',
                  (user_id, action_type, action_data, now))
    conn.commit()
    conn.close()

def update_user_segment(user_id):
    """Actualiza el segmento del usuario según comportamiento"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT registration_date, last_interaction FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return
    
    reg_date = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
    last_int = datetime.strptime(result[1], '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    
    days_since_reg = (now - reg_date).days
    days_since_int = (now - last_int).days
    
    # Determinar segmento
    if days_since_int > LOST_DAYS:
        segment = 'perdido'
    elif days_since_int > INACTIVE_DAYS:
        segment = 'inactivo'
    elif days_since_reg <= 3:
        segment = 'nuevo'
    else:
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id = ? AND action_type = ?', 
                      (user_id, 'button_privacy_vip'))
        vip_clicks = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id = ? AND action_type = ?',
                      (user_id, 'button_privacy_free'))
        free_clicks = cursor.fetchone()[0]
        
        segment = 'interesado' if vip_clicks > 0 else ('curioso' if free_clicks > 0 else 'activo')
    
    cursor.execute('UPDATE users SET segment = ? WHERE user_id = ?', (segment, user_id))
    conn.commit()
    conn.close()

def get_referidos_count(user_id):
    """Cuenta referidos de un usuario"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referidor_id = ?', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_user_stats():
    """Estadísticas completas del bot"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM users WHERE registration_date LIKE ?', (f'{today}%',))
    users_today = cursor.fetchone()[0]
    
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM users WHERE registration_date >= ?', (week_ago,))
    users_week = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE last_interaction >= ?', (week_ago,))
    activos_week = cursor.fetchone()[0]
    
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
    
    cursor.execute('SELECT COUNT(*) FROM interactions')
    total_interactions = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM referrals')
    total_referidos = cursor.fetchone()[0]
    
    cursor.execute('SELECT segment, COUNT(*) FROM users GROUP BY segment')
    segments = dict(cursor.fetchall())
    
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
        'engagement': engagement,
        'segments': segments
    }

def get_all_user_ids(segment=None):
    """Obtiene IDs de usuarios, filtrado opcional por segmento"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    if segment:
        cursor.execute('SELECT user_id FROM users WHERE segment = ?', (segment,))
    else:
        cursor.execute('SELECT user_id FROM users')
    
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return user_ids

# ==================== FUNCIONES DE CONTENIDO ====================

def init_daily_content():
    """Inicializa sistema de contenido diario"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        logger.info("⚠️ No hay contenido diario. Usa /importcontent para agregar fotos.")
    else:
        logger.info(f"✅ Contenido diario: {count} fotos disponibles")

async def send_daily_content(context: ContextTypes.DEFAULT_TYPE):
    """Envía contenido diario a todos los usuarios"""
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        # Obtener contenido menos usado
        cursor.execute('''
            SELECT id, image_url, caption FROM daily_content 
            ORDER BY sent_count ASC, last_sent ASC 
            LIMIT 1
        ''')
        content = cursor.fetchone()
        
        if not content:
            logger.warning("⚠️ No hay contenido disponible")
            conn.close()
            return
        
        content_id, image_url, caption = content
        user_ids = get_all_user_ids()
        
        enviados = 0
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for user_id in user_ids:
            try:
                await context.bot.send_photo(chat_id=user_id, photo=image_url, caption=caption)
                enviados += 1
            except Exception as e:
                logger.error(f"Error enviando a {user_id}: {e}")
        
        # Actualizar contador
        cursor.execute('UPDATE daily_content SET sent_count = sent_count + 1, last_sent = ? WHERE id = ?',
                      (now, content_id))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Contenido diario enviado a {enviados} usuarios")
        
        # Notificar al admin
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"✅ *Conteúdo Diário*\n\nEnviado para: {enviados} usuários\nFoto ID: {content_id}",
                parse_mode='Markdown'
            )
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error en envío diario: {e}")

async def schedule_daily_content(application):
    """Programa el envío diario en horario aleatorio"""
    while True:
        try:
            now = datetime.now()
            target_hour = random.choice(DAILY_CONTENT_HOURS)
            target_time = now.replace(hour=target_hour, minute=random.randint(0, 59), second=0)
            
            if target_time < now:
                target_time += timedelta(days=1)
            
            seconds_until = (target_time - now).total_seconds()
            logger.info(f"⏰ Próximo envío diario: {target_time.strftime('%d/%m/%Y %H:%M')}")
            
            await asyncio.sleep(seconds_until)
            await send_daily_content(application)
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Error en programación diaria: {e}")
            await asyncio.sleep(3600)

# ==================== FUNNEL AUTOMÁTICO ====================

async def check_funnel(context: ContextTypes.DEFAULT_TYPE):
    """Revisa y envía mensajes del funnel automático"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    now = datetime.now()
    cursor.execute('SELECT user_id, registration_date FROM users')
    users = cursor.fetchall()
    
    for user_id, reg_date in users:
        reg_datetime = datetime.strptime(reg_date, '%Y-%m-%d %H:%M:%S')
        days_since_reg = (now - reg_datetime).days
        
        for day in FUNNEL_DAYS:
            if days_since_reg >= day:
                cursor.execute('SELECT sent FROM funnel_status WHERE user_id = ? AND day_number = ?',
                             (user_id, day))
                result = cursor.fetchone()
                
                if result and not result[0]:
                    try:
                        from config import FUNNEL_MESSAGES
                        message = FUNNEL_MESSAGES[day]
                        await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
                        
                        cursor.execute('UPDATE funnel_status SET sent = 1, sent_date = ? WHERE user_id = ? AND day_number = ?',
                                     (now.strftime('%Y-%m-%d %H:%M:%S'), user_id, day))
                        conn.commit()
                        logger.info(f"✅ Funnel día {day} enviado a {user_id}")
                    except Exception as e:
                        logger.error(f"Error enviando funnel a {user_id}: {e}")
    
    conn.close()

# ==================== MENÚS Y COMANDOS ====================

def crear_menu_principal():
    """Menú principal (7 botones)"""
    keyboard = [
        [InlineKeyboardButton("💛 Privacy VIP", callback_data='privacy_vip')],
        [InlineKeyboardButton("💙 Privacy FREE", callback_data='privacy_free')],
        [InlineKeyboardButton("🔥 OnlyFans", callback_data='onlyfans')],
        [InlineKeyboardButton("🌐 Todos os Links", callback_data='beacons')],
        [InlineKeyboardButton("📣 Canal Telegram", callback_data='canal')],
        [InlineKeyboardButton("⭐ Sobre Mim", callback_data='sobre_mim')],
        [InlineKeyboardButton("🎁 Meus Referidos", callback_data='referidos')]
    ]
    return InlineKeyboardMarkup(keyboard)

def crear_menu_admin():
    """Menú admin"""
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data='admin_dashboard')],
        [InlineKeyboardButton("👥 Segmentos", callback_data='admin_segments')],
        [InlineKeyboardButton("📢 Broadcast Total", callback_data='admin_broadcast_all')],
        [InlineKeyboardButton("🎯 Broadcast Segmentado", callback_data='admin_broadcast_segment')],
        [InlineKeyboardButton("🔙 Fechar", callback_data='admin_close')]
    ]
    return InlineKeyboardMarkup(keyboard)

def crear_boton_volver():
    """Botón volver al menú"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data='volver')]])

# ==================== HANDLERS DE COMANDOS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user = update.effective_user
    
    # Detectar referido
    referido_por = None
    if context.args and context.args[0].startswith('ref_'):
        try:
            referido_por = int(context.args[0].replace('ref_', ''))
        except:
            pass
    
    register_user(user.id, user.username, user.first_name, user.last_name, referido_por)
    log_interaction(user.id, "start", "Comando /start")
    update_user_segment(user.id)
    
    # Notificar referidor
    if referido_por:
        try:
            referidos = get_referidos_count(referido_por)
            msg = f"🎉 *Novo referido!*\n\n{user.first_name} entrou!\n\n📊 Total: *{referidos}*"
            if referidos >= REFERIDOS_NECESARIOS:
                msg += f"\n\n🎁 Você atingiu {REFERIDOS_NECESARIOS} referidos! Use /referidos"
            await context.bot.send_message(chat_id=referido_por, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error notificando referidor: {e}")
    
    # Enviar menú con imagen
    try:
        from config import TEXTO_BIENVENIDA
        await update.message.reply_photo(
            photo=IMAGEN_BIENVENIDA,
            caption=TEXTO_BIENVENIDA,
            parse_mode='Markdown',
            reply_markup=crear_menu_principal()
        )
        logger.info(f"✅ Bienvenida enviada a {user.id}")
    except Exception as e:
        logger.error(f"❌ Error enviando imagen: {e}")
        await update.message.reply_text(
            TEXTO_BIENVENIDA,
            parse_mode='Markdown',
            reply_markup=crear_menu_principal()
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    from config import TEXTO_HELP
    await update.message.reply_text(TEXTO_HELP, parse_mode='Markdown')

async def referidos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sistema de referidos"""
    user = update.effective_user
    referidos = get_referidos_count(user.id)
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    
    mensaje = f"""🎁 *SISTEMA DE REFERIDOS*

👥 *Seus referidos:* {referidos}
🎯 *Meta:* {REFERIDOS_NECESARIOS}
🏆 *Prêmio:* {PREMIO_REFERIDO}

📊 *Progresso:* {min(referidos, REFERIDOS_NECESARIOS)}/{REFERIDOS_NECESARIOS}

━━━━━━━━━━━━━━━━━━

🔗 *Seu link único:*
`{link}`

💡 *Como funciona:*
Compartilhe com amigos e ganhe prêmios!
"""
    
    if referidos >= REFERIDOS_NECESARIOS:
        mensaje += f"\n\n🎉 *PARABÉNS!*\nVocê atingiu a meta! Fale comigo para resgatar."
    
    await update.message.reply_text(mensaje, parse_mode='Markdown', reply_markup=crear_boton_volver())

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panel admin"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    await update.message.reply_text(
        "🔐 *PAINEL DE ADMINISTRAÇÃO*",
        parse_mode='Markdown',
        reply_markup=crear_menu_admin()
    )

# ==================== HANDLERS DE BOTONES ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja clicks en botones"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    register_user(user.id, user.username, user.first_name, user.last_name)
    log_interaction(user.id, f"button_{query.data}", query.data)
    update_user_segment(user.id)
    
    logger.info(f"Botón: {query.data} por {user.id}")
    
    # Importar textos
    from config import (TEXTO_PRIVACY_VIP, TEXTO_PRIVACY_FREE, TEXTO_BEACONS,
                       TEXTO_CANAL, TEXTO_ONLYFANS, TEXTO_SOBRE_MIM, TEXTO_BIENVENIDA)
    
    # Botones principales
    if query.data == 'privacy_vip':
        await query.message.reply_text(TEXTO_PRIVACY_VIP, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'privacy_free':
        await query.message.reply_text(TEXTO_PRIVACY_FREE, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'beacons':
        await query.message.reply_text(TEXTO_BEACONS, reply_markup=crear_boton_volver())
    
    elif query.data == 'canal':
        await query.message.reply_text(TEXTO_CANAL, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'onlyfans':
        await query.message.reply_text(TEXTO_ONLYFANS, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'sobre_mim':
        await query.message.reply_text(TEXTO_SOBRE_MIM, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'referidos':
        referidos = get_referidos_count(user.id)
        link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
        msg = f"🎁 *REFERIDOS*\n\n👥 Total: *{referidos}*\n🎯 Meta: {REFERIDOS_NECESARIOS}\n\n🔗 `{link}`"
        await query.message.reply_text(msg, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
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
            
            # Formatear segmentos sin Markdown problemático
            segments_list = []
            emojis = {"nuevo": "🆕", "curioso": "👀", "interesado": "🔥", "inactivo": "😴", "perdido": "💔", "activo": "💛"}
            for seg, count in stats['segments'].items():
                segments_list.append(f"{emojis.get(seg, '•')} {seg.title()}: {count}")
            segments_text = "\n".join(segments_list)
            
            # Mensaje sin caracteres problemáticos
            msg = f"""📊 DASHBOARD

👥 Total: {stats['total_users']}
🆕 Hoje: {stats['users_today']}
📈 Semana: {stats['users_week']}
💚 Ativos: {stats['activos_week']}

🔥 Engagement: {stats['engagement']:.1f}%
⚡ Interações: {stats['total_interactions']}
👆 Top: {stats['popular_action']}

🎁 Referidos: {stats['total_referidos']}

🎯 SEGMENTOS:
{segments_text}

📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            # Enviar SIN parse_mode para evitar errores
            await query.message.reply_text(msg)
    
    elif query.data == 'admin_segments':
        if str(user.id) == ADMIN_CHAT_ID:
            stats = get_user_stats()
            msg = "🎯 *SEGMENTOS*\n\n"
            emojis = {"nuevo": "🆕", "curioso": "👀", "interesado": "🔥", "inactivo": "😴", "perdido": "💔", "activo": "💛"}
            for seg, count in stats['segments'].items():
                msg += f"{emojis.get(seg, '•')} {seg.title()}: {count}\n"
            await query.message.reply_text(msg, parse_mode='Markdown')
    
    elif query.data == 'admin_broadcast_all':
        if str(user.id) == ADMIN_CHAT_ID:
            context.user_data['broadcast_type'] = 'all'
            await query.message.reply_text("📢 Envie a mensagem para TODOS.")
    
    elif query.data == 'admin_broadcast_segment':
        if str(user.id) == ADMIN_CHAT_ID:
            keyboard = [
                [InlineKeyboardButton("🆕 Nuevos", callback_data='bc_nuevo')],
                [InlineKeyboardButton("👀 Curiosos", callback_data='bc_curioso')],
                [InlineKeyboardButton("🔥 Interesados", callback_data='bc_interesado')],
                [InlineKeyboardButton("😴 Inactivos", callback_data='bc_inactivo')],
                [InlineKeyboardButton("💔 Perdidos", callback_data='bc_perdido')],
                [InlineKeyboardButton("🔙 Cancelar", callback_data='admin_close')]
            ]
            await query.message.reply_text("🎯 Escolha o segmento:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith('bc_'):
        if str(user.id) == ADMIN_CHAT_ID:
            segment = query.data.replace('bc_', '')
            context.user_data['broadcast_type'] = 'segment'
            context.user_data['broadcast_segment'] = segment
            await query.message.reply_text(f"📢 Mensagem para: *{segment}*", parse_mode='Markdown')
    
    elif query.data == 'admin_close':
        await query.message.delete()

async def mensaje_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto"""
    user = update.effective_user
    
    # Broadcast
    if context.user_data.get('broadcast_type') and str(user.id) == ADMIN_CHAT_ID:
        broadcast_type = context.user_data['broadcast_type']
        mensaje = update.message.text
        
        if broadcast_type == 'all':
            user_ids = get_all_user_ids()
        else:
            segment = context.user_data.get('broadcast_segment')
            user_ids = get_all_user_ids(segment)
        
        await update.message.reply_text(f"📤 Enviando para {len(user_ids)} usuários...")
        
        enviados = 0
        for uid in user_ids:
            try:
                await context.bot.send_message(chat_id=uid, text=mensaje, parse_mode='Markdown')
                enviados += 1
            except Exception as e:
                logger.error(f"Error: {e}")
        
        await update.message.reply_text(f"✅ Enviado: {enviados}/{len(user_ids)}")
        context.user_data.clear()
        return
    
    # Otros mensajes
    await update.message.reply_text("Use /start para ver o menu 😊", reply_markup=crear_menu_principal())

# ==================== COMANDOS ADMIN - CONTENIDO ====================

async def add_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Agregar contenido diario"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Uso: /addcontent [URL] [caption]\n\nExemplo:\n/addcontent https://i.ibb.co/ABC/foto.jpg Boa noite 💛"
        )
        return
    
    url = context.args[0]
    caption = " ".join(context.args[1:])
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO daily_content (image_url, caption, sent_count) VALUES (?, ?, 0)', (url, caption))
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    total = cursor.fetchone()[0]
    conn.close()
    
    await update.message.reply_text(f"✅ Adicionado!\n\n📊 Total: {total} fotos")

async def import_imgbb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Importa las 33 fotos de ImgBB"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    # URLs directas de ImgBB
    direct_urls = [
        "https://i.ibb.co/SXvDNtvY/Imagen-de-Whats-App-2025-11-05-a-las-13-45-17-0b1cbd92.jpg",
        "https://i.ibb.co/5gfKzpjm/Imagen-de-Whats-App-2025-11-05-a-las-13-45-17-99293d9a.jpg",
        "https://i.ibb.co/Rp6ct9sY/IMG-20251103-WA0123.jpg",
        "https://i.ibb.co/wGwMM8M/IMG-20251115-WA0083.jpg",
        "https://i.ibb.co/R4sr42Md/IMG-20251115-WA0084.jpg",
        "https://i.ibb.co/gbYcgz80/IMG-20251115-WA0085.jpg",
        "https://i.ibb.co/ksCYNw7k/IMG-20251115-WA0087.jpg",
        "https://i.ibb.co/G6NmsW5/IMG-20251116-WA0134.jpg",
        "https://i.ibb.co/WNPkrvHV/IMG-20251116-WA0135.jpg",
        "https://i.ibb.co/RGsXvkfv/IMG-20251116-WA0136.jpg",
        "https://i.ibb.co/M5hS006d/IMG-20251116-WA0137.jpg",
        "https://i.ibb.co/k6rKMmxB/IMG-20251116-WA0138.jpg",
        "https://i.ibb.co/V0tzpjWJ/IMG-20251116-WA0139.jpg",
        "https://i.ibb.co/Mk1WtCdX/IMG-20251116-WA0140.jpg",
        "https://i.ibb.co/5xG1bF0R/IMG-20251116-WA0141.jpg",
        "https://i.ibb.co/YBdCxDz2/IMG-20251116-WA0142.jpg",
        "https://i.ibb.co/mFSfHzc3/IMG-20251116-WA0143.jpg",
        "https://i.ibb.co/xSmwWJJ2/IMG-20251116-WA0144.jpg",
        "https://i.ibb.co/Nd5kt0bg/IMG-20251116-WA0145.jpg",
        "https://i.ibb.co/DJHy3C4/IMG-20251116-WA0146.jpg",
        "https://i.ibb.co/4RbQxqcG/IMG-20251116-WA0147.jpg",
        "https://i.ibb.co/0yLsgCRp/IMG-20251116-WA0148.jpg",
        "https://i.ibb.co/dsfbVQms/IMG-20251116-WA0149.jpg",
        "https://i.ibb.co/Mxzm5Tnc/IMG-20251116-WA0150.jpg",
        "https://i.ibb.co/vxhYGVWB/IMG-20251116-WA0151.jpg",
        "https://i.ibb.co/Q3pJjwLw/IMG-20251116-WA0152.jpg",
        "https://i.ibb.co/twH5F3jn/IMG-20251116-WA0153.jpg",
        "https://i.ibb.co/DgRMN03B/IMG-20251116-WA0154.jpg",
        "https://i.ibb.co/zWvTrkD2/IMG-20251116-WA0155.jpg",
        "https://i.ibb.co/BH2g2bZN/IMG-20251116-WA0156.jpg",
        "https://i.ibb.co/93mGyMmS/IMG-20251116-WA0157.jpg",
        "https://i.ibb.co/whdT8MMr/IMG-20251116-WA0158.jpg",
        "https://i.ibb.co/tMqgZ8s4/IMG-20251116-WA0159.jpg"
    ]
    
    from config import DAILY_CAPTIONS
    
    await update.message.reply_text("📥 Importando 33 fotos...")
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    importados = 0
    for url in direct_urls:
        try:
            caption = random.choice(DAILY_CAPTIONS)
            cursor.execute('INSERT INTO daily_content (image_url, caption, sent_count) VALUES (?, ?, 0)', (url, caption))
            importados += 1
        except Exception as e:
            logger.error(f"Error: {e}")
    
    conn.commit()
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    total = cursor.fetchone()[0]
    conn.close()
    
    await update.message.reply_text(f"✅ Importado!\n\n📸 Importados: {importados}\n📊 Total: {total}")

async def list_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista contenido"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, sent_count FROM daily_content ORDER BY id LIMIT 10')
    content = cursor.fetchall()
    conn.close()
    
    if not content:
        await update.message.reply_text("❌ Nenhum conteúdo.")
        return
    
    msg = "📸 *CONTEÚDO*\n\n"
    for c in content:
        msg += f"ID: {c[0]} | Enviado: {c[1]}x\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def delete_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elimina contenido por ID"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    if not context.args:
        await update.message.reply_text("❌ Uso: /delcontent [ID]")
        return
    
    content_id = context.args[0]
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM daily_content WHERE id = ?', (content_id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Deletado: {content_id}")

async def delete_all_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elimina TODO el contenido"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    count = cursor.fetchone()[0]
    cursor.execute('DELETE FROM daily_content')
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"🗑️ Deletados: {count} itens")

# ==================== BACKUP AUTOMÁTICO ====================

async def backup_database(context: ContextTypes.DEFAULT_TYPE):
    """Hace backup de la BD y la envía al admin"""
    try:
        import shutil
        from datetime import datetime
        
        # Copiar BD
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'backup_bot_{timestamp}.db'
        shutil.copy('bot_database.db', backup_name)
        
        # Enviar al admin
        with open(backup_name, 'rb') as f:
            await context.bot.send_document(
                chat_id=ADMIN_CHAT_ID,
                document=f,
                filename=backup_name,
                caption=f"📦 *Backup Automático*\n\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n✅ Base de dados salva!",
                parse_mode='Markdown'
            )
        
        # Eliminar archivo local para no llenar espacio
        import os
        os.remove(backup_name)
        
        logger.info(f"✅ Backup enviado: {backup_name}")
        
    except Exception as e:
        logger.error(f"❌ Error en backup: {e}")
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"⚠️ Erro no backup: {e}"
            )
        except:
            pass

async def schedule_backups(application):
    """Programa backups cada 6 horas"""
    while True:
        try:
            await backup_database(application)
            await asyncio.sleep(21600)  # 6 horas
        except Exception as e:
            logger.error(f"Error en schedule_backups: {e}")
            await asyncio.sleep(21600)

# ==================== IMPORTAR CONTACTOS ====================

async def import_contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Importa los 509 contactos del bot anterior"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    # Lista de los 509 IDs
    old_contacts = [
        6368408762, 7519505004, 7196184634, 7723659270, 404989065, 6321691912, 6329562703, 912014471,
        6063585046, 7325714780, 6480419273, 1868036611, 762177618, 5773753629, 5587645842, 6983021095,
        6109755569, 5347462885, 1257916990, 6824488625, 5444924408, 7810186076, 6820925579, 5322912200,
        1304703978, 8151807574, 7564059535, 1285216987, 6884496567, 5121634240, 996059764, 5846687627,
        1700953010, 7562792939, 5262352806, 7081682693, 1330444082, 5901200726, 5244161036, 5911783184,
        2005834574, 7168878896, 5084228931, 761851086, 1319270006, 7181803145, 5098236953, 7836194105,
        1354825072, 5919834696, 1269313274, 6821949423, 7506868943, 1096381701, 6059790320, 1864262429,
        1795469026, 6028691409, 5375123308, 216671574, 6042155257, 6145734834, 1386067562, 7134261250,
        7358938054, 5527515780, 1939927532, 916692617, 1356520928, 7400124808, 7992971946, 7970226484,
        6821243278, 5363753521, 949143774, 6804458896, 5666566708, 6322019774, 1669590544, 6872253096,
        8414853368, 6809719496, 6273558398, 1809696267, 2056814347, 5791416031, 5788121996, 1556014545,
        5850631953, 6303564305, 1400892956, 7579595754, 2001788052, 6387223037, 6231147114, 6412816620,
        7573953400, 6376273044, 724610925, 7681381692, 6142859623, 1457909758, 2119164516, 1920045638,
        6101249980, 8433921712, 1697107576, 5412674618, 6741558166, 7253201164, 1086754710, 6358339974,
        7318113557, 8129076809, 7244522049, 1248157448, 2088599877, 7529382329, 1610882441, 5310943636,
        5983913481, 5646697505, 1914179678, 6681892925, 6432755217, 6879554996, 5957959350, 7068866468,
        5335714069, 6173266513, 7116943545, 1257918181, 1700137250, 5402204966, 5457978113, 5077251397,
        6231840311, 7297429452, 5840869762, 6733910324, 2142804677, 5198336426, 906173934, 5960781046,
        8477648094, 6654892337, 7099091633, 677717836, 5576686726, 6946295278, 6954938827, 7349154082,
        1748059668, 1322520377, 1054158384, 927810273, 7708424163, 1037928453, 6096295536, 5888485875,
        2054445052, 7503638881, 6921958183, 7983723158, 7419679652, 1693166348, 5093693659, 7333443885,
        6739985930, 1655580373, 7875752393, 6579240444, 8023274210, 1150397347, 6654582551, 6423480785,
        7235022163, 8141001098, 1623229527, 1528111155, 7683621222, 5678362203, 7086650965, 5675362802,
        7021340527, 821256390, 2037188520, 5974549402, 6311473196, 7857658195, 1235122416, 6439723452,
        7254023509, 5527802370, 615209164, 7098519438, 6634918482, 6920484298, 6685990861, 794165301,
        7889380338, 6367881912, 8167141955, 630422488, 5598761152, 2007282668, 6704884799, 1992692601,
        6757041232, 1698842005, 1100843687, 1060780064, 6407775053, 605682174, 1450165170, 1279187119,
        6335778230, 5220423087, 8075661670, 6410625382, 6332664354, 6131681570, 5214007634, 1220374545,
        1752996329, 8429599191, 6178710026, 8106391313, 5753575016, 5546856632, 1725705398, 2035214892,
        6705681192, 1768600228, 5503729552, 7654047959, 5035631254, 6258944387, 1914426755, 1133971702,
        7909584896, 6437155575, 1978543992, 1788915597, 5036997168, 1639523661, 7426212425, 5996189940,
        1886607605, 8011690244, 6129084465, 5734236951, 5844294320, 5772419329, 8192438850, 5744274646,
        6082973894, 1403786258, 8045138310, 8062379465, 5828442777, 7143151315, 8220738984, 1340328922,
        1260157298, 6773023785, 1008549153, 7943882133, 5271125724, 5704580482, 5605388545, 667507323,
        6764040637, 7905290739, 7610047725, 2054568833, 1798582401, 845328689, 1056089009, 7790493319,
        7160221987, 7141971714, 5082056881, 1503530606, 5498726176, 8124214617, 6116209395, 7635989454,
        1524359065, 7938406562, 8327571049, 5743756318, 7864858799, 723007196, 5807854531, 1017269470,
        7029697555, 5745831489, 6705098018, 8058373460, 869543607, 5844229836, 8488015996, 7955998156,
        6939404529, 5098282152, 5697560629, 8412275149, 5215675855, 184746196, 1889571881, 2105351223,
        7493018848, 6593835904, 6504336604, 5121232306, 5716629017, 6929592938, 6625765590, 6312253674,
        6730714292, 6515411584, 5266487899, 8259672427, 7777237892, 1056516241, 984637412, 5476465920,
        5546104886, 6844194874, 8008542097, 1868452742, 6111096409, 5847343537, 6379951854, 5708305423,
        7573532334, 7826862011, 7624097243, 2034133677, 8124698475, 1168653261, 1781677723, 8171540536,
        6621198996, 7988938408, 5586666095, 2140699725, 7474118729, 6769581758, 8097544841, 2036583547,
        6811321132, 1664858565, 5534923613, 7713771140, 2129904727, 5585174165, 1317663211, 5324669825,
        5925758523, 7532210354, 5236014709, 6504970898, 5454271234, 5397224520, 1616283422, 5895402762,
        7673181269, 6748602156, 5344780176, 1904234431, 5822059306, 7856422320, 5543521191, 5464812495,
        7546864466, 7771622145, 8260942112, 7815471004, 6414290158, 8464424619, 7941767199, 6821619489,
        7699242551, 5211694855, 8373857030, 1983776533, 6642705141, 5836421312, 1939863838, 7513692141,
        7460139192, 1087968824, 7693735681, 1064595503, 5555157588, 6273957792, 6545063839, 5518781666,
        8331533928, 5709737296, 7931674659, 8383422262, 5948006888, 6651524858, 7113855550, 7341926605,
        5043931381, 2052893140, 6976245434, 6702792804, 5214155528, 6890597297, 8027492881, 8275305803,
        1652271648, 1994969972, 8277696811, 6768289263, 5654531031, 6528639395, 8241367137, 1098258094,
        6254735829, 7792280724, 7301342235, 8163859092, 6146394994, 7369135258, 1281240989, 946903703,
        6997411774, 6476274719, 1628684663, 2056437854, 6161036306, 7148631309, 2057995692, 5437900119,
        8004266905, 5359576888, 8280061336, 6787679727, 8268864201, 8335637659, 1398589391, 1244223813,
        924459737, 6368867130, 1331808996, 1601924523, 7740326229, 6650070182, 1341158980, 2032286350,
        2071648115, 5340739910, 7864189749, 1728559090, 8266495352, 6241218806, 6571734106, 6482300655,
        952335342, 7710923776, 7599919886, 6322226610, 8499204260, 1926665057, 5171275379, 8401424398,
        6855002950, 7051578817, 8324549278, 6947585540, 1428368795, 5861120111, 5873138822, 5454136867,
        8160815067, 5322288276, 6794278466, 7016079544, 2025408428, 6517107222, 6292563237, 5039579873,
        1402633813, 7982170496, 8503592060, 8217814753, 8355987621, 5677533404, 8572392912, 6208506885,
        8174589865, 7425363026, 5421850656, 6057800862, 6897665088, 8315500054, 7375669270, 837796756,
        7411212510, 8108956721, 6393223834, 8138268663, 2086937171, 8216538870
    ]
    
    await update.message.reply_text(f"📥 Importando {len(old_contacts)} contactos... Aguarde...")
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    importados = 0
    ya_existian = 0
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for user_id in old_contacts:
        try:
            # Verificar si ya existe
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone()
            
            if not exists:
                # Registrar como usuario recuperado
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, registration_date, last_interaction, total_interactions, segment)
                    VALUES (?, ?, ?, ?, ?, ?, 0, 'recuperado')
                ''', (user_id, None, f"User_{user_id}", None, now, now))
                
                # Inicializar funnel
                for day in FUNNEL_DAYS:
                    cursor.execute('INSERT INTO funnel_status (user_id, day_number, sent) VALUES (?, ?, 0)', (user_id, day))
                
                importados += 1
            else:
                ya_existian += 1
                
        except Exception as e:
            logger.error(f"Error importando {user_id}: {e}")
    
    conn.commit()
    
    # Total ahora
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    conn.close()
    
    msg = f"""✅ *IMPORTACIÓN COMPLETA*

📊 *Resultados:*
• Importados: {importados}
• Ya existían: {ya_existian}
• Total en BD: {total}

🎯 Los contactos recuperados recibirán el funnel desde día 0!"""
    
    await update.message.reply_text(msg, parse_mode='Markdown')
    logger.info(f"✅ Importados {importados} contactos del bot anterior")

async def test_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prueba envío diario"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT image_url, caption FROM daily_content ORDER BY RANDOM() LIMIT 1')
    content = cursor.fetchone()
    conn.close()
    
    if not content:
        await update.message.reply_text("❌ Sem conteúdo")
        return
    
    try:
        await update.message.reply_photo(photo=content[0], caption=content[1])
        await update.message.reply_text("✅ Teste OK!")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")

# ==================== SERVIDOR HTTP ====================

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Servidor HTTP para mantener el bot activo"""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body><h1>Bot Online!</h1><p>Jack Loppes Bot funcionando.</p></body></html>')
    
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body><h1>Bot Online!</h1></body></html>')
    
    def log_message(self, format, *args):
        pass

def run_http_server():
    """Corre servidor HTTP"""
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"✅ HTTP Server: puerto {port}")
    server.serve_forever()

# ==================== TAREAS AUTOMÁTICAS ====================

async def scheduled_tasks(application):
    """Tareas programadas: funnel y contenido"""
    # Iniciar envío diario
    asyncio.create_task(schedule_daily_content(application))
    
    while True:
        try:
            # Revisar funnel cada hora
            await check_funnel(application)
            await asyncio.sleep(3600)
        except Exception as e:
            logger.error(f"Error en tareas: {e}")
            await asyncio.sleep(3600)

# ==================== MAIN ====================

def main():
    """Inicia el bot"""
    logger.info("🚀 Iniciando Bot Jack Loppes...")
    
    # Inicializar BD
    init_database()
    init_daily_content()
    
    # Servidor HTTP
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Bot
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("referidos", referidos_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("addcontent", add_content_command))
    application.add_handler(CommandHandler("importcontacts", import_contacts_command))
    application.add_handler(CommandHandler("importcontent", import_imgbb_command))
    application.add_handler(CommandHandler("listcontent", list_content_command))
    application.add_handler(CommandHandler("delcontent", delete_content_command))
    application.add_handler(CommandHandler("delcontentall", delete_all_content_command))
    application.add_handler(CommandHandler("testdaily", test_daily_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_handler))
    
    # Tareas automáticas
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_tasks(application))
    
    logger.info("✅ Bot iniciado!")
    logger.info("📊 Funnel automático: ACTIVO")
    logger.info("🎯 Segmentación: ACTIVA")
    logger.info("📸 Contenido diario: ACTIVO")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
