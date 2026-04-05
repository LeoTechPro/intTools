from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "lib" / "intdb.py"
SPEC = spec_from_file_location("intdb_module", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
intdb = module_from_spec(SPEC)
sys.modules[SPEC.name] = intdb
SPEC.loader.exec_module(intdb)


class IntDbTests(unittest.TestCase):
    def test_parse_env_text_strips_comments(self) -> None:
        values = intdb._parse_env_text(
            """
            # comment
            A=1
            B=hello # inline
            C="quoted # keep"
            export D=world
            """
        )
        self.assertEqual(values["A"], "1")
        self.assertEqual(values["B"], "hello")
        self.assertEqual(values["C"], "quoted # keep")
        self.assertEqual(values["D"], "world")

    def test_load_profiles_reads_profile_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "INTDB_PROFILE__INTDATA_DEV__PGHOST=api.intdata.pro",
                        "INTDB_PROFILE__INTDATA_DEV__PGPORT=5432",
                        "INTDB_PROFILE__INTDATA_DEV__PGDATABASE=intdata",
                        "INTDB_PROFILE__INTDATA_DEV__PGUSER=dev_user",
                        "INTDB_PROFILE__INTDATA_DEV__PGPASSWORD=secret",
                        "INTDB_PROFILE__INTDATA_DEV__WRITE_CLASS=nonprod",
                    ]
                ),
                encoding="utf-8",
            )
            profile = intdb._get_profile(env_path, "intdata-dev")
        self.assertEqual(profile.host, "api.intdata.pro")
        self.assertEqual(profile.port, "5432")
        self.assertEqual(profile.user, "dev_user")
        self.assertEqual(profile.write_class, "nonprod")

    def test_write_guard_requires_exact_approval(self) -> None:
        profile = intdb.Profile(
            name="intdata-dev",
            key="INTDATA_DEV",
            values={
                "PGHOST": "api.intdata.pro",
                "PGDATABASE": "intdata",
                "PGUSER": "dev_user",
                "PGPASSWORD": "secret",
            },
        )
        with self.assertRaises(intdb.IntDbError):
            intdb._ensure_write_allowed(profile, approve_target=None, force_prod_write=False)
        intdb._ensure_write_allowed(profile, approve_target="intdata-dev", force_prod_write=False)

    def test_prod_guard_requires_force_flag(self) -> None:
        profile = intdb.Profile(
            name="intdata-prod",
            key="INTDATA_PROD",
            values={
                "PGHOST": "vds.intdata.pro",
                "PGDATABASE": "intdata",
                "PGUSER": "prod_user",
                "PGPASSWORD": "secret",
                "WRITE_CLASS": "prod",
            },
        )
        with self.assertRaises(intdb.IntDbError):
            intdb._ensure_write_allowed(profile, approve_target="intdata-prod", force_prod_write=False)
        intdb._ensure_write_allowed(profile, approve_target="intdata-prod", force_prod_write=True)

    def test_read_manifest_versions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            init_dir = repo / "init"
            init_dir.mkdir(parents=True, exist_ok=True)
            (init_dir / "migration_manifest.lock").write_text(
                "20260405093000|first.sql|checksum\n20260405113000|second.sql|checksum\n",
                encoding="utf-8",
            )
            versions = intdb._read_manifest_versions(repo)
        self.assertEqual(
            versions,
            [
                ("20260405093000", "first.sql"),
                ("20260405113000", "second.sql"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
