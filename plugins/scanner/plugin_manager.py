from plugins.scanner.hourly_move_plugin import (
    HourlyMovePlugin
)

from plugins.scanner.hourly_volume_plugin import (
    HourlyVolumePlugin
)

from plugins.scanner.rsi_plugin import (
    RSIPlugin
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

    return plugins