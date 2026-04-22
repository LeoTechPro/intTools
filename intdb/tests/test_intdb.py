from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
import io
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

ENTRYPOINT_MODULE_PATH = Path(__file__).resolve().parents[1] / "bin" / "_entrypoint_common.py"
ENTRYPOINT_SPEC = spec_from_file_location("intdb_entrypoint_common", ENTRYPOINT_MODULE_PATH)
assert ENTRYPOINT_SPEC is not None and ENTRYPOINT_SPEC.loader is not None
entrypoints = module_from_spec(ENTRYPOINT_SPEC)
sys.modules[ENTRYPOINT_SPEC.name] = entrypoints
ENTRYPOINT_SPEC.loader.exec_module(entrypoints)


class IntDbTests(unittest.TestCase):
    def test_entrypoint_confirmation_requires_exact_target(self) -> None:
        with self.assertRaises(entrypoints.WrapperError):
            entrypoints._require_confirmation("wrong", "punkt_b_prod")
        entrypoints._require_confirmation("punkt_b_prod", "punkt_b_prod")

    def test_entrypoint_prints_banner(self) -> None:
        config = entrypoints.EntryPointConfig(
            profile="punktb-prod-ro",
            role="db_readonly_prod",
            database="punkt_b_prod",
            environment="prod",
        )
        with mock.patch("sys.stdout", new_callable=io.StringIO) as fake_stdout:
            entrypoints._print_banner(config, "READONLY")
            text = fake_stdout.getvalue()
        self.assertIn("YOU ARE CONNECTING TO PROD", text)
        self.assertIn("ROLE = db_readonly_prod", text)
        self.assertIn("MODE = READONLY", text)

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

    def test_punktb_legacy_target_sql_uses_rollback_for_dry_run(self) -> None:
        sql = intdb._build_punktb_legacy_target_sql(
            clients_path=Path("clients.jsonl"),
            managers_path=Path("managers.jsonl"),
            dry_run=True,
        )
        self.assertIn("ROLLBACK;", sql)
        self.assertNotIn("COMMIT;", sql)
        self.assertIn("lower(btrim(raw->>'email'))", sql)
        self.assertIn("pg_temp._intdb_uuid('punktb-user-email:' || email_norm)", sql)
        self.assertNotIn("punktb-client-email:", sql)
        self.assertNotIn("punktb-specialist-email:", sql)
        self.assertIn("raw->>'legacy_id'", sql)
        self.assertIn("c.raw->>'legacy_id'", sql)
        self.assertNotIn("legacy-client-", sql)
        self.assertNotIn("legacy-specialist-", sql)
        self.assertIn("target assess.specialists has conflicting legacy numeric slugs", sql)
        self.assertIn("target assess.clients has conflicting legacy numeric slugs", sql)
        self.assertIn("auth.users", sql)
        self.assertIn("assess.diag_results", sql)

    def test_punktb_legacy_target_sql_uses_commit_for_apply(self) -> None:
        sql = intdb._build_punktb_legacy_target_sql(
            clients_path=Path("clients.jsonl"),
            managers_path=Path("managers.jsonl"),
            dry_run=False,
        )
        self.assertIn("COMMIT;", sql)
        self.assertNotIn("ROLLBACK;", sql)

    def test_punktb_export_sql_is_read_only_copy_select(self) -> None:
        self.assertIn("\\copy (", intdb.PUNKTB_LEGACY_CLIENTS_EXPORT_SQL)
        self.assertIn("FROM public.clients", intdb.PUNKTB_LEGACY_CLIENTS_EXPORT_SQL)
        self.assertNotIn("INSERT", intdb.PUNKTB_LEGACY_CLIENTS_EXPORT_SQL.upper())
        self.assertIn("FROM public.managers", intdb.PUNKTB_LEGACY_MANAGERS_EXPORT_SQL)
        self.assertNotIn("UPDATE", intdb.PUNKTB_LEGACY_MANAGERS_EXPORT_SQL.upper())

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

    def test_resolve_data_repo_uses_non_windows_sibling_repo(self) -> None:
        previous_root = intdb.TOOL_ROOT
        previous = os.environ.get("INTDB_DATA_REPO")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "data"
            repo.mkdir()
            intdb.TOOL_ROOT = root / "tools" / "intdb"
            try:
                os.environ.pop("INTDB_DATA_REPO", None)
                with mock.patch.object(intdb.os, "name", "posix"):
                    resolved = intdb._resolve_data_repo(None)
            finally:
                intdb.TOOL_ROOT = previous_root
                if previous is None:
                    os.environ.pop("INTDB_DATA_REPO", None)
                else:
                    os.environ["INTDB_DATA_REPO"] = previous
            self.assertEqual(resolved, repo.resolve())

    def test_resolve_data_repo_skips_windows_sibling_repo(self) -> None:
        previous_root = intdb.TOOL_ROOT
        previous = os.environ.get("INTDB_DATA_REPO")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "data").mkdir()
            intdb.TOOL_ROOT = root / "tools" / "intdb"
            try:
                os.environ.pop("INTDB_DATA_REPO", None)
                with mock.patch.object(intdb.os, "name", "nt"):
                    with self.assertRaisesRegex(intdb.IntDbError, "agents@vds\\.intdata\\.pro:/int/data"):
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

    def test_assert_owner_control_token_requires_exact_ack(self) -> None:
        with self.assertRaises(intdb.IntDbError):
            intdb._assert_owner_control_token(None)
        with self.assertRaises(intdb.IntDbError):
            intdb._assert_owner_control_token("wrong")
        intdb._assert_owner_control_token(intdb.OWNER_CONTROL_ACK)

    def test_resolve_supabase_command_uses_supabase_binary_first(self) -> None:
        with mock.patch.object(intdb.shutil, "which", side_effect=[r"C:\supabase.exe", r"C:\npx.cmd"]):
            self.assertEqual(intdb._resolve_supabase_command(), [r"C:\supabase.exe"])

    def test_resolve_supabase_command_falls_back_to_npx(self) -> None:
        with mock.patch.object(intdb.shutil, "which", side_effect=[None, r"C:\npx.cmd"]):
            self.assertEqual(intdb._resolve_supabase_command(), [r"C:\npx.cmd", "supabase"])

    def test_supabase_status_db_url_extracts_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            with mock.patch.object(
                intdb,
                "_run_checked_capture",
                return_value=intdb.subprocess.CompletedProcess(
                    ["supabase", "status"],
                    0,
                    "API URL: http://127.0.0.1:54321\nDB URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres\n",
                    "",
                ),
            ):
                value = intdb._supabase_status_db_url(["supabase"], workspace)
        self.assertEqual(value, "postgresql://postgres:postgres@127.0.0.1:54322/postgres")

    def test_db_env_from_url_returns_full_postgres_env(self) -> None:
        env = intdb._db_env_from_url("postgresql://postgres:secret@127.0.0.1:54322/postgres")
        self.assertEqual(env["POSTGRES_HOST"], "127.0.0.1")
        self.assertEqual(env["POSTGRES_PORT"], "54322")
        self.assertEqual(env["POSTGRES_DB"], "postgres")
        self.assertEqual(env["POSTGRES_USER"], "postgres")
        self.assertEqual(env["POSTGRES_PASSWORD"], "secret")
        self.assertEqual(env["PGPASSWORD"], "secret")
        self.assertEqual(env["LOCAL_TEST_DATABASE_URL"], "postgresql://postgres:secret@127.0.0.1:54322/postgres")

    def test_local_test_parser_requires_confirmation(self) -> None:
        parser = intdb._build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["local-test", "run"])
        args = parser.parse_args(
            [
                "local-test",
                "run",
                "--confirm-owner-control",
                intdb.OWNER_CONTROL_ACK,
            ]
        )
        self.assertEqual(args.local_test_command, "run")

    def test_local_test_run_passes_full_postgres_env_to_migration_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "data"
            (repo_root / "init").mkdir(parents=True, exist_ok=True)
            args = intdb.argparse.Namespace(
                repo=str(repo_root),
                workdir=str(root / "workspace"),
                smoke_file=None,
                no_seed=True,
                keep_running=True,
                confirm_owner_control=intdb.OWNER_CONTROL_ACK,
            )
            captured_calls: list[dict[str, object]] = []
            with mock.patch.object(intdb, "_require_docker", return_value="docker"):
                with mock.patch.object(intdb, "_resolve_supabase_command", return_value=["supabase"]):
                    with mock.patch.object(intdb, "_supabase_status_db_url", return_value="postgresql://postgres:secret@127.0.0.1:54322/postgres"):
                        with mock.patch.object(intdb, "_require_bash", return_value=r"C:\Program Files\Git\bin\bash.exe"):
                            with mock.patch.object(intdb, "_run_checked", side_effect=lambda argv, **kwargs: captured_calls.append({"argv": argv, "kwargs": kwargs}) or intdb.subprocess.CompletedProcess(argv, 0, "", "")):
                                exit_code = intdb._cmd_local_test_run(args)
        self.assertEqual(exit_code, 0)
        self.assertEqual(captured_calls[0]["argv"], ["supabase", "init"])
        self.assertEqual(captured_calls[1]["argv"], ["supabase", "start"])
        migration_call = captured_calls[2]
        self.assertEqual(migration_call["argv"][0], r"C:\Program Files\Git\bin\bash.exe")
        self.assertEqual(migration_call["kwargs"]["extra_env"]["POSTGRES_HOST"], "127.0.0.1")
        self.assertEqual(migration_call["kwargs"]["extra_env"]["POSTGRES_PORT"], "54322")
        self.assertEqual(migration_call["kwargs"]["extra_env"]["POSTGRES_DB"], "postgres")
        self.assertEqual(migration_call["kwargs"]["extra_env"]["POSTGRES_USER"], "postgres")
        self.assertEqual(migration_call["kwargs"]["extra_env"]["POSTGRES_PASSWORD"], "secret")
        self.assertEqual(migration_call["kwargs"]["extra_env"]["PGPASSWORD"], "secret")

    def test_prepend_path_entry_moves_pg_bin_to_front(self) -> None:
        result = intdb._prepend_path_entry(
            r"C:\Windows\System32;C:\Program Files\PostgreSQL\17\bin;C:\Tools",
            Path(r"C:\Program Files\PostgreSQL\17\bin"),
        )
        self.assertEqual(
            result,
            r"C:\Program Files\PostgreSQL\17\bin;C:\Windows\System32;C:\Tools",
        )

    def test_migrate_data_incremental_prepends_pg_bin_to_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            env_path = root / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "INTDB_PROFILE__SMOKE__PGHOST=api.intdata.pro",
                        "INTDB_PROFILE__SMOKE__PGPORT=5432",
                        "INTDB_PROFILE__SMOKE__PGDATABASE=intdata",
                        "INTDB_PROFILE__SMOKE__PGUSER=dev_user",
                        "INTDB_PROFILE__SMOKE__PGPASSWORD=secret",
                    ]
                ),
                encoding="utf-8",
            )
            repo_root = root / "data"
            (repo_root / "init").mkdir(parents=True, exist_ok=True)
            (repo_root / "init" / "010_supabase_migrate.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            args = intdb.argparse.Namespace(
                target="smoke",
                approve_target="smoke",
                force_prod_write=False,
                repo=str(repo_root),
                mode="incremental",
                seed_business=False,
            )
            previous_root = intdb.TOOL_ROOT
            captured: dict[str, object] = {}
            intdb.TOOL_ROOT = root
            with mock.patch.object(intdb, "_require_bash", return_value=r"C:\Program Files\Git\bin\bash.exe"):
                with mock.patch.object(intdb, "_require_pg_command", return_value=r"C:\Program Files\PostgreSQL\17\bin\psql.exe"):
                    with mock.patch.object(intdb, "_run_checked", side_effect=lambda argv, **kwargs: captured.update({"argv": argv, "kwargs": kwargs}) or intdb.subprocess.CompletedProcess(argv, 0, "", "")):
                        try:
                            intdb._cmd_migrate_data(args)
                        finally:
                            intdb.TOOL_ROOT = previous_root

            self.assertEqual(captured["argv"][0], r"C:\Program Files\Git\bin\bash.exe")
            self.assertTrue(
                captured["kwargs"]["extra_env"]["PATH"].startswith(r"C:\Program Files\PostgreSQL\17\bin")
            )

    def test_migrate_data_bootstrap_passes_profile_password(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            env_path = root / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "INTDB_PROFILE__SMOKE__PGHOST=api.intdata.pro",
                        "INTDB_PROFILE__SMOKE__PGPORT=5432",
                        "INTDB_PROFILE__SMOKE__PGDATABASE=intdata",
                        "INTDB_PROFILE__SMOKE__PGUSER=dev_user",
                        "INTDB_PROFILE__SMOKE__PGPASSWORD=secret",
                    ]
                ),
                encoding="utf-8",
            )
            repo_root = root / "data"
            init_dir = repo_root / "init"
            init_dir.mkdir(parents=True, exist_ok=True)
            (init_dir / "schema.sql").write_text("select 1;\n", encoding="utf-8")
            args = intdb.argparse.Namespace(
                target="smoke",
                approve_target="smoke",
                force_prod_write=False,
                repo=str(repo_root),
                mode="bootstrap",
                seed_business=False,
            )
            previous_root = intdb.TOOL_ROOT
            calls: list[dict[str, object]] = []
            intdb.TOOL_ROOT = root
            with mock.patch.object(intdb, "_require_pg_command", return_value="psql"):
                with mock.patch.object(intdb, "_run_checked", side_effect=lambda argv, **kwargs: calls.append({"argv": argv, "kwargs": kwargs}) or intdb.subprocess.CompletedProcess(argv, 0, "", "")):
                    try:
                        intdb._cmd_migrate_data(args)
                    finally:
                        intdb.TOOL_ROOT = previous_root

            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["kwargs"]["profile"].password, "secret")
            self.assertEqual(calls[0]["kwargs"]["extra_env"]["POSTGRES_PASSWORD"], "secret")

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
