from database import get_connection


def init_price_table():

    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS prices (
        symbol TEXT PRIMARY KEY,
        price REAL,
        updated_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def update_price(
    symbol,
    price,
    updated_at
):

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO prices (
            symbol,
            price,
            updated_at
        )
        VALUES (?, ?, ?)
        ON CONFLICT(symbol)
        DO UPDATE SET
            price=excluded.price,
            updated_at=excluded.updated_at
        """,
        (
            symbol,
            price,
            updated_at
        )
    )

    conn.commit()
    conn.close()


def get_prices():

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT symbol,
               price,
               updated_at
        FROM prices
        ORDER BY symbol
        """
    ).fetchall()

    conn.close()

    return rows

def get_price(symbol):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT price
        FROM prices
        WHERE symbol = ?
        """,
        (symbol,)
    ).fetchone()

    conn.close()

    if row:
        return row[0]

    return None