"""
BOT DE TELEGRAM - JACK LOPPES
Estrategia Vainilla - Novia Virtual
Versión Optimizada y Limpia
"""

import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import random
import asyncio
import requests

# Importar funciones de base de datos
from database import (
    init_database, register_user, log_interaction, update_user_segment,
    get_referidos_count, get_user_stats, get_all_user_ids, export_contacts_to_csv,
    get_daily_content, update_content_sent, add_daily_content, get_content_count,
    get_random_content, get_users_for_funnel, mark_funnel_sent, import_old_contacts,
    list_content, delete_content, delete_all_content
)

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
# Todas las funciones de BD ahora están en database.py

# ==================== FUNCIONES DE CONTENIDO ====================

def init_daily_content():
    """Inicializa sistema de contenido diario"""
    count = get_content_count()

    if count == 0:
        logger.info("⚠️ No hay contenido diario. Usa /importcontent para agregar fotos.")
    else:
        logger.info(f"✅ Contenido diario: {count} fotos disponibles")

async def send_daily_content(context: ContextTypes.DEFAULT_TYPE):
    """Envía contenido diario a todos los usuarios"""
    try:
        content = get_daily_content()

        if not content:
            logger.warning("⚠️ No hay contenido disponible")
            return

        content_id, image_url, caption = content
        user_ids = get_all_user_ids()

        enviados = 0

        for user_id in user_ids:
            try:
                await context.bot.send_photo(chat_id=user_id, photo=image_url, caption=caption)
                enviados += 1
            except Exception as e:
                logger.error(f"Error enviando a {user_id}: {e}")

        # Actualizar contador
        update_content_sent(content_id)

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
    pending_funnel = get_users_for_funnel(FUNNEL_DAYS)

    for user_id, day in pending_funnel:
        try:
            from config import FUNNEL_MESSAGES
            message = FUNNEL_MESSAGES[day]
            await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')

            mark_funnel_sent(user_id, day)
            logger.info(f"✅ Funnel día {day} enviado a {user_id}")
        except Exception as e:
            logger.error(f"Error enviando funnel a {user_id}: {e}")

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

    total = add_daily_content(url, caption)

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

    importados = 0
    for url in direct_urls:
        try:
            caption = random.choice(DAILY_CAPTIONS)
            add_daily_content(url, caption)
            importados += 1
        except Exception as e:
            logger.error(f"Error: {e}")

    total = get_content_count()

    await update.message.reply_text(f"✅ Importado!\n\n📸 Importados: {importados}\n📊 Total: {total}")

async def list_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista contenido"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return

    content = list_content(10)

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
    delete_content(content_id)

    await update.message.reply_text(f"✅ Deletado: {content_id}")

async def delete_all_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elimina TODO el contenido"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return

    count = delete_all_content()

    await update.message.reply_text(f"🗑️ Deletados: {count} itens")

# ==================== BACKUP AUTOMÁTICO ====================

async def backup_database(context: ContextTypes.DEFAULT_TYPE):
    """Hace backup de la BD (exporta a CSV) y la envía al admin"""
    try:
        # Exportar a CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'backup_contacts_{timestamp}.csv'

        filename, total = export_contacts_to_csv(backup_name)

        # Enviar al admin
        with open(backup_name, 'rb') as f:
            await context.bot.send_document(
                chat_id=ADMIN_CHAT_ID,
                document=f,
                filename=backup_name,
                caption=f"📦 *Backup Automático*\n\n📊 Contactos: {total}\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n✅ Base de datos PostgreSQL exportada!",
                parse_mode='Markdown'
            )

        # Eliminar archivo local
        os.remove(backup_name)

        logger.info(f"✅ Backup enviado: {backup_name} ({total} contactos)")

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
    """Importa contactos desde contacts_data.py"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return

    # Importar desde archivo separado
    from contacts_data import OLD_CONTACTS

    await update.message.reply_text(f"📥 Importando {len(OLD_CONTACTS)} contactos... Aguarde...")

    importados, ya_existian, total = import_old_contacts(OLD_CONTACTS, FUNNEL_DAYS)

    msg = f"""✅ *IMPORTACIÓN COMPLETA*

📊 *Resultados:*
• Importados: {importados}
• Ya existían: {ya_existian}
• Total en BD: {total}

🎯 Los contactos recuperados recibirán el funnel desde día 0!

💡 Para actualizar contactos, editá el archivo contacts_data.py"""

    await update.message.reply_text(msg, parse_mode='Markdown')
    logger.info(f"✅ Importados {importados} contactos del bot anterior")

async def test_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prueba envío diario (solo al admin)"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return

    content = get_random_content()

    if not content:
        await update.message.reply_text("❌ Sem conteúdo")
        return

    try:
        await update.message.reply_photo(photo=content[0], caption=content[1])
        await update.message.reply_text("✅ Teste OK!")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")

async def send_daily_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispara envío diario manual COMPLETO a todos los usuarios"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return

    await update.message.reply_text("🚀 Iniciando envio diário manual para TODOS os usuários...")

    # Reutiliza la función send_daily_content
    try:
        await send_daily_content(context)
        await update.message.reply_text("✅ Envio diário completo!")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")
        logger.error(f"Error en envío manual: {e}")

async def export_contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exporta todos los contactos a CSV"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return

    await update.message.reply_text("📊 Exportando contactos...")

    try:
        filename, total = export_contacts_to_csv()

        with open(filename, 'rb') as csv_file:
            await context.bot.send_document(
                chat_id=ADMIN_CHAT_ID,
                document=csv_file,
                filename=filename,
                caption=f"✅ *Exportación Completa*\n\n📊 Total: {total} contactos\n\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                parse_mode='Markdown'
            )

        # Eliminar archivo local
        import os
        os.remove(filename)

        logger.info(f"✅ Contactos exportados: {total}")

    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")
        logger.error(f"Error exportando contactos: {e}")

async def backup_manual_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hace backup manual de la BD"""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return

    await update.message.reply_text("📦 Creando backup...")

    try:
        await backup_database(context)
        await update.message.reply_text("✅ Backup enviado!")
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
    """Tareas programadas: funnel, contenido y backups"""
    # Iniciar envío diario
    asyncio.create_task(schedule_daily_content(application))

    # Iniciar backups automáticos cada 6 horas
    asyncio.create_task(schedule_backups(application))

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
    application.add_handler(CommandHandler("senddaily", send_daily_now_command))
    application.add_handler(CommandHandler("exportcontacts", export_contacts_command))
    application.add_handler(CommandHandler("backup", backup_manual_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_handler))
    
    # Tareas automáticas
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_tasks(application))
    
    logger.info("✅ Bot iniciado!")
    logger.info("📊 Funnel automático: ACTIVO")
    logger.info("🎯 Segmentación: ACTIVA")
    logger.info("📸 Contenido diario: ACTIVO")
    logger.info("💾 Backups automáticos (cada 6h): ACTIVO")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
