#!/usr/bin/env python3
from _entrypoint_common import EntryPointConfig, main


if __name__ == "__main__":
    raise SystemExit(
        main(
            EntryPointConfig(
                profile="punktb-legacy-ro",
                role="db_readonly_prod",
                database="punkt_b_legacy_prod",
                environment="prod",
            ),
            "readonly",
        )
    )
