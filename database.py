import sqlite3
from datetime import datetime


DB_NAME = "safeai.db"


def connect():
    return sqlite3.connect(DB_NAME)



def create_tables():

    conn = connect()
    cursor = conn.cursor()


    # пользователи
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        trusted_contact TEXT,
        last_active_at TEXT
    )
    """)

    cursor.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in cursor.fetchall()]

    if "last_active_at" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_active_at TEXT")


    # события SOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_type TEXT,
        level TEXT,
        score INTEGER,
        created_at TEXT
    )
    """)


    # сообщения
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        text TEXT,
        created_at TEXT
    )
    """)


    # доверенные контакты
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trusted_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER,
        contact_id INTEGER,
        contact_name TEXT,
        created_at TEXT
    )
    """)

    # Долговременная персональная память. Она изолирована по user_id и не
    # используется для других пользователей.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, category, value)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        voice_auto_reply INTEGER NOT NULL DEFAULT 1,
        preferred_voice TEXT
    )
    """)

    cursor.execute("PRAGMA table_info(user_settings)")
    settings_columns = [column[1] for column in cursor.fetchall()]
    if "preferred_voice" not in settings_columns:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN preferred_voice TEXT")


    conn.commit()
    conn.close()



def add_user(user_id, username, first_name):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users
    (id, username, first_name, last_active_at)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        username=excluded.username,
        first_name=excluded.first_name,
        last_active_at=excluded.last_active_at
    """,
    (
        user_id,
        username,
        first_name,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def touch_user(user_id):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET last_active_at=? WHERE id=?",
        (datetime.now().isoformat(), user_id)
    )

    conn.commit()
    conn.close()



def get_user(user_id):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    )

    user = cursor.fetchone()

    conn.close()

    return user



def set_contact(user_id, contact):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users
    SET trusted_contact=?
    WHERE id=?
    """,
    (
        contact,
        user_id
    ))

    conn.commit()
    conn.close()



# -------------------------
# TRUSTED CONTACTS
# -------------------------


def add_trusted_contact(owner_id, contact_id, contact_name):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 1
    FROM trusted_contacts
    WHERE owner_id=? AND contact_id=?
    """,
    (
        owner_id,
        contact_id
    ))

    if cursor.fetchone():
        conn.close()
        return

    cursor.execute("""
    INSERT INTO trusted_contacts
    (
        owner_id,
        contact_id,
        contact_name,
        created_at
    )
    VALUES (?, ?, ?, ?)
    """,
    (
        owner_id,
        contact_id,
        contact_name,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()



def get_trusted_contacts(owner_id):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT contact_id
    FROM trusted_contacts
    WHERE owner_id=?
    """,
    (owner_id,)
    )

    contacts = cursor.fetchall()

    conn.close()

    return [
        contact[0]
        for contact in contacts
    ]


def get_trusted_contact_details(owner_id):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        trusted_contacts.contact_id,
        trusted_contacts.contact_name,
        users.username
    FROM trusted_contacts
    LEFT JOIN users ON users.id = trusted_contacts.contact_id
    WHERE trusted_contacts.owner_id=?
    ORDER BY trusted_contacts.id
    """, (owner_id,))

    contacts = cursor.fetchall()
    conn.close()

    return contacts


def get_all_users():

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, username, first_name, last_active_at
    FROM users
    ORDER BY id DESC
    """)

    users = cursor.fetchall()
    conn.close()

    return users


def get_all_trusted_contact_details():

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        trusted_contacts.owner_id,
        owner.first_name,
        trusted_contacts.contact_id,
        trusted_contacts.contact_name
    FROM trusted_contacts
    LEFT JOIN users AS owner ON owner.id = trusted_contacts.owner_id
    ORDER BY trusted_contacts.id DESC
    """)

    contacts = cursor.fetchall()
    conn.close()

    return contacts


def get_user_conversation(user_id, limit=100):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT role, text, created_at
    FROM messages
    WHERE user_id=?
    ORDER BY id DESC
    LIMIT ?
    """, (user_id, limit))

    messages = list(reversed(cursor.fetchall()))
    conn.close()

    return messages


def save_user_memory(user_id, category, value):
    """Save one durable user preference or fact without duplicating it."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO user_memories (user_id, category, value, updated_at)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(user_id, category, value) DO UPDATE SET
        updated_at=excluded.updated_at
    """, (user_id, category, value, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_user_memories(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT category, value
    FROM user_memories
    WHERE user_id=?
    ORDER BY updated_at DESC, id DESC
    """, (user_id,))
    memories = cursor.fetchall()
    conn.close()
    return memories


def clear_user_memories(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_memories WHERE user_id=?", (user_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def get_voice_auto_reply(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT voice_auto_reply FROM user_settings WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return True if row is None else bool(row[0])


def set_voice_auto_reply(user_id, enabled):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO user_settings (user_id, voice_auto_reply)
    VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET voice_auto_reply=excluded.voice_auto_reply
    """, (user_id, int(enabled)))
    conn.commit()
    conn.close()


def get_preferred_voice(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT preferred_voice FROM user_settings WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] in {"male", "female"} else None


def set_preferred_voice(user_id, voice):
    if voice not in {"male", "female"}:
        raise ValueError("Unsupported voice")
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO user_settings (user_id, preferred_voice)
    VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET preferred_voice=excluded.preferred_voice
    """, (user_id, voice))
    conn.commit()
    conn.close()



def remove_trusted_contact(owner_id, contact_id):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM trusted_contacts
    WHERE owner_id=?
    AND contact_id=?
    """,
    (
        owner_id,
        contact_id
    ))

    conn.commit()
    conn.close()



# -------------------------
# EVENTS
# -------------------------


def add_event(user_id, event_type, level, score):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO events
    (
        user_id,
        event_type,
        level,
        score,
        created_at
    )
    VALUES (?, ?, ?, ?, ?)
    """,
    (
        user_id,
        event_type,
        level,
        score,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()



# -------------------------
# MESSAGES
# -------------------------


def add_message(user_id, role, text):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO messages
    (
        user_id,
        role,
        text,
        created_at
    )
    VALUES (?, ?, ?, ?)
    """,
    (
        user_id,
        role,
        text,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()
