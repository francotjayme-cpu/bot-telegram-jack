"""
DATABASE MANAGER - BOT TELEGRAM JACK LOPPES
===========================================
Todas las funciones de base de datos centralizadas
"""

import sqlite3
import logging
from datetime import datetime, timedelta
import csv

logger = logging.getLogger(__name__)

# ==================== INICIALIZACIÓN ====================

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

# ==================== GESTIÓN DE USUARIOS ====================

def register_user(user_id, username, first_name, last_name, referido_por=None, funnel_days=None):
    """Registra o actualiza un usuario"""
    if funnel_days is None:
        funnel_days = [0, 1, 3, 5, 7]

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
        for day in funnel_days:
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

def update_user_segment(user_id, inactive_days=3, lost_days=7):
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
    if days_since_int > lost_days:
        segment = 'perdido'
    elif days_since_int > inactive_days:
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

# ==================== CONSULTAS ====================

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

def get_all_users_data():
    """Obtiene todos los datos de usuarios para exportar"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id, username, first_name, last_name,
               registration_date, last_interaction, total_interactions,
               puntos_referido, segment
        FROM users
        ORDER BY registration_date DESC
    ''')

    users = cursor.fetchall()
    conn.close()
    return users

def export_contacts_to_csv(filename='contacts_export.csv'):
    """Exporta todos los contactos a un archivo CSV"""
    users = get_all_users_data()

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        # Encabezados
        writer.writerow([
            'User ID', 'Username', 'Nombre', 'Apellido',
            'Fecha Registro', 'Última Interacción', 'Total Interacciones',
            'Puntos Referido', 'Segmento'
        ])

        # Datos
        for user in users:
            writer.writerow(user)

    logger.info(f"✅ Contactos exportados a {filename}")
    return filename, len(users)

# ==================== CONTENIDO DIARIO ====================

def get_daily_content():
    """Obtiene contenido diario menos usado"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, image_url, caption FROM daily_content
        ORDER BY sent_count ASC, last_sent ASC
        LIMIT 1
    ''')
    content = cursor.fetchone()
    conn.close()

    return content

def update_content_sent(content_id):
    """Actualiza contador de envíos de contenido"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('UPDATE daily_content SET sent_count = sent_count + 1, last_sent = ? WHERE id = ?',
                  (now, content_id))
    conn.commit()
    conn.close()

def add_daily_content(image_url, caption):
    """Agrega contenido diario"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO daily_content (image_url, caption, sent_count) VALUES (?, ?, 0)',
                  (image_url, caption))
    conn.commit()

    cursor.execute('SELECT COUNT(*) FROM daily_content')
    total = cursor.fetchone()[0]
    conn.close()

    return total

def get_content_count():
    """Obtiene cantidad de contenido disponible"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_random_content():
    """Obtiene contenido aleatorio para pruebas"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT image_url, caption FROM daily_content ORDER BY RANDOM() LIMIT 1')
    content = cursor.fetchone()
    conn.close()
    return content

# ==================== FUNNEL ====================

def get_users_for_funnel(funnel_days=None):
    """Obtiene usuarios que necesitan recibir mensajes del funnel"""
    if funnel_days is None:
        funnel_days = [0, 1, 3, 5, 7]

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    now = datetime.now()
    cursor.execute('SELECT user_id, registration_date FROM users')
    users = cursor.fetchall()

    pending_funnel = []

    for user_id, reg_date in users:
        reg_datetime = datetime.strptime(reg_date, '%Y-%m-%d %H:%M:%S')
        days_since_reg = (now - reg_datetime).days

        for day in funnel_days:
            if days_since_reg >= day:
                cursor.execute('SELECT sent FROM funnel_status WHERE user_id = ? AND day_number = ?',
                             (user_id, day))
                result = cursor.fetchone()

                if result and not result[0]:
                    pending_funnel.append((user_id, day))

    conn.close()
    return pending_funnel

def mark_funnel_sent(user_id, day_number):
    """Marca un mensaje del funnel como enviado"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('UPDATE funnel_status SET sent = 1, sent_date = ? WHERE user_id = ? AND day_number = ?',
                  (now, user_id, day_number))
    conn.commit()
    conn.close()

# ==================== IMPORTACIÓN ====================

def import_old_contacts(contact_ids, funnel_days=None):
    """Importa contactos antiguos masivamente"""
    if funnel_days is None:
        funnel_days = [0, 1, 3, 5, 7]

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    importados = 0
    ya_existian = 0
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for user_id in contact_ids:
        try:
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, registration_date, last_interaction, total_interactions, segment)
                    VALUES (?, ?, ?, ?, ?, ?, 0, 'recuperado')
                ''', (user_id, None, f"User_{user_id}", None, now, now))

                for day in funnel_days:
                    cursor.execute('INSERT INTO funnel_status (user_id, day_number, sent) VALUES (?, ?, 0)',
                                 (user_id, day))

                importados += 1
            else:
                ya_existian += 1

        except Exception as e:
            logger.error(f"Error importando {user_id}: {e}")

    conn.commit()

    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    conn.close()

    return importados, ya_existian, total
