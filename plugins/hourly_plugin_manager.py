from plugins.hourly_move_plugin import (
    HourlyMovePlugin
)

from plugins.hourly_volume_plugin import (
    HourlyVolumePlugin
)


def load_hourly_plugins():

    return [
        HourlyMovePlugin(),
        HourlyVolumePlugin()
    ]