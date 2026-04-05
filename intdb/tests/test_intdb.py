from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest import mock


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

    def test_resolve_data_repo_uses_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            resolved = intdb._resolve_data_repo(str(repo))
            self.assertEqual(resolved, repo.resolve())

    def test_resolve_data_repo_uses_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            previous = os.environ.get("INTDB_DATA_REPO")
            os.environ["INTDB_DATA_REPO"] = str(repo)
            try:
                resolved = intdb._resolve_data_repo(None)
            finally:
                if previous is None:
                    os.environ.pop("INTDB_DATA_REPO", None)
                else:
                    os.environ["INTDB_DATA_REPO"] = previous
            self.assertEqual(resolved, repo.resolve())

    def test_resolve_data_repo_reads_local_env_file(self) -> None:
        previous_root = intdb.TOOL_ROOT
        previous = os.environ.get("INTDB_DATA_REPO")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "custom-data"
            repo.mkdir()
            tool_root = root / "tools" / "intdb"
            tool_root.mkdir(parents=True, exist_ok=True)
            (tool_root / ".env").write_text(f"INTDB_DATA_REPO={repo}\n", encoding="utf-8")
            intdb.TOOL_ROOT = tool_root
            try:
                os.environ.pop("INTDB_DATA_REPO", None)
                resolved = intdb._resolve_data_repo(None)
            finally:
                intdb.TOOL_ROOT = previous_root
                if previous is None:
                    os.environ.pop("INTDB_DATA_REPO", None)
                else:
                    os.environ["INTDB_DATA_REPO"] = previous
            self.assertEqual(resolved, repo.resolve())

    def test_resolve_data_repo_requires_hint_when_auto_not_found(self) -> None:
        previous_root = intdb.TOOL_ROOT
        previous = os.environ.get("INTDB_DATA_REPO")
        with tempfile.TemporaryDirectory() as tmpdir:
            intdb.TOOL_ROOT = Path(tmpdir) / "tools" / "intdb"
            try:
                os.environ.pop("INTDB_DATA_REPO", None)
                with self.assertRaises(intdb.IntDbError):
                    intdb._resolve_data_repo(None)
            finally:
                intdb.TOOL_ROOT = previous_root
                if previous is None:
                    os.environ.pop("INTDB_DATA_REPO", None)
                else:
                    os.environ["INTDB_DATA_REPO"] = previous

    def test_run_process_keeps_secrets_in_env_not_in_argv(self) -> None:
        captured: dict[str, object] = {}

        def fake_run(command: list[str], **kwargs: object) -> object:
            captured["command"] = command
            captured["env"] = kwargs["env"]
            return intdb.subprocess.CompletedProcess(command, 0, "", "")

        previous_run = intdb.subprocess.run
        intdb.subprocess.run = fake_run
        try:
            intdb._run_process(
                ["psql", "--version"],
                env_map={
                    "PGPASSWORD": "secret",
                    "POSTGRES_PASSWORD": "other-secret",
                },
            )
        finally:
            intdb.subprocess.run = previous_run

        command = captured["command"]
        env_map = captured["env"]
        self.assertEqual(command, ["psql", "--version"])
        self.assertNotIn("PGPASSWORD=secret", command)
        self.assertNotIn("POSTGRES_PASSWORD=other-secret", command)
        self.assertEqual(env_map["PGPASSWORD"], "secret")
        self.assertEqual(env_map["POSTGRES_PASSWORD"], "other-secret")

    def test_query_remote_versions_returns_empty_when_schema_migrations_missing(self) -> None:
        calls: list[list[str]] = []

        def fake_run_checked(argv: list[str], **kwargs: object) -> object:
            calls.append(argv)
            return intdb.subprocess.CompletedProcess(argv, 0, "\n", "")

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
        previous_run_checked = intdb._run_checked
        previous_require_pg_command = intdb._require_pg_command
        intdb._run_checked = fake_run_checked
        intdb._require_pg_command = lambda command_name: command_name
        try:
            versions = intdb._query_remote_versions(profile)
        finally:
            intdb._run_checked = previous_run_checked
            intdb._require_pg_command = previous_require_pg_command

        self.assertEqual(versions, [])
        self.assertEqual(len(calls), 1)

    def test_require_pg_command_wraps_missing_binary(self) -> None:
        with mock.patch.object(intdb, "_resolve_command", return_value=None):
            with self.assertRaises(intdb.IntDbError):
                intdb._require_pg_command("psql")

    def test_require_bash_wraps_missing_binary(self) -> None:
        with mock.patch.object(intdb, "WINDOWS_GIT_BASH_PATHS", tuple()):
            with mock.patch.object(intdb.os, "name", "nt"):
                with mock.patch.object(intdb.shutil, "which", return_value=None):
                    with self.assertRaises(intdb.IntDbError):
                        intdb._require_bash()

    def test_require_bash_prefers_git_for_windows_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            git_bash = Path(tmpdir) / "bash.exe"
            git_bash.write_text("", encoding="utf-8")
            with mock.patch.object(intdb, "WINDOWS_GIT_BASH_PATHS", (git_bash,)):
                with mock.patch.object(intdb.os, "name", "nt"):
                    with mock.patch.object(intdb.shutil, "which", return_value=r"C:\Windows\System32\bash.exe"):
                        self.assertEqual(intdb._require_bash(), str(git_bash))

    def test_test_tcp_wraps_socket_errors(self) -> None:
        profile = intdb.Profile(
            name="intdata-dev",
            key="INTDATA_DEV",
            values={
                "PGHOST": "127.0.0.1",
                "PGPORT": "1",
                "PGDATABASE": "postgres",
                "PGUSER": "postgres",
                "PGPASSWORD": "secret",
            },
        )
        with mock.patch.object(intdb.socket, "create_connection", side_effect=ConnectionRefusedError("refused")):
            with self.assertRaises(intdb.IntDbError):
                intdb._test_tcp(profile)


if __name__ == "__main__":
    unittest.main()
