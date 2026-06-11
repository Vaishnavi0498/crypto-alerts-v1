from plugins.scanner.hourly_move_plugin import (
    HourlyMovePlugin
)

from plugins.scanner.hourly_volume_plugin import (
    HourlyVolumePlugin
)

from plugins.scanner.rsi_plugin import (
    RSIPlugin
)


def load_plugins():

    return [
        HourlyMovePlugin(),
        HourlyVolumePlugin(),
        RSIPlugin()
    ]