from scanners.base_scanner import (
    BaseScanner
)

from plugins.scanner.plugin_manager import (
    load_plugins
)


class MinuteScanner(
    BaseScanner
):

    INTERVAL = "1m"

    LIMIT = 300

    SLEEP_SECONDS = 300

    def __init__(self):

        super().__init__(
            plugins=load_plugins(
                interval="1m"
            )
        )


if __name__ == "__main__":

    MinuteScanner().run()