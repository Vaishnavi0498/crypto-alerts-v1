class BasePlugin:

    def process_trade(
        self,
        symbol,
        price,
        trade
    ):
        return []

    def process_kline(
        self,
        symbol,
        kline
    ):
        return []