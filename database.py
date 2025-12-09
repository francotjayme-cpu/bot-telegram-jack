"""
DATABASE MANAGER - BOT TELEGRAM JACK LOPPES
===========================================
Versión Supabase - Base de datos permanente
CORREGIDO: Agregado flag de migración y diagnóstico
"""

import os
import psycopg2
from psycopg2 import pool
import logging
from datetime import datetime, timedelta
import csv

logger = logging.getLogger(__name__)

# URL de Supabase (PERMANENTE - no expira)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Francotomasjayme610600%21@db.myjntjxmewkolndqlwgv.supabase.co:5432/postgres"
)

# Pool de conexiones
connection_pool = None

def get_connection():
    """Obtiene una conexión del pool"""
    global connection_pool
    try:
        if connection_pool is None:
            connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)
        return connection_pool.getconn()
    except Exception as e:
        logger.error(f"Error conectando a BD: {e}")
        # Intentar reconectar
        connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)
        return connection_pool.getconn()

def release_connection(conn):
    """Devuelve la conexión al pool"""
    global connection_pool
    if connection_pool and conn:
        try:
            connection_pool.putconn(conn)
        except:
            pass

# ==================== INICIALIZACIÓN ====================

def init_database():
    """Inicializa la base de datos con todas las tablas"""
    conn = get_connection()
    cursor = conn.cursor()

    # Usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registration_date TEXT,
            last_interaction TEXT,
            total_interactions INTEGER DEFAULT 0,
            referido_por BIGINT DEFAULT NULL,
            puntos_referido INTEGER DEFAULT 0,
            segment TEXT DEFAULT 'nuevo'
        )
    ''')

    # Interacciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            action_type TEXT,
            action_data TEXT,
            timestamp TEXT
        )
    ''')

    # Referidos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id SERIAL PRIMARY KEY,
            referidor_id BIGINT,
            referido_id BIGINT,
            fecha TEXT,
            recompensa_reclamada INTEGER DEFAULT 0
        )
    ''')

    # Funnel
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funnel_status (
            user_id BIGINT,
            day_number INTEGER,
            sent INTEGER DEFAULT 0,
            sent_date TEXT,
            PRIMARY KEY (user_id, day_number)
        )
    ''')

    # Contenido diario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_content (
            id SERIAL PRIMARY KEY,
            image_url TEXT,
            caption TEXT,
            sent_count INTEGER DEFAULT 0,
            last_sent TEXT
        )
    ''')

    # NUEVA TABLA: Configuración del bot (para flags)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    ''')

    conn.commit()
    release_connection(conn)
    logger.info("✅ Base de datos Supabase inicializada correctamente")

# ==================== GESTIÓN DE USUARIOS ====================

def register_user(user_id, username, first_name, last_name, referido_por=None, funnel_days=None):
    """Registra o actualiza un usuario"""
    if funnel_days is None:
        funnel_days = [0, 1, 3, 5, 7]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT user_id FROM users WHERE user_id = %s', (user_id,))
    exists = cursor.fetchone()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not exists:
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, registration_date, last_interaction, total_interactions, referido_por, segment)
            VALUES (%s, %s, %s, %s, %s, %s, 1, %s, 'nuevo')
        ''', (user_id, username, first_name, last_name, now, now, referido_por))

        # Inicializar funnel
        for day in funnel_days:
            cursor.execute('INSERT INTO funnel_status (user_id, day_number, sent) VALUES (%s, %s, 0)', (user_id, day))

        # Registrar referido
        if referido_por:
            cursor.execute('INSERT INTO referrals (referidor_id, referido_id, fecha) VALUES (%s, %s, %s)',
                         (referido_por, user_id, now))
            cursor.execute('UPDATE users SET puntos_referido = puntos_referido + 1 WHERE user_id = %s', (referido_por,))

        # LOG IMPORTANTE: Confirmar que se guardó
        logger.info(f"✅ NUEVO USUARIO GUARDADO EN SUPABASE: {first_name} ({user_id})")
    else:
        cursor.execute('''
            UPDATE users
            SET last_interaction = %s, total_interactions = total_interactions + 1,
                username = %s, first_name = %s, last_name = %s
            WHERE user_id = %s
        ''', (now, username, first_name, last_name, user_id))

    conn.commit()
    release_connection(conn)

def log_interaction(user_id, action_type, action_data=""):
    """Registra una interacción del usuario"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO interactions (user_id, action_type, action_data, timestamp) VALUES (%s, %s, %s, %s)',
                  (user_id, action_type, action_data, now))
    conn.commit()
    release_connection(conn)

def update_user_segment(user_id, inactive_days=3, lost_days=7):
    """Actualiza el segmento del usuario según comportamiento"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT registration_date, last_interaction FROM users WHERE user_id = %s', (user_id,))
    result = cursor.fetchone()

    if not result:
        release_connection(conn)
        return

    try:
        reg_date = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
        last_int = datetime.strptime(result[1], '%Y-%m-%d %H:%M:%S')
    except:
        release_connection(conn)
        return

    now = datetime.now()
    days_since_reg = (now - reg_date).days
    days_since_int = (now - last_int).days

    if days_since_int > lost_days:
        segment = 'perdido'
    elif days_since_int > inactive_days:
        segment = 'inactivo'
    elif days_since_reg <= 3:
        segment = 'nuevo'
    else:
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id = %s AND action_type = %s',
                      (user_id, 'button_privacy_vip'))
        vip_clicks = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id = %s AND action_type = %s',
                      (user_id, 'button_privacy_free'))
        free_clicks = cursor.fetchone()[0]

        segment = 'interesado' if vip_clicks > 0 else ('curioso' if free_clicks > 0 else 'activo')

    cursor.execute('UPDATE users SET segment = %s WHERE user_id = %s', (segment, user_id))
    conn.commit()
    release_connection(conn)

# ==================== CONSULTAS ====================

def get_referidos_count(user_id):
    """Cuenta referidos de un usuario"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referidor_id = %s', (user_id,))
    count = cursor.fetchone()[0]
    release_connection(conn)
    return count

def get_user_stats():
    """Estadísticas completas del bot"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM users WHERE registration_date LIKE %s', (f'{today}%',))
    users_today = cursor.fetchone()[0]

    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM users WHERE registration_date >= %s', (week_ago,))
    users_week = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users WHERE last_interaction >= %s', (week_ago,))
    activos_week = cursor.fetchone()[0]

    cursor.execute('''
        SELECT action_type, COUNT(*) as count
        FROM interactions
        GROUP BY action_type
        ORDER BY count DESC
        LIMIT 1
    ''')
    popular = cursor.fetchone()
    popular_action = popular[0] if popular else 'N/A'
    popular_count = popular[1] if popular else 0

    cursor.execute('SELECT COUNT(*) FROM interactions')
    total_interactions = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM referrals')
    total_referidos = cursor.fetchone()[0]

    cursor.execute('SELECT segment, COUNT(*) FROM users GROUP BY segment')
    segments = dict(cursor.fetchall())

    engagement = (activos_week / total_users * 100) if total_users > 0 else 0

    release_connection(conn)

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
    conn = get_connection()
    cursor = conn.cursor()

    if segment:
        cursor.execute('SELECT user_id FROM users WHERE segment = %s', (segment,))
    else:
        cursor.execute('SELECT user_id FROM users')

    user_ids = [row[0] for row in cursor.fetchall()]
    release_connection(conn)
    return user_ids

def get_all_users_data():
    """Obtiene todos los datos de usuarios para exportar"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id, username, first_name, last_name,
               registration_date, last_interaction, total_interactions,
               puntos_referido, segment
        FROM users
        ORDER BY registration_date DESC
    ''')

    users = cursor.fetchall()
    release_connection(conn)
    return users

def export_contacts_to_csv(filename='contacts_export.csv'):
    """Exporta todos los contactos a un archivo CSV"""
    users = get_all_users_data()

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'User ID', 'Username', 'Nombre', 'Apellido',
            'Fecha Registro', 'Última Interacción', 'Total Interacciones',
            'Puntos Referido', 'Segmento'
        ])
        for user in users:
            writer.writerow(user)

    logger.info(f"✅ Contactos exportados a {filename}")
    return filename, len(users)

# ==================== CONTENIDO DIARIO ====================

def get_daily_content():
    """Obtiene contenido diario menos usado"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, image_url, caption FROM daily_content
        ORDER BY sent_count ASC, last_sent ASC NULLS FIRST
        LIMIT 1
    ''')
    content = cursor.fetchone()
    release_connection(conn)
    return content

def update_content_sent(content_id):
    """Actualiza contador de envíos de contenido"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('UPDATE daily_content SET sent_count = sent_count + 1, last_sent = %s WHERE id = %s',
                  (now, content_id))
    conn.commit()
    release_connection(conn)

def add_daily_content(image_url, caption):
    """Agrega contenido diario"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO daily_content (image_url, caption, sent_count) VALUES (%s, %s, 0)',
                  (image_url, caption))
    conn.commit()

    cursor.execute('SELECT COUNT(*) FROM daily_content')
    total = cursor.fetchone()[0]
    release_connection(conn)
    return total

def get_content_count():
    """Obtiene cantidad de contenido disponible"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    count = cursor.fetchone()[0]
    release_connection(conn)
    return count

def get_random_content():
    """Obtiene contenido aleatorio para pruebas"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT image_url, caption FROM daily_content ORDER BY RANDOM() LIMIT 1')
    content = cursor.fetchone()
    release_connection(conn)
    return content

def list_content(limit=10):
    """Lista contenido diario"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, sent_count FROM daily_content ORDER BY id LIMIT %s', (limit,))
    content = cursor.fetchall()
    release_connection(conn)
    return content

def delete_content(content_id):
    """Elimina contenido por ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM daily_content WHERE id = %s', (content_id,))
    conn.commit()
    release_connection(conn)

def delete_all_content():
    """Elimina todo el contenido"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM daily_content')
    count = cursor.fetchone()[0]
    cursor.execute('DELETE FROM daily_content')
    conn.commit()
    release_connection(conn)
    return count

# ==================== FUNNEL ====================

def get_users_for_funnel(funnel_days=None):
    """Obtiene usuarios que necesitan recibir mensajes del funnel"""
    if funnel_days is None:
        funnel_days = [0, 1, 3, 5, 7]

    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now()
    cursor.execute('SELECT user_id, registration_date FROM users')
    users = cursor.fetchall()

    pending_funnel = []

    for user_id, reg_date in users:
        try:
            reg_datetime = datetime.strptime(reg_date, '%Y-%m-%d %H:%M:%S')
            days_since_reg = (now - reg_datetime).days

            for day in funnel_days:
                if days_since_reg >= day:
                    cursor.execute('SELECT sent FROM funnel_status WHERE user_id = %s AND day_number = %s',
                                 (user_id, day))
                    result = cursor.fetchone()

                    if result and not result[0]:
                        pending_funnel.append((user_id, day))
        except:
            continue

    release_connection(conn)
    return pending_funnel

def mark_funnel_sent(user_id, day_number):
    """Marca un mensaje del funnel como enviado"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('UPDATE funnel_status SET sent = 1, sent_date = %s WHERE user_id = %s AND day_number = %s',
                  (now, user_id, day_number))
    conn.commit()
    release_connection(conn)

# ==================== FLAGS DE CONFIGURACIÓN (NUEVO) ====================

def get_config(key, default=None):
    """Obtiene un valor de configuración de la BD"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM bot_config WHERE key = %s', (key,))
        result = cursor.fetchone()
        release_connection(conn)
        return result[0] if result else default
    except Exception as e:
        logger.error(f"Error obteniendo config {key}: {e}")
        return default

def set_config(key, value):
    """Guarda un valor de configuración en la BD"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO bot_config (key, value, updated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = %s
        ''', (key, value, now, value, now))
        
        conn.commit()
        release_connection(conn)
        return True
    except Exception as e:
        logger.error(f"Error guardando config {key}: {e}")
        return False

def check_initial_migration_done():
    """Verifica si ya se hizo la migración inicial de contacts_data.py"""
    return get_config('initial_migration_done') == 'true'

def mark_initial_migration_done():
    """Marca que la migración inicial ya se completó"""
    set_config('initial_migration_done', 'true')
    logger.info("✅ Migración inicial marcada como completada")

# ==================== IMPORTACIÓN ====================

def import_old_contacts(contact_ids, funnel_days=None):
    """Importa contactos antiguos masivamente"""
    if funnel_days is None:
        funnel_days = [0, 1, 3, 5, 7]

    conn = get_connection()
    cursor = conn.cursor()

    importados = 0
    ya_existian = 0
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for user_id in contact_ids:
        try:
            cursor.execute('SELECT user_id FROM users WHERE user_id = %s', (user_id,))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, registration_date, last_interaction, total_interactions, segment)
                    VALUES (%s, %s, %s, %s, %s, %s, 0, 'recuperado')
                ''', (user_id, None, f"User_{user_id}", None, now, now))

                for day in funnel_days:
                    cursor.execute('INSERT INTO funnel_status (user_id, day_number, sent) VALUES (%s, %s, 0)',
                                 (user_id, day))

                importados += 1
            else:
                ya_existian += 1

        except Exception as e:
            logger.error(f"Error importando {user_id}: {e}")

    conn.commit()

    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    release_connection(conn)

    return importados, ya_existian, total

# ==================== DIAGNÓSTICO (NUEVO) ====================

def get_database_info():
    """Obtiene información de diagnóstico de la BD"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Total usuarios
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        # Usuarios de hoy
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT COUNT(*) FROM users WHERE registration_date LIKE %s', (f'{today}%',))
        users_today = cursor.fetchone()[0]
        
        # Último usuario registrado
        cursor.execute('SELECT first_name, registration_date FROM users ORDER BY registration_date DESC LIMIT 1')
        last_user = cursor.fetchone()
        
        # Verificar flag de migración
        cursor.execute('SELECT value FROM bot_config WHERE key = %s', ('initial_migration_done',))
        migration_result = cursor.fetchone()
        migration_done = migration_result[0] if migration_result else 'no'
        
        release_connection(conn)
        
        return {
            'total_users': total_users,
            'users_today': users_today,
            'last_user': last_user,
            'migration_done': migration_done,
            'db_type': 'Supabase' if 'supabase' in DATABASE_URL.lower() else 'PostgreSQL',
            'connected': True
        }
    except Exception as e:
        logger.error(f"Error en diagnóstico: {e}")
        return {
            'total_users': 0,
            'users_today': 0,
            'last_user': None,
            'migration_done': 'unknown',
            'db_type': 'Error',
            'connected': False,
            'error': str(e)
        }
