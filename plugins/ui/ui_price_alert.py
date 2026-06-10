from plugins.ui.base_plugin import BasePlugin

from alert_engine import (
    evaluate_alerts
)


class UIPriceAlertPlugin(
    BasePlugin
):

    def process_trade(
        self,
        symbol,
        price,
        trade
    ):
        return evaluate_alerts(
            symbol,
            price
        )