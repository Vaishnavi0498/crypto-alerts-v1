from plugins.ui_price_alert import (
    UIPriceAlertPlugin
)

from plugins.hourly_move_alert import (
    HourlyMoveAlertPlugin
)


def load_plugins():

    return [
        UIPriceAlertPlugin(),
        HourlyMoveAlertPlugin()
    ]