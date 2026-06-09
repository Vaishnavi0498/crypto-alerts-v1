from alert_engine import evaluate_alerts


class UIPriceAlertPlugin:

    def process(
        self,
        symbol,
        price,
        trade=None
    ):
        return evaluate_alerts(
            symbol,
            price
        )