from database import init_db

init_db()

print("Database initialized")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hourly_alerts (
    symbol TEXT,
    candle_time INTEGER,
    PRIMARY KEY(symbol, candle_time)
)
""")
""")