# Postgres Audit Playbook

Use this playbook for `review-sql-find` when collecting section data and assigning statuses.

## Section Catalog

| id | category | expected status domain |
| --- | --- | --- |
| access_control_roles | security | Critical/Warning/Advisory/Good |
| network_security | security | Critical/Warning/Advisory/Good |
| auth_ssl | security | Critical/Warning/Advisory/Good |
| audit_logging | security | Critical/Warning/Advisory/Good |
| connection_management | performance | Critical/Warning/Advisory/Good |
| query_performance | performance | Critical/Warning/Advisory/Good |
| wal_checkpoint | performance | Critical/Warning/Advisory/Good |
| autovacuum | performance | Critical/Warning/Advisory/Good |
| planner_settings | performance | Critical/Warning/Advisory/Good |
| parallelism_workers | performance | Critical/Warning/Advisory/Good |
| extensions | security | Critical/Warning/Advisory/Good |
| cache_efficiency | performance | Critical/Warning/Advisory/Good |
| replication_status | performance | Critical/Warning/Advisory/Good |

## Read-only SQL Checklist

Run only read-only SQL. Adapt query text to server version where needed.

### access_control_roles

```sql
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls, rolcanlogin, rolvaliduntil
FROM pg_roles
ORDER BY rolname;
```

### network_security

```sql
SELECT name, setting FROM pg_settings
WHERE name IN ('listen_addresses','port','max_connections');

SELECT line_number, type, database, user_name, address, netmask, auth_method
FROM pg_hba_file_rules
ORDER BY line_number;
```

### auth_ssl

```sql
SELECT name, setting FROM pg_settings
WHERE name IN (
  'password_encryption','ssl','ssl_min_protocol_version','ssl_ciphers','ssl_prefer_server_ciphers'
);
```

### audit_logging

```sql
SELECT name, setting FROM pg_settings
WHERE name IN (
  'log_connections','log_disconnections','log_line_prefix','log_min_duration_statement',
  'log_lock_waits','log_statement'
);
```

### connection_management

```sql
SELECT name, setting FROM pg_settings
WHERE name IN (
  'statement_timeout','lock_timeout','idle_in_transaction_session_timeout',
  'idle_session_timeout','max_connections','superuser_reserved_connections'
);

SELECT state, count(*) AS cnt
FROM pg_stat_activity
GROUP BY state
ORDER BY cnt DESC;
```

### query_performance

```sql
SELECT queryid, calls, total_exec_time, mean_exec_time, rows, query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

SELECT queryid, calls, total_exec_time, mean_exec_time, query
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 20;
```

### wal_checkpoint

```sql
SELECT name, setting FROM pg_settings
WHERE name IN (
  'checkpoint_timeout','checkpoint_completion_target','max_wal_size','min_wal_size',
  'wal_level','wal_compression','max_wal_senders','synchronous_commit','wal_writer_delay'
);

SELECT * FROM pg_stat_bgwriter;
```

### autovacuum

```sql
SELECT name, setting FROM pg_settings
WHERE name LIKE 'autovacuum%'
ORDER BY name;

SELECT schemaname, relname, n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 30;
```

### planner_settings

```sql
SELECT name, setting FROM pg_settings
WHERE name IN (
  'random_page_cost','seq_page_cost','effective_cache_size','work_mem',
  'default_statistics_target','effective_io_concurrency'
);
```

### parallelism_workers

```sql
SELECT name, setting FROM pg_settings
WHERE name IN (
  'max_worker_processes','max_parallel_workers','max_parallel_workers_per_gather',
  'max_parallel_maintenance_workers','parallel_leader_participation'
);
```

### extensions

```sql
SELECT extname, extversion, extnamespace::regnamespace AS schema
FROM pg_extension
ORDER BY extname;
```

### cache_efficiency

```sql
SELECT datname,
       blks_read,
       blks_hit,
       CASE WHEN blks_read + blks_hit = 0 THEN NULL
            ELSE round(100.0 * blks_hit / (blks_read + blks_hit), 2)
       END AS cache_hit_pct
FROM pg_stat_database
ORDER BY datname;
```

### replication_status

```sql
SELECT pg_is_in_recovery() AS is_replica;

SELECT pid, usename, application_name, client_addr, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn
FROM pg_stat_replication;

SELECT status, receive_start_lsn, receive_start_tli, written_lsn, flushed_lsn, latest_end_lsn
FROM pg_stat_wal_receiver;
```

## Severity Rules

Apply these defaults unless project policy overrides them.

- Critical:
  - public DB exposure patterns (`listen_addresses='*'` + broad `pg_hba` rules)
  - non-essential superusers or login roles with `rolbypassrls`
  - `query_performance` top query mean time >= 1000 ms and high total runtime
  - recursive or metadata query mean time >= 60000 ms
- Warning:
  - timeouts disabled (`statement_timeout=0`, `lock_timeout=0`, idle timeouts 0)
  - high idle ratio (`idle / total >= 0.7`)
  - expensive permission functions or repeated checks with significant CPU load
- Advisory:
  - weak defaults without immediate incident risk
  - stale monitoring coverage or partial telemetry
- Good:
  - secure defaults and no active high-risk findings in section

## Completeness Rules

Mark section as `INCOMPLETE` when at least one condition is true:

- section payload missing or unparsable
- missing required keys (`id`, `title`, `status`, `findings`, `recommendations`)
- explicit truncation marker exists (`<Truncated in logs>`, `Synthesis failed`)
- obvious tail artifacts exist (for example `- real`, unfinished recommendation ending in `for`)
- section status already equals `INCOMPLETE`

If any required section is `INCOMPLETE`, stop synthesis and re-request only failed sections.
