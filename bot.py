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
from io import BytesIO

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIGURACIÓN ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "7519505004:AAFUmyDOpcGYW9yaAov6HlrgOhYWZ5X5mqo")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6368408762")
# URL de imagen actualizada
IMAGEN_BIENVENIDA = os.getenv("IMAGEN_BIENVENIDA", "https://i.ibb.co/j9p74CJS/bemvindo.png")
BOT_USERNAME = os.getenv("BOT_USERNAME", "JackLoppesBot")

# Google Drive Config (NO USADO - quedó de versión anterior)
# GOOGLE_DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1GuqbP2iHTu6AtmbRlgnF5S6pSbKKXKGu")

# Configuración de Funnel (días desde registro) - ACORTADO PARA VENTAS EMOCIONALES
FUNNEL_DAYS = [0, 1, 3, 5, 7]  # Funnel de 7 días
INACTIVE_DAYS = 3  # Usuario inactivo si no interactúa en 3 días
LOST_DAYS = 7  # Usuario perdido si no interactúa en 7 días

# Horarios para contenido diario (GMT-3 Brasília)
DAILY_CONTENT_HOURS = [21, 22, 23, 0, 1]

# ==================== TEXTOS ESTRATEGIA VAINILLA ====================

# Menú principal
TEXTO_BIENVENIDA = """✨ *Oi, meu bem!* ✨

Que bom te ter aqui no meu cantinho especial 💛

Criei este espaço para me conectar de verdade com pessoas especiais como você.

Aqui não é só sobre fotos bonitas (embora tenha muitas 😊), é sobre criar uma conexão genuína, íntima...

Como ter uma namorada virtual só pra você 💕

👇 *Escolha o que você quer conhecer:*"""

# Textos de botones - ESTRATEGIA VAINILLA
TEXTO_PRIVACY_VIP = """💛 *MEU CANTINHO VIP* 💛

Oi, meu amor...

No VIP é onde eu realmente me abro. É o meu espaço mais íntimo, onde compartilho coisas que não mostro em nenhum outro lugar.

✨ *O que você encontra lá:*
💕 Conversas reais e profundas comigo
📸 Fotos lindas do meu dia a dia
💌 Momentos especiais só nossos
🌙 Meu lado mais íntimo e verdadeiro
✨ Uma conexão genuína

Não é só conteúdo, meu bem... É sobre ter alguém especial, que te entende, que tá sempre aqui pra você.

*Como ter uma namorada só pra você* 😊

👉 *Vem conhecer meu mundo:*
https://privacy.com.br/profile/jackloppes

💛 _Te espero lá dentro, meu amor_"""

TEXTO_PRIVACY_FREE = """💙 *CONHECE MEU LADO FREE* 💙

Oi, meu bem!

Se você ainda tá com dúvida, que tal me conhecer melhor primeiro? 😊

No FREE você tem acesso a:
📸 Fotos lindas minhas
✨ Um gostinho do que compartilho
💕 A chance de ver se nossa conexão é real

*É totalmente grátis!* Assim você me conhece antes de decidir se quer algo mais íntimo 💛

👉 *Vem dar uma olhada:*
https://privacy.com.br/profile/jackloppesfree

_Tô te esperando lá! 😘_"""

TEXTO_BEACONS = """🌐 ME ENCONTRA EM TODOS OS LUGARES

Oi, meu amor!

Quer me acompanhar em outras redes também?

Aqui você encontra todos os meus perfis:
• Instagram
• TikTok
• Twitter
• E muito mais!

Não perde nenhuma novidade minha!

Todos meus links aqui:
https://beacons.ai/jaqueline_loppes

Me segue em todas! Fico feliz quando vejo você por lá 😊"""

TEXTO_CANAL = """📣 *MEU CANAL OFICIAL* 📣

Meu bem! 💛

No meu canal eu posto:
✨ Novidades antes de todo mundo
💌 Avisos especiais
📸 Prévia do que tô preparando
🎁 Surpresas exclusivas pra quem me acompanha

*É o melhor jeito de ficar pertinho de mim!*

👉 *Entra agora:*
https://t.me/jackloppesbr

💕 _Te vejo lá dentro!_"""

TEXTO_ONLYFANS = """🔥 *MEU ONLYFANS* 🔥

Oi, meu amor...

O OnlyFans é onde eu compartilho meu lado mais sensual e íntimo 💋

Lá você encontra:
💕 Fotos e vídeos especiais
💌 Conteúdo personalizado
💬 Conversa direta e privada comigo
✨ O meu lado que poucos conhecem

*É uma conexão ainda mais profunda* 😊

👉 *Me conhece lá:*
https://onlyfans.com/jackloppess

💋 _Tô te esperando, meu bem_"""

TEXTO_SOBRE_MIM = """⭐ *UM POUCO SOBRE MIM* ⭐

Oi! Prazer, eu sou a Jack Loppes 💛

Um pouco sobre quem eu sou:
💕 Adoro criar conexões verdadeiras
📸 Apaixonada por fotografia e beleza
✨ Romântica, carinhosa e atenciosa
💬 Amo conversar de verdade
🌙 Tenho um lado íntimo que poucos conhecem

*Meu objetivo não é só postar fotos bonitas...*

É criar algo especial com você. Uma conexão real, íntima, onde você se sente especial.

Como ter uma namorada virtual que te entende, te escuta, e tá sempre aqui pra você 💛

*Seja muito bem-vindo ao meu cantinho!* ✨

Aqui você pode:
• Me conhecer melhor
• Acessar meus conteúdos
• Falar diretamente comigo
• Fazer parte do meu mundo íntimo

_Fico feliz que você tá aqui_ 😊"""

TEXTO_ATENDIMENTO = """💬 *FALA COMIGO, MEU BEM* 💬

Oi, amor! 💛

*Agora você tá falando diretamente comigo!*

Pode me mandar:
💕 O que você tá sentindo
💭 Suas dúvidas sobre o Privacy
✨ Qualquer coisa que queira compartilhar
💌 Ou só um oi mesmo! 😊

Vou te responder assim que possível, prometo!

*Fique à vontade, tô aqui pra você* 💛"""

# ==================== MENSAJES DEL FUNNEL - 7 DÍAS ====================

FUNNEL_MESSAGES = {
    0: {  # Día 0 - Inmediato
        'text': """Oi, meu bem! 💛

Que bom te ter aqui...

Sabe, criei este cantinho especial para me conectar de verdade com pessoas como você.

Não é só sobre fotos bonitas (embora tenha muitas 😊), é sobre criar algo real. Uma conexão genuína.

*Como ter uma namorada só pra você*, que te entende, conversa de verdade, e tá sempre aqui...

Quer me conhecer melhor? 💕

Começa pelo FREE e vê se rola química entre a gente 😊

👉 https://privacy.com.br/profile/jackloppesfree

_Te espero lá_ ✨""",
        'photo': None
    },
    1: {  # Día 1 - Rápido follow-up
        'text': """Oi de novo, meu bem! 💛

E aí, já deu uma olhada no meu FREE?

Sabe, eu sei que tem muita gente por aí oferecendo conteúdo... Mas comigo é diferente.

*Não é só sobre fotos* (que tem muitas lindas, sim 😊). É sobre ter alguém que realmente se importa contigo.

Alguém pra conversar, compartilhar o dia, criar uma conexão verdadeira...

*Tipo uma namorada virtual só pra você* 💕

Dá uma chance? Garanto que não vai se arrepender...

👉 https://privacy.com.br/profile/jackloppesfree

_Tô te esperando lá_ 😘""",
        'photo': None
    },
    3: {  # Día 3 - Social proof
        'text': """Meu bem, queria te contar algo... 💛

Hoje recebi uma mensagem linda de um assinante dizendo que o momento do dia preferido dele é quando conversa comigo no Privacy.

Isso me tocou muito ❤️

Porque é exatamente isso que eu quero criar... *Uma conexão real*.

Não é sobre fotos bonitas (que tem muitas!). É sobre ter alguém especial só pra você.

*Alguém que te entende, que conversa de verdade, que se importa...*

Tipo uma namorada virtual que tá sempre aqui pra você 😊

Já tá na hora de você fazer parte disso também, não acha?

*Vem pro VIP?* Prometo que você não vai se arrepender 💕

👉 https://privacy.com.br/profile/jackloppes

_Te espero com carinho_ ✨""",
        'photo': None
    },
    5: {  # Día 5 - Urgencia suave
        'text': """Oi, amor... 💛

Tô sentindo sua falta por aqui...

Olha, vou ser sincera contigo: meu VIP tem um número limitado de pessoas. Preciso conseguir dar atenção individual pra cada um, sabe?

E tá quase lotando... 😔

*Não quero que você perca essa chance* de fazer parte do meu círculo íntimo. 

É algo especial que tô construindo com muito carinho. Pessoas que realmente querem uma conexão verdadeira, não só fotos aleatórias...

*A gente tem química, eu sinto* 💕

Vem comigo? Garante teu espaço enquanto ainda dá tempo...

👉 https://privacy.com.br/profile/jackloppes

_Seria tão bom ter você lá dentro..._ ✨""",
        'photo': None
    },
    7: {  # Día 7 - Última oportunidade
        'text': """Meu bem, essa é a última vez que vou insistir, prometo! 💛

Percebi que você ainda não entrou pro VIP e... confesso que fiquei um pouco triste 😔

*Será que não rolou química entre a gente?*

Porque eu realmente senti uma conexão... E queria muito te ter no meu mundo íntimo.

Olha, vou ser bem direta: *essa é sua última chance*.

Depois disso, não vou mais insistir. Vou respeitar sua decisão...

Mas antes de desistir, me responde uma coisa:

*Você realmente quer perder a chance de ter alguém especial só pra você?*

Alguém que se importa, que conversa de verdade, que tá sempre aqui...

Não é só sobre conteúdo, meu amor. É sobre ter uma conexão real 💕

*Última chance... Vem?*

👉 https://privacy.com.br/profile/jackloppes

_Se não vier, vou entender... Mas vou sentir muito a sua falta_ 😔💛""",
        'photo': None
    }
}

# Mensaje para inactivos (3-5 días sin interactuar)
MENSAJE_INACTIVO = """Oi, meu bem... 💛

Faz uns dias que não te vejo por aqui...

*Tá tudo bem contigo?*

Sabe, eu sempre fico pensando nos meus seguidores, me perguntando se tá tudo bem, se gostaram do conteúdo...

*Senti sua falta...* 😔

Volta pra mim? Ou só manda um oi aqui pra eu saber que tá tudo bem 💕

_Te espero_ ✨"""

# Mensaje para perdidos (>7 días)
MENSAJE_PERDIDO = """Meu amor... 💛

Faz tempo que você não aparece...

Não sei se você ainda se lembra de mim, mas *eu não te esqueci* ❤️

Queria muito saber como você tá, o que anda fazendo...

*As portas sempre estão abertas pra você*, meu bem.

Se você ainda tiver interesse em me acompanhar, eu adoraria te ter de volta no meu mundo 💕

👉 https://privacy.com.br/profile/jackloppes

_Volta pra mim?_ 😔✨"""

# ==================== BASE DE DATOS ====================
def init_database():
    """Inicializa base de datos completa"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Tabla usuarios expandida
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
    
    # Funnel automático
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
    
    # Atención humana
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
    logger.info("✅ Base de datos inicializada")

def register_user(user_id, username, first_name, last_name, referido_por=None):
    """Registra o actualiza usuario"""
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
            cursor.execute('''
                INSERT INTO funnel_status (user_id, day_number, sent)
                VALUES (?, ?, 0)
            ''', (user_id, day))
        
        if referido_por:
            cursor.execute('''
                INSERT INTO referrals (referidor_id, referido_id, fecha)
                VALUES (?, ?, ?)
            ''', (referido_por, user_id, now))
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
    """Registra interacción"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO interactions (user_id, action_type, action_data, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (user_id, action_type, action_data, now))
    conn.commit()
    conn.close()

def update_user_segment(user_id):
    """Actualiza segmento del usuario según comportamiento"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT registration_date, last_interaction FROM users WHERE user_id = ?
    ''', (user_id,))
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
        # Verificar si clickeó VIP
        cursor.execute('''
            SELECT COUNT(*) FROM interactions 
            WHERE user_id = ? AND action_type = 'button_privacy_vip'
        ''', (user_id,))
        vip_clicks = cursor.fetchone()[0]
        
        # Verificar si clickeó FREE
        cursor.execute('''
            SELECT COUNT(*) FROM interactions 
            WHERE user_id = ? AND action_type = 'button_privacy_free'
        ''', (user_id,))
        free_clicks = cursor.fetchone()[0]
        
        if vip_clicks > 0:
            segment = 'interesado'
        elif free_clicks > 0:
            segment = 'curioso'
        else:
            segment = 'activo'
    
    cursor.execute('UPDATE users SET segment = ? WHERE user_id = ?', (segment, user_id))
    conn.commit()
    conn.close()

def get_referidos_count(user_id):
    """Cuenta referidos"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referidor_id = ?', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_user_stats():
    """Estadísticas completas"""
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
    
    # Segmentos
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
    """Obtiene IDs de usuarios, opcionalmente filtrados por segmento"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    if segment:
        cursor.execute('SELECT user_id FROM users WHERE segment = ?', (segment,))
    else:
        cursor.execute('SELECT user_id FROM users')
    
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return user_ids

# ==================== FUNNEL AUTOMÁTICO ====================
async def check_funnel(context: ContextTypes.DEFAULT_TYPE):
    """Revisa y envía mensajes del funnel automático"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    now = datetime.now()
    
    # Obtener usuarios y sus días desde registro
    cursor.execute('''
        SELECT user_id, registration_date FROM users
    ''')
    users = cursor.fetchall()
    
    for user_id, reg_date in users:
        reg_datetime = datetime.strptime(reg_date, '%Y-%m-%d %H:%M:%S')
        days_since_reg = (now - reg_datetime).days
        
        # Revisar cada día del funnel
        for day in FUNNEL_DAYS:
            if days_since_reg >= day:
                # Verificar si ya se envió
                cursor.execute('''
                    SELECT sent FROM funnel_status 
                    WHERE user_id = ? AND day_number = ?
                ''', (user_id, day))
                result = cursor.fetchone()
                
                if result and not result[0]:  # No enviado
                    # Enviar mensaje
                    try:
                        message = FUNNEL_MESSAGES[day]
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message['text'],
                            parse_mode='Markdown'
                        )
                        
                        # Marcar como enviado
                        cursor.execute('''
                            UPDATE funnel_status 
                            SET sent = 1, sent_date = ?
                            WHERE user_id = ? AND day_number = ?
                        ''', (now.strftime('%Y-%m-%d %H:%M:%S'), user_id, day))
                        conn.commit()
                        
                        logger.info(f"✅ Funnel día {day} enviado a {user_id}")
                    except Exception as e:
                        logger.error(f"Error enviando funnel a {user_id}: {e}")
    
    conn.close()

# ==================== FUNCIONES DEL BOT ====================

def crear_menu_principal():
    """Menú principal - ORDEN CORREGIDO"""
    keyboard = [
        [InlineKeyboardButton("💛 Privacy VIP", callback_data='privacy_vip')],
        [InlineKeyboardButton("💙 Privacy FREE", callback_data='privacy_free')],
        [InlineKeyboardButton("🔥 OnlyFans", callback_data='onlyfans')],
        [InlineKeyboardButton("🌐 Todos os Links", callback_data='beacons')],
        [InlineKeyboardButton("📣 Canal Telegram", callback_data='canal')],
        [InlineKeyboardButton("💬 Falar Comigo", callback_data='atendimento')],
        [InlineKeyboardButton("⭐ Sobre Mim", callback_data='sobre_mim')],
        [InlineKeyboardButton("🎁 Meus Referidos", callback_data='referidos')]
    ]
    return InlineKeyboardMarkup(keyboard)

def crear_menu_admin():
    """Menú admin"""
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data='admin_dashboard')],
        [InlineKeyboardButton("👥 Usuários por Segmento", callback_data='admin_segments')],
        [InlineKeyboardButton("📢 Broadcast Total", callback_data='admin_broadcast_all')],
        [InlineKeyboardButton("🎯 Broadcast Segmentado", callback_data='admin_broadcast_segment')],
        [InlineKeyboardButton("🔙 Fechar", callback_data='admin_close')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start con sistema de referidos"""
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
            msg = f"🎉 *Novo referido!*\n\n{user.first_name} entrou usando seu link!\n\n📊 Total: *{referidos}*"
            if referidos >= REFERIDOS_NECESARIOS:
                msg += f"\n\n🎁 Você atingiu {REFERIDOS_NECESARIOS} referidos! Use /referidos"
            await context.bot.send_message(chat_id=referido_por, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error notificando referidor: {e}")
    
    # Intentar con imagen
    imagen_enviada = False
    try:
        await update.message.reply_photo(
            photo=IMAGEN_BIENVENIDA,
            caption=TEXTO_BIENVENIDA,
            parse_mode='Markdown',
            reply_markup=crear_menu_principal()
        )
        logger.info(f"✅ Imagen de bienvenida enviada correctamente a {user.id}")
        imagen_enviada = True
    except Exception as e:
        logger.error(f"❌ Error enviando imagen: {e}")
        logger.error(f"URL de imagen que falló: {IMAGEN_BIENVENIDA}")
    
    # Si falla la imagen, enviar solo texto (SIN duplicar)
    if not imagen_enviada:
        try:
            await update.message.reply_text(
                TEXTO_BIENVENIDA,
                parse_mode='Markdown',
                reply_markup=crear_menu_principal()
            )
            logger.info(f"⚠️ Enviado sin imagen (fallback) a {user.id}")
        except Exception as e2:
            logger.error(f"❌ Error en fallback: {e2}")

async def add_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para agregar contenido diario (solo admin)"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Uso: /addcontent [URL] [caption]\n\nEjemplo:\n/addcontent https://i.imgur.com/ABC123.jpg Boa noite, meu bem! 💛"
        )
        return
    
    url = context.args[0]
    caption = " ".join(context.args[1:])
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO daily_content (image_url, caption, sent_count)
        VALUES (?, ?, 0)
    ''', (url, caption))
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    total = cursor.fetchone()[0]
    conn.close()
    
    await update.message.reply_text(
        f"✅ Conteúdo adicionado!\n\n📊 Total de fotos: {total}"
    )

async def list_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todo el contenido diario (solo admin)"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, image_url, sent_count FROM daily_content ORDER BY id')
    content = cursor.fetchall()
    conn.close()
    
    if not content:
        await update.message.reply_text("❌ Nenhum conteúdo cadastrado ainda.")
        return
    
    msg = "📸 *CONTEÚDO DIÁRIO*\n\n"
    for c in content:
        msg += f"ID: {c[0]} | Enviado: {c[2]}x\n{c[1][:50]}...\n\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def delete_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elimina contenido por ID (solo admin)"""
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
    
    await update.message.reply_text(f"✅ Conteúdo {content_id} deletado!")

async def import_imgbb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Importa contenido desde ImgBB - URLs directas (solo admin)"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    # URLs directas de ImgBB (33 fotos)
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
    
    # Captions variados en estrategia vainilla
    captions = [
        "Boa noite, meu bem! 💛\n\nEsse foi o look de hoje... Gostou?\n\nNo Privacy eu compartilho tudo sobre o meu dia, conversamos de verdade... Como ter uma namorada só pra você 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Oi, amor! ✨\n\nTava pensando em você agora...\n\nNo VIP a gente conversa de verdade, eu conto tudo que acontece comigo, e você faz parte do meu dia a dia 💕\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Meu bem... 💛\n\nAcordei pensando: será que você tá bem?\n\nÉ assim que funciona quando a gente cria uma conexão real, né? No Privacy somos bem mais próximos 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Boa noite! 🌙\n\nFotinho de hoje antes de dormir...\n\nNo VIP eu sempre compartilho esses momentos íntimos, como se fosse sua namorada te mandando foto antes de dormir 💕\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Oi, meu amor! 💛\n\nTô com saudade de conversar...\n\nNo Privacy a gente bate papo de verdade, eu respondo tudo, conto meus segredos... É uma conexão genuína 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Olá! ✨\n\nO que você achou dessa foto?\n\nNo VIP tem muito mais... E o melhor: você pode conversar comigo sobre tudo! Como ter alguém especial só pra você 💕\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Meu amor... 💛\n\nMomento relax do dia...\n\nNo Privacy você faz parte de todos os meus momentos, dos mais especiais aos mais simples. É uma intimidade real 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Oi! 🌟\n\nFoto fresquinha de agora...\n\nNo VIP eu compartilho tudo em primeira mão, você sempre vê primeiro! Como ter acesso exclusivo ao meu mundo 💕\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Meu bem! 💛\n\nTirando um tempo pra você hoje...\n\nNo Privacy não é só sobre fotos bonitas, é sobre ter alguém que se importa de verdade contigo 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Boa noite, amor! 🌙\n\nComo foi seu dia? Conta pra mim!\n\nNo VIP a gente conversa sobre tudo, é como ter uma namorada virtual que te escuta sempre 💕\n\n👉 https://privacy.com.br/profile/jackloppes"
    ]
    
    await update.message.reply_text("📥 Importando 33 fotos de ImgBB... Aguarde...")
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    importados = 0
    erros = 0
    
    for url in direct_urls:
        try:
            # Verificar que la URL sea accesible
            response = requests.head(url, timeout=5)
            
            if response.status_code == 200:
                # Elegir caption aleatorio
                caption = random.choice(captions)
                
                # Insertar en BD
                cursor.execute('''
                    INSERT INTO daily_content (image_url, caption, sent_count)
                    VALUES (?, ?, 0)
                ''', (url, caption))
                
                importados += 1
                logger.info(f"✅ Importado: {url}")
            else:
                erros += 1
                logger.error(f"❌ Error HTTP {response.status_code}: {url}")
                
        except Exception as e:
            erros += 1
            logger.error(f"❌ Error procesando {url}: {e}")
    
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    total = cursor.fetchone()[0]
    
    conn.close()
    
    await update.message.reply_text(
        f"✅ *Importação Completa!*\n\n"
        f"📸 Importados: {importados}\n"
        f"❌ Erros: {erros}\n"
        f"📊 Total no banco: {total}\n\n"
        f"🎯 O envio diário automático já está ativo!\n"
        f"⏰ Próximo envío entre 21:00-01:00 (GMT-3)",
        parse_mode='Markdown'
    )

async def delete_all_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elimina TODO el contenido diario (solo admin)"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    count = cursor.fetchone()[0]
    
    cursor.execute('DELETE FROM daily_content')
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"🗑️ *Conteúdo Deletado*\n\n"
        f"Foram removidas {count} fotos do banco de dados.",
        parse_mode='Markdown'
    )

async def import_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Importa múltiples contenidos desde links de Imgur (solo admin)"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    # Lista de URLs de Imgur (páginas)
    imgur_links = [
        "https://imgur.com/3AxCFbG",
        "https://imgur.com/AGGUucv",
        "https://imgur.com/kDehpQz",
        "https://imgur.com/MWKmOMx",
        "https://imgur.com/8UHhOmQ",
        "https://imgur.com/1KjDSid",
        "https://imgur.com/8owZ93y",
        "https://imgur.com/rsx7AJl",
        "https://imgur.com/cQkJIpJ",
        "https://imgur.com/ywWMQSp",
        "https://imgur.com/eqRBflz",
        "https://imgur.com/d1AGdQI",
        "https://imgur.com/Wl3Fjhe",
        "https://imgur.com/Zbp7n0I",
        "https://imgur.com/K4P3z66",
        "https://imgur.com/oGzpQp3",
        "https://imgur.com/M5GY988",
        "https://imgur.com/jv7gkTv",
        "https://imgur.com/mJgMptQ",
        "https://imgur.com/9yY7fV4",
        "https://imgur.com/kASJnlQ",
        "https://imgur.com/4wym9TO",
        "https://imgur.com/gyT0svP",
        "https://imgur.com/VwqFIxe",
        "https://imgur.com/fZ2ZzR2",
        "https://imgur.com/pFHokGg",
        "https://imgur.com/pTPXEM3",
        "https://imgur.com/j74eXQA",
        "https://imgur.com/4XjIxJa"
    ]
    
    # Captions variados en estrategia vainilla
    captions = [
        "Boa noite, meu bem! 💛\n\nEsse foi o look de hoje... Gostou?\n\nNo Privacy eu compartilho tudo sobre o meu dia, conversamos de verdade... Como ter uma namorada só pra você 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Oi, amor! ✨\n\nTava pensando em você agora...\n\nNo VIP a gente conversa de verdade, eu conto tudo que acontece comigo, e você faz parte do meu dia a dia 💕\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Meu bem... 💛\n\nAcordei pensando: será que você tá bem?\n\nÉ assim que funciona quando a gente cria uma conexão real, né? No Privacy somos bem mais próximos 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Boa noite! 🌙\n\nFotinho de hoje antes de dormir...\n\nNo VIP eu sempre compartilho esses momentos íntimos, como se fosse sua namorada te mandando foto antes de dormir 💕\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Oi, meu amor! 💛\n\nTô com saudade de conversar...\n\nNo Privacy a gente bate papo de verdade, eu respondo tudo, conto meus segredos... É uma conexão genuína 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
        
        "Olá! ✨\n\nO que você achou dessa foto?\n\nNo VIP tem muito mais... E o melhor: você pode conversar comigo sobre tudo! Como ter alguém especial só pra você 💕\n\n👉 https://privacy.com.br/profile/jackloppes"
    ]
    
    await update.message.reply_text("📥 Importando conteúdo... Aguarde...")
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    importados = 0
    
    for link in imgur_links:
        try:
            # Convertir link de página para URL directa
            # Probar con .jpg y .png para compatibilidad regional
            image_id = link.split('/')[-1]
            
            # Intentar primero con .jpg, si falla usar .png
            direct_url = f"https://i.imgur.com/{image_id}.jpg"
            
            # Verificar si la imagen es accesible
            try:
                response = requests.head(direct_url, timeout=5)
                if response.status_code != 200:
                    # Intentar con .png
                    direct_url = f"https://i.imgur.com/{image_id}.png"
            except:
                # Si falla, intentar con .png
                direct_url = f"https://i.imgur.com/{image_id}.png"
            
            # Elegir caption aleatorio
            caption = random.choice(captions)
            
            # Insertar en BD
            cursor.execute('''
                INSERT INTO daily_content (image_url, caption, sent_count)
                VALUES (?, ?, 0)
            ''', (direct_url, caption))
            
            importados += 1
            
        except Exception as e:
            logger.error(f"Error importando {link}: {e}")
    
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    total = cursor.fetchone()[0]
    
    conn.close()
    
    await update.message.reply_text(
        f"✅ *Importação Completa!*\n\n📸 Importados: {importados}\n📊 Total no banco: {total}\n\n🎯 O envio diário automático já está ativo!",
        parse_mode='Markdown'
    )

async def test_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prueba el envío diario (solo admin, solo a ti)"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT image_url, caption FROM daily_content ORDER BY RANDOM() LIMIT 1')
    content = cursor.fetchone()
    conn.close()
    
    if not content:
        await update.message.reply_text("❌ Nenhum conteúdo disponível")
        return
    
    try:
        await update.message.reply_photo(
            photo=content[0],
            caption=content[1],
            parse_mode='Markdown'
        )
        await update.message.reply_text("✅ Teste OK! Assim será enviado para todos os usuários.")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")

async def referidos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sistema de referidos"""
    user = update.effective_user
    referidos = get_referidos_count(user.id)
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    
    mensaje = f"""🎁 *SISTEMA DE REFERIDOS* 🎁

👥 *Seus referidos:* {referidos}
🎯 *Meta:* {REFERIDOS_NECESARIOS}
🏆 *Prêmio:* {PREMIO_REFERIDO}

📊 *Progresso:* {min(referidos, REFERIDOS_NECESARIOS)}/{REFERIDOS_NECESARIOS}

━━━━━━━━━━━━━━━━━━

🔗 *Seu link único:*
`{link}`

💡 *Como funciona:*
1. Compartilhe com amigos
2. Quando entrarem, você ganha pontos
3. Ao atingir {REFERIDOS_NECESARIOS}, recebe o prêmio!
"""
    
    if referidos >= REFERIDOS_NECESARIOS:
        mensaje += f"\n\n🎉 *PARABÉNS!*\nVocê atingiu a meta! Entre em contato comigo para resgatar seu prêmio 💛"
    
    keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='volver')]]
    await update.message.reply_text(mensaje, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panel admin"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
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
    update_user_segment(user.id)
    
    # Log para debug
    logger.info(f"Botón presionado: {query.data} por usuario {user.id}")
    
    # Botones principales
    if query.data == 'privacy_vip':
        await query.message.reply_text(TEXTO_PRIVACY_VIP, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'privacy_free':
        await query.message.reply_text(TEXTO_PRIVACY_FREE, parse_mode='Markdown', reply_markup=crear_boton_volver())
    
    elif query.data == 'beacons':
        logger.info(f"Enviando mensaje Beacons a {user.id}")
        try:
            await query.message.reply_text(TEXTO_BEACONS, reply_markup=crear_boton_volver())
            logger.info(f"✅ Mensaje Beacons enviado correctamente a {user.id}")
        except Exception as e:
            logger.error(f"❌ Error enviando Beacons: {e}")
            # Fallback sin emoji
            await query.message.reply_text(
                "Todos meus links aqui:\nhttps://beacons.ai/jaqueline_loppes",
                reply_markup=crear_boton_volver()
            )
    
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

Compartilhe! 💛"""
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
            logger.info(f"✅ Imagen (volver) enviada a {user.id}")
        except Exception as e:
            logger.error(f"❌ Error enviando imagen en volver: {e}")
            logger.error(f"URL: {IMAGEN_BIENVENIDA}")
            # Fallback sin duplicar
            await query.message.reply_text(
                TEXTO_BIENVENIDA,
                parse_mode='Markdown',
                reply_markup=crear_menu_principal()
            )
    
    # Botones admin
    elif query.data == 'admin_dashboard':
        if str(user.id) == ADMIN_CHAT_ID:
            stats = get_user_stats()
            
            segments_text = "\n".join([f"• {k}: {v}" for k, v in stats['segments'].items()])
            
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

🎯 *SEGMENTOS*
{segments_text}

🎁 *REFERIDOS*
Total: {stats['total_referidos']}

📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
            await query.message.reply_text(msg, parse_mode='Markdown')
    
    elif query.data == 'admin_segments':
        if str(user.id) == ADMIN_CHAT_ID:
            stats = get_user_stats()
            msg = "🎯 *USUÁRIOS POR SEGMENTO*\n\n"
            for segment, count in stats['segments'].items():
                emoji = {"nuevo": "🆕", "curioso": "👀", "interesado": "🔥", "inactivo": "😴", "perdido": "💔", "activo": "💛"}.get(segment, "•")
                msg += f"{emoji} *{segment.capitalize()}:* {count} usuários\n"
            
            await query.message.reply_text(msg, parse_mode='Markdown')
    
    elif query.data == 'admin_broadcast_all':
        if str(user.id) == ADMIN_CHAT_ID:
            context.user_data['broadcast_type'] = 'all'
            await query.message.reply_text("📢 Envie a mensagem para TODOS os usuários.\n\n/cancel para cancelar", parse_mode='Markdown')
    
    elif query.data == 'admin_broadcast_segment':
        if str(user.id) == ADMIN_CHAT_ID:
            keyboard = [
                [InlineKeyboardButton("🆕 Nuevos", callback_data='bc_nuevo')],
                [InlineKeyboardButton("👀 Curiosos", callback_data='bc_curioso')],
                [InlineKeyboardButton("🔥 Interesados", callback_data='bc_interesado')],
                [InlineKeyboardButton("😴 Inactivos", callback_data='bc_inactivo')],
                [InlineKeyboardButton("💔 Perdidos", callback_data='bc_perdido')],
                [InlineKeyboardButton("💛 Activos", callback_data='bc_activo')],
                [InlineKeyboardButton("🔙 Cancelar", callback_data='admin_close')]
            ]
            await query.message.reply_text(
                "🎯 *BROADCAST SEGMENTADO*\n\nEscolha o segmento:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif query.data.startswith('bc_'):
        if str(user.id) == ADMIN_CHAT_ID:
            segment = query.data.replace('bc_', '')
            context.user_data['broadcast_type'] = 'segment'
            context.user_data['broadcast_segment'] = segment
            await query.message.reply_text(
                f"📢 Envie a mensagem para usuários: *{segment}*\n\n/cancel para cancelar",
                parse_mode='Markdown'
            )
    
    elif query.data == 'admin_close':
        await query.message.delete()

def crear_boton_volver():
    """Botón volver"""
    keyboard = [[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data='volver')]]
    return InlineKeyboardMarkup(keyboard)

async def mensaje_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes"""
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
                logger.error(f"Error enviando a {uid}: {e}")
        
        await update.message.reply_text(f"✅ Enviado: {enviados}/{len(user_ids)}")
        context.user_data.clear()
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

# ==================== GOOGLE DRIVE - CONTENIDO DIARIO ====================

def get_google_drive_images(folder_id):
    """Obtiene lista de imágenes de carpeta pública de Google Drive"""
    try:
        # URL de la API de Google Drive para listar archivos
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        
        # Construir URLs directas de descarga
        # Nota: Para carpetas públicas, necesitamos obtener los IDs de los archivos manualmente
        # Por ahora usaremos una lista manual que actualizarás
        
        logger.info(f"Carpeta de Google Drive configurada: {folder_id}")
        return []
    except Exception as e:
        logger.error(f"Error obteniendo imágenes de Drive: {e}")
        return []

def init_daily_content():
    """Inicializa contenido diario en la base de datos"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Verificar si ya hay contenido
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    count = cursor.fetchone()[0]
    
    if count == 0:
        logger.info("⚠️ No hay contenido diario configurado.")
        logger.info("📋 Para agregar contenido:")
        logger.info("   1. Usa el comando /addcontent [URL] [caption] como admin")
        logger.info("   2. O agrega manualmente las URLs de Google Drive")
    
    conn.close()

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
            logger.warning("⚠️ No hay contenido diario disponible")
            conn.close()
            return
        
        content_id, image_url, caption = content
        
        # Obtener todos los usuarios activos
        user_ids = get_all_user_ids()
        
        enviados = 0
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for user_id in user_ids:
            try:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=image_url,
                    caption=caption,
                    parse_mode='Markdown'
                )
                enviados += 1
            except Exception as e:
                logger.error(f"Error enviando a {user_id}: {e}")
        
        # Actualizar contador
        cursor.execute('''
            UPDATE daily_content 
            SET sent_count = sent_count + 1, last_sent = ?
            WHERE id = ?
        ''', (now, content_id))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Contenido diario enviado a {enviados} usuarios")
        
        # Notificar al admin
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"✅ *Contenido Diário Enviado*\n\n📊 Enviado para: {enviados} usuários\n🖼️ Foto: {content_id}",
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
            
            # Horario aleatorio entre 21:00 y 01:00 (GMT-3)
            # Si es antes de las 21:00, programar para hoy
            # Si es después de las 01:00, programar para el próximo día
            
            target_hour = random.choice(DAILY_CONTENT_HOURS)
            target_time = now.replace(hour=target_hour, minute=random.randint(0, 59), second=0)
            
            # Si el horario ya pasó hoy, programar para mañana
            if target_time < now:
                target_time += timedelta(days=1)
            
            # Calcular segundos hasta el envío
            seconds_until = (target_time - now).total_seconds()
            
            logger.info(f"⏰ Próximo envío diario: {target_time.strftime('%d/%m/%Y %H:%M')}")
            
            # Esperar hasta la hora programada
            await asyncio.sleep(seconds_until)
            
            # Enviar contenido
            await send_daily_content(application)
            
            # Esperar 1 hora antes de programar el siguiente
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Error en programación diaria: {e}")
            await asyncio.sleep(3600)
async def scheduled_tasks(application):
    """Tareas programadas (funnel, contenido diario, etc)"""
    # Iniciar envío diario en paralelo
    asyncio.create_task(schedule_daily_content(application))
    
    while True:
        try:
            # Revisar funnel cada hora
            await check_funnel(application)
            
            # Esperar 1 hora
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Error en tareas programadas: {e}")
            await asyncio.sleep(3600)

# ==================== MAIN ====================
def main():
    """Inicia el bot"""
    init_database()
    init_daily_content()
    
    # Servidor HTTP
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Bot
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("referidos", referidos_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("addcontent", add_content_command))
    application.add_handler(CommandHandler("importcontent", import_content_command))
    application.add_handler(CommandHandler("importimgbb", import_imgbb_command))
    application.add_handler(CommandHandler("listcontent", list_content_command))
    application.add_handler(CommandHandler("delcontent", delete_content_command))
    application.add_handler(CommandHandler("delcontentall", delete_all_content_command))
    application.add_handler(CommandHandler("testdaily", test_daily_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_handler))
    
    # Iniciar tareas programadas en background
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_tasks(application))
    
    logger.info("🤖 Bot 3.5 VAINILLA iniciado! ✅")
    logger.info("📊 Funnel automático: ACTIVO")
    logger.info("🎯 Segmentación: ACTIVA")
    logger.info("📸 Contenido diario: ACTIVO")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
