import sqlite3

DB_NAME = "beaconfeed.db"


# =========================================================
# CONNECTION
# =========================================================


def get_connection():

    conn = sqlite3.connect(
        DB_NAME,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA journal_mode=WAL"
    )

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


# =========================================================
# INITIALIZE DATABASE
# =========================================================


def initialize_database():

    conn = get_connection()

    cursor = conn.cursor()

    # =========================================
    # USERS
    # =========================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (

        user_id TEXT PRIMARY KEY,

        username TEXT
    )
    """)

    # =========================================
    # SUBSCRIPTIONS
    # =========================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id TEXT,

        topic TEXT,

        UNIQUE(user_id, topic)
    )
    """)

    # =========================================
    # SEEN LINKS
    # =========================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seen_links (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id TEXT,

        link TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(user_id, link)
    )
    """)

    # =========================================
    # INDEXES
    # =========================================

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_subscriptions_user
    ON subscriptions(user_id)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_seen_links_user
    ON seen_links(user_id)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_seen_links_created
    ON seen_links(created_at)
    """)

    conn.commit()

    conn.close()


# =========================================================
# SUBSCRIPTIONS
# =========================================================


def add_subscription(user_id, username, topic):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO users (
            user_id,
            username
        )
        VALUES (?, ?)
        """,
        (user_id, username)
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO subscriptions (
            user_id,
            topic
        )
        VALUES (?, ?)
        """,
        (user_id, topic)
    )

    conn.commit()

    conn.close()


# =========================================================
# REMOVE SUBSCRIPTION
# =========================================================


def remove_subscription(user_id, topic):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM subscriptions
        WHERE user_id = ?
        AND topic = ?
        """,
        (user_id, topic)
    )

    conn.commit()

    conn.close()


# =========================================================
# GET USER TOPICS
# =========================================================


def get_user_topics(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT topic
        FROM subscriptions
        WHERE user_id = ?
        """,
        (user_id,)
    )

    rows = cursor.fetchall()

    conn.close()

    return [row["topic"] for row in rows]


# =========================================================
# GET ALL USERS
# =========================================================


def get_all_users_with_topics():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        users.user_id,
        users.username,
        subscriptions.topic
    FROM users
    LEFT JOIN subscriptions
    ON users.user_id = subscriptions.user_id
    """)

    rows = cursor.fetchall()

    conn.close()

    result = {}

    for row in rows:

        user_id = row["user_id"]

        if user_id not in result:

            result[user_id] = {
                "username": row["username"],
                "topics": []
            }

        if row["topic"]:

            result[user_id]["topics"].append(
                row["topic"]
            )

    return result


# =========================================================
# SEEN LINKS
# =========================================================


def link_exists(user_id, link):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM seen_links
        WHERE user_id = ?
        AND link = ?
        """,
        (user_id, link)
    )

    exists = cursor.fetchone()

    conn.close()

    return exists is not None


# =========================================================
# SAVE SEEN LINK
# =========================================================


def save_seen_link(user_id, link):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO seen_links (
            user_id,
            link
        )
        VALUES (?, ?)
        """,
        (user_id, link)
    )

    conn.commit()

    conn.close()


# =========================================================
# CLEANUP OLD LINKS
# =========================================================


def cleanup_seen_links(days=3):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM seen_links
        WHERE created_at <
        datetime('now', ?)
        """,
        (f'-{days} days',)
    )

    conn.commit()

    conn.close()