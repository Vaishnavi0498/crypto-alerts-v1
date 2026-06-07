from notifications import send_alert

send_alert(
    symbol="BTCUSDT",
    price=120000,
    notes="""
Liquidity sweep expected.

Support:
118000

Target:
130000
"""
)