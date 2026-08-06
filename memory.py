from datetime import datetime
from database import connect


def save_message(user_id, role, text):

    conn = connect()
    cursor = conn.cursor()

    created_at = datetime.now().isoformat()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        text TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    INSERT INTO messages
    (user_id, role, text, created_at)
    VALUES (?, ?, ?, ?)
    """,
    (
        user_id,
        role,
        text,
        created_at
    ))

    cursor.execute(
        "UPDATE users SET last_active_at=? WHERE id=?",
        (created_at, user_id)
    )

    conn.commit()
    conn.close()


def get_history(user_id, limit=30):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT role, text
    FROM messages
    WHERE user_id=?
    ORDER BY id DESC
    LIMIT ?
    """,
    (
        user_id,
        limit
    ))

    rows = cursor.fetchall()

    conn.close()

    history = []

    for role, text in reversed(rows):
        history.append(
            {
                "role": role,
                "content": text
            }
        )

    return history
