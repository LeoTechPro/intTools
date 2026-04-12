#!/usr/bin/env python3
from _entrypoint_common import EntryPointConfig, main


if __name__ == "__main__":
    raise SystemExit(
        main(
            EntryPointConfig(
                profile="intdata-dev-migrator",
                role="db_migrator_dev",
                database="intdata",
                environment="dev",
            ),
            "migrate",
        )
    )
