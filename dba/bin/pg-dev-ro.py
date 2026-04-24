#!/usr/bin/env python3
from _entrypoint_common import EntryPointConfig, main


if __name__ == "__main__":
    raise SystemExit(
        main(
            EntryPointConfig(
                profile="intdata-dev-ro",
                role="db_readonly_dev",
                database="intdata",
                environment="dev",
            ),
            "readonly",
        )
    )
