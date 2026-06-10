from plugins.scanner.hourly_move_plugin import (
    HourlyMovePlugin
)

from plugins.scanner.hourly_volume_plugin import (
    HourlyVolumePlugin
)


def load_plugins():

    return [
        HourlyMovePlugin(),
        HourlyVolumePlugin()
    ]