#!/usr/bin/env python3
from _entrypoint_common import EntryPointConfig, main


if __name__ == "__main__":
    raise SystemExit(
        main(
            EntryPointConfig(
                profile="punktb-test-bootstrap",
                role="intdata_test_bootstrap",
                database="punkt_b_test",
                environment="test",
            ),
            "test-bootstrap",
        )
    )
