from plugins.scanner.hourly_move_plugin import (
    HourlyMovePlugin
)

from plugins.scanner.hourly_volume_plugin import (
    HourlyVolumePlugin
)

from plugins.scanner.rsi_plugin import (
    RSIPlugin
)

from plugins.scanner.choc_plugin import (
    ChoCHPlugin
)
from plugins.scanner.monthly_breakout_plugin import (
    MonthlyBreakoutPlugin
)


def load_plugins(
    interval
):

    plugins = []

    if interval == "1h":

        plugins.append(
            HourlyMovePlugin()
        )

        plugins.append(
            HourlyVolumePlugin()
        )

    if interval == "1m":

        plugins.append(
            RSIPlugin()
        )

    if interval == "15m":

        plugins.append(
            ChoCHPlugin()
        )

    if interval == "monthly":
        plugins.append(MonthlyBreakoutPlugin())

    return plugins