import sqlite3
from datetime import datetime

DB_PATH = "data/alerts.db"


def get_connection():

    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    conn.execute(
        "PRAGMA journal_mode=WAL"
    )

    return conn


def init_db():

    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS alerts (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        symbol TEXT NOT NULL,

        condition TEXT NOT NULL,

        target_price REAL NOT NULL,

        alert_type TEXT NOT NULL,

        notes TEXT,

        active INTEGER DEFAULT 1,

        triggered_count INTEGER DEFAULT 0,

        last_state TEXT,

        created_at TEXT,

        last_triggered_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS alert_history (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        alert_id INTEGER,

        symbol TEXT,

        trigger_price REAL,

        notes TEXT,

        triggered_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS hourly_alerts (

        symbol TEXT NOT NULL,

        candle_time INTEGER NOT NULL,

        alert_type TEXT NOT NULL,

        PRIMARY KEY (
            symbol,
            candle_time,
            alert_type
        )
    )
    """)

    conn.commit()
    conn.close()


# ---------------------------------
# ALERT CRUD
# ---------------------------------

def create_alert(
    symbol,
    condition,
    target_price,
    alert_type,
    notes
):

    conn = get_connection()

    cur = conn.execute(
        """
        INSERT INTO alerts (
            symbol,
            condition,
            target_price,
            alert_type,
            notes,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            symbol.upper(),
            condition,
            target_price,
            alert_type,
            notes,
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()

    alert_id = cur.lastrowid

    conn.close()

    return alert_id


def get_all_alerts():

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM alerts
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return rows


def get_active_alerts():

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM alerts
        WHERE active = 1
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return rows


def get_triggered_alerts():

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM alerts
        WHERE triggered_count > 0
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return rows


def delete_alert(alert_id):

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM alerts
        WHERE id = ?
        """,
        (alert_id,)
    )

    conn.commit()
    conn.close()


def reset_alert(alert_id):

    conn = get_connection()

    conn.execute(
        """
        UPDATE alerts
        SET
            active = 1,
            triggered_count = 0,
            last_state = NULL,
            last_triggered_at = NULL
        WHERE id = ?
        """,
        (alert_id,)
    )

    conn.commit()
    conn.close()


def deactivate_alert(alert_id):

    conn = get_connection()

    conn.execute(
        """
        UPDATE alerts
        SET active = 0
        WHERE id = ?
        """,
        (alert_id,)
    )

    conn.commit()
    conn.close()


def update_alert(
    alert_id,
    condition,
    target_price,
    alert_type,
    notes
):

    conn = get_connection()

    conn.execute(
        """
        UPDATE alerts
        SET
            condition = ?,
            target_price = ?,
            alert_type = ?,
            notes = ?
        WHERE id = ?
        """,
        (
            condition,
            target_price,
            alert_type,
            notes,
            alert_id
        )
    )

    conn.commit()
    conn.close()


# ---------------------------------
# STATE MANAGEMENT
# ---------------------------------

def update_state(
    alert_id,
    state
):

    conn = get_connection()

    conn.execute(
        """
        UPDATE alerts
        SET last_state = ?
        WHERE id = ?
        """,
        (
            state,
            alert_id
        )
    )

    conn.commit()
    conn.close()


def mark_triggered(alert_id):

    conn = get_connection()

    conn.execute(
        """
        UPDATE alerts
        SET
            triggered_count = triggered_count + 1,
            last_triggered_at = ?
        WHERE id = ?
        """,
        (
            datetime.utcnow().isoformat(),
            alert_id
        )
    )

    conn.commit()
    conn.close()


# ---------------------------------
# HISTORY
# ---------------------------------

def add_history(
    alert_id,
    symbol,
    trigger_price,
    notes
):

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO alert_history(
            alert_id,
            symbol,
            trigger_price,
            notes,
            triggered_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            alert_id,
            symbol,
            trigger_price,
            notes,
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()
    conn.close()


def get_history():

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM alert_history
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return rows


# ---------------------------------
# SYMBOLS
# ---------------------------------

def get_monitored_symbols():

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT DISTINCT symbol
        FROM alerts
        WHERE active = 1
        """
    ).fetchall()

    conn.close()

    return [
        row[0]
        for row in rows
    ]


def active_alert_count():

    conn = get_connection()

    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM alerts
        WHERE active = 1
        """
    ).fetchone()[0]

    conn.close()

    return count


def triggered_alert_count():

    conn = get_connection()

    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM alerts
        WHERE triggered_count > 0
        """
    ).fetchone()[0]

    conn.close()

    return count


def history_count():

    conn = get_connection()

    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM alert_history
        """
    ).fetchone()[0]

    conn.close()

    return count

def hourly_alert_exists(
    symbol,
    candle_time,
    alert_type
):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT 1
        FROM hourly_alerts
        WHERE symbol = ?
        AND candle_time = ?
        AND alert_type = ?
        """,
        (
            symbol,
            candle_time,
            alert_type
        )
    ).fetchone()

    conn.close()

    return row is not None

def save_hourly_alert(
    symbol,
    candle_time,
    alert_type
):

    conn = get_connection()

    conn.execute(
        """
        INSERT OR IGNORE INTO
        hourly_alerts(
            symbol,
            candle_time,
            alert_type
        )
        VALUES (?,?,?)
        """,
        (
            symbol,
            candle_time,
            alert_type
        )
    )

    conn.commit()

    conn.close()