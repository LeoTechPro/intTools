#!/usr/bin/env python3
from _entrypoint_common import EntryPointConfig, main


if __name__ == "__main__":
    raise SystemExit(
        main(
            EntryPointConfig(
                profile="punktb-prod-migrator",
                role="db_migrator_prod",
                database="punkt_b_prod",
                environment="prod",
            ),
            "migrate",
            prod=True,
        )
    )
