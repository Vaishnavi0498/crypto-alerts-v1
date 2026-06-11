from database import init_db

init_db()

print("Database initialized")

cursor.execute("""
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