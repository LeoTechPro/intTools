#!/usr/bin/env python3
import os, sys, time, argparse, math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

def dsn(prefix: str):
    params = dict(
        host=os.getenv(f"{prefix}_HOST"),
        port=os.getenv(f"{prefix}_PORT"),
        dbname=os.getenv(f"{prefix}_DB"),
        user=os.getenv(f"{prefix}_USER"),
        password=os.getenv(f"{prefix}_PASSWORD"),
    )
    sslmode = os.getenv(f"{prefix}_SSLMODE")
    sslroot = os.getenv(f"{prefix}_SSLROOTCERT")
    parts = [f"{k}={v}" for k, v in params.items() if v]
    if sslmode:
        parts.append(f"sslmode={sslmode}")
    if sslroot:
        parts.append(f"sslrootcert={sslroot}")
    return " ".join(parts)

SRC_DSN = dsn("SRC")
DST_DSN = dsn("DST")

@dataclass
class TableInfo:
    schema: str
    name: str
    pk_cols: List[str]
    has_updated_at: bool
    strategy: str  # 'updated_at', 'append_id', 'fallback'

def fetchall(conn, q, args=None):
    with conn.cursor() as c:
        c.execute(q, args or [])
        return c.fetchall()

def fetchone(conn, q, args=None):
    with conn.cursor() as c:
        c.execute(q, args or [])
        return c.fetchone()

def get_tables(conn, schema="public") -> List[str]:
    q = """
    select table_name
    from information_schema.tables
    where table_schema=%s and table_type='BASE TABLE'
    """
    return [r[0] for r in fetchall(conn, q, [schema])]

def get_pk(conn, schema, table) -> List[str]:
    q = """
    select a.attname
    from pg_index i
    join pg_attribute a on a.attrelid=i.indrelid and a.attnum=ANY(i.indkey)
    join pg_class c on c.oid=i.indrelid
    join pg_namespace n on n.oid=c.relnamespace
    where i.indisprimary and n.nspname=%s and c.relname=%s
    order by a.attnum
    """
    return [r[0] for r in fetchall(conn, q, [schema, table])]

def get_columns(conn, schema, table) -> List[str]:
    q = """
    select column_name
    from information_schema.columns
    where table_schema=%s and table_name=%s
    order by ordinal_position
    """
    return [r[0] for r in fetchall(conn, q, [schema, table])]

def table_info(src_conn, dst_conn, table, schema="public") -> TableInfo:
    pk = get_pk(dst_conn, schema, table) or get_pk(src_conn, schema, table)  # пробуем на обеих
    cols_src = get_columns(src_conn, schema, table)
    has_upd = "updated_at" in cols_src
    # стратегия
    if has_upd and pk:
        strategy = "updated_at"
    elif pk == ["id"]:
        strategy = "append_id"
    else:
        strategy = "fallback"
    return TableInfo(schema=schema, name=table, pk_cols=pk, has_updated_at=has_upd, strategy=strategy)

def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'

def upsert_updated_at(src_conn, dst_conn, t: TableInfo, batch_size: int):
    cols = get_columns(src_conn, t.schema, t.name)
    pk = t.pk_cols
    if not pk:
        print(f"  [SKIP] {t.name}: нет PK → fallback")
        return 0
    non_pk = [c for c in cols if c not in pk]
    cols_list = ", ".join(map(quote_ident, cols))
    excluded_set = ", ".join([f'{quote_ident(c)}=EXCLUDED.{quote_ident(c)}' for c in non_pk])
    pk_list = ", ".join(map(quote_ident, pk))

    # целевая метка updated_at (может быть NULL, тогда берем с нуля)
    row = fetchone(dst_conn, f"select max(updated_at) from {quote_ident(t.schema)}.{quote_ident(t.name)}")
    cutoff = row[0]

    # считаем сколько строк к импорту
    if cutoff is None:
        cnt = fetchone(src_conn, f"select count(*) from {quote_ident(t.schema)}.{quote_ident(t.name)}")[0]
    else:
        cnt = fetchone(src_conn,
            f"select count(*) from {quote_ident(t.schema)}.{quote_ident(t.name)} where updated_at>%s", [cutoff])[0]

    imported = 0
    with src_conn.cursor(name=f"cur_{t.name}") as cur_src, dst_conn.cursor() as cur_dst:
        if cutoff is None:
            cur_src.itersize = batch_size
            cur_src.execute(f"select {cols_list} from {quote_ident(t.schema)}.{quote_ident(t.name)} order by {pk_list}")
        else:
            cur_src.itersize = batch_size
            cur_src.execute(
                f"select {cols_list} from {quote_ident(t.schema)}.{quote_ident(t.name)} "
                f"where updated_at>%s order by {pk_list}", [cutoff]
            )

        while True:
            rows = cur_src.fetchmany(batch_size)
            if not rows:
                break
            # формируем VALUES
            placeholders = ", ".join(["(" + ", ".join(["%s"]*len(cols)) + ")"]*len(rows))
            flat = []
            for r in rows:
                flat.extend(list(r))
            q = (
              f"insert into {quote_ident(t.schema)}.{quote_ident(t.name)} ({cols_list}) values {placeholders} "
              f"on conflict ({pk_list}) do update set {excluded_set} "
              f"where {quote_ident(t.schema)}.{quote_ident(t.name)}.updated_at IS DISTINCT FROM EXCLUDED.updated_at "
              f"   or {quote_ident(t.schema)}.{quote_ident(t.name)}.updated_at < EXCLUDED.updated_at"
            )
            cur_dst.execute(q, flat)
            imported += len(rows)
        dst_conn.commit()
    print(f"  [OK] {t.name}: upsert {imported} (нов/измен) из ~{cnt}")
    return imported

def append_by_id(src_conn, dst_conn, t: TableInfo, batch_size: int):
    # предполагаем целочисленный id
    row = fetchone(dst_conn, f"select coalesce(max(id),0) from {quote_ident(t.schema)}.{quote_ident(t.name)}")
    last_id = int(row[0]) if row and row[0] is not None else 0
    cols = get_columns(src_conn, t.schema, t.name)
    cols_list = ", ".join(map(quote_ident, cols))

    total = fetchone(src_conn,
        f"select count(*) from {quote_ident(t.schema)}.{quote_ident(t.name)} where id>%s", [last_id])[0]
    imported = 0
    with src_conn.cursor(name=f"cur_{t.name}") as cur_src, dst_conn.cursor() as cur_dst:
        cur_src.itersize = batch_size
        cur_src.execute(
            f"select {cols_list} from {quote_ident(t.schema)}.{quote_ident(t.name)} where id>%s order by id",
            [last_id]
        )
        while True:
            rows = cur_src.fetchmany(batch_size)
            if not rows:
                break
            placeholders = ", ".join(["(" + ", ".join(["%s"]*len(cols)) + ")"]*len(rows))
            flat = []
            for r in rows: flat.extend(list(r))
            q = f"insert into {quote_ident(t.schema)}.{quote_ident(t.name)} ({cols_list}) values {placeholders} on conflict do nothing"
            cur_dst.execute(q, flat)
            imported += len(rows)
        dst_conn.commit()
    print(f"  [OK] {t.name}: append {imported} новых из ~{total}")
    return imported

def verify_table(src_conn, dst_conn, table: str, schema="public") -> Dict[str, Optional[str]]:
    # лёгкая верификация: count, max(id), max(updated_at), быстрая «контрольная сумма» по SUM(pk) и COUNT(DISTINCT pk)
    def safe(q, conn, args=None):
        try: return fetchone(conn, q, args)[0]
        except Exception: return None

    cnt_s = safe(f"select count(*) from {quote_ident(schema)}.{quote_ident(table)}", src_conn)
    cnt_d = safe(f"select count(*) from {quote_ident(schema)}.{quote_ident(table)}", dst_conn)
    max_id_s = safe(f"select max(id) from {quote_ident(schema)}.{quote_ident(table)}", src_conn)
    max_id_d = safe(f"select max(id) from {quote_ident(schema)}.{quote_ident(table)}", dst_conn)
    max_upd_s = safe(f"select max(updated_at) from {quote_ident(schema)}.{quote_ident(table)}", src_conn)
    max_upd_d = safe(f"select max(updated_at) from {quote_ident(schema)}.{quote_ident(table)}", dst_conn)
    sum_id_s = safe(f"select sum(id) from {quote_ident(schema)}.{quote_ident(table)}", src_conn)
    sum_id_d = safe(f"select sum(id) from {quote_ident(schema)}.{quote_ident(table)}", dst_conn)
    return dict(table=table, src_count=cnt_s, dst_count=cnt_d,
                src_max_id=max_id_s, dst_max_id=max_id_d,
                src_max_updated=max_upd_s, dst_max_updated=max_upd_d,
                src_sum_id=sum_id_s, dst_sum_id=sum_id_d)

def main():
    ap = argparse.ArgumentParser(description="PunktB: delta sync + verify (source->target)")
    ap.add_argument("--tables", help="Список таблиц через запятую (по умолчанию все из public)", default="")
    ap.add_argument("--batch-size", type=int, default=5000)
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--full-refresh", action="store_true", help="[DANGEROUS] полная перезаливка указанных таблиц")
    args = ap.parse_args()

    with psycopg2.connect(SRC_DSN) as src, psycopg2.connect(DST_DSN) as dst:
        src.autocommit = False
        dst.autocommit = False

        all_tables = args.tables.split(",") if args.tables else get_tables(src)
        all_tables = [t.strip() for t in all_tables if t.strip()]

        infos: List[TableInfo] = [table_info(src, dst, t) for t in all_tables]

        if args.verify-only:
            rows = [verify_table(src, dst, t.name) for t in infos]
            print(tabulate(rows, headers="keys", tablefmt="github"))
            sys.exit(0)

        if args.full-refresh:
            print("[DANGEROUS] Полная перезаливка включена. Будут очищены и импортированы указанные таблицы.")
            for t in infos:
                print(f"  → {t.name}: full refresh")
                cols = get_columns(src, t.schema, t.name)
                cols_list = ", ".join(map(quote_ident, cols))
                with src.cursor(name=f"cur_full_{t.name}") as cur_src, dst.cursor() as cur_dst:
                    cur_dst.execute(f"TRUNCATE {quote_ident(t.schema)}.{quote_ident(t.name)} RESTART IDENTITY CASCADE;")
                    dst.commit()
                    cur_src.itersize = args.batch_size
                    cur_src.execute(f"select {cols_list} from {quote_ident(t.schema)}.{quote_ident(t.name)}")
                    while True:
                        rows = cur_src.fetchmany(args.batch_size)
                        if not rows: break
                        placeholders = ", ".join(["(" + ", ".join(["%s"]*len(cols)) + ")"]*len(rows))
                        flat = []
                        for r in rows: flat.extend(list(r))
                        q = f"insert into {quote_ident(t.schema)}.{quote_ident(t.name)} ({cols_list}) values {placeholders}"
                        cur_dst.execute(q, flat)
                    dst.commit()

        else:
            print(f"Запускаю дельту батчами по {args.batch_size}...")
            for t in infos:
                if t.strategy == "updated_at":
                    upsert_updated_at(src, dst, t, args.batch_size)
                elif t.strategy == "append_id":
                    append_by_id(src, dst, t, args.batch_size)
                else:
                    print(f"  [WARN] {t.name}: ни updated_at, ни id-паттерна — пропускаю (или используйте --full-refresh --tables {t.name})")

        # Итоговая верификация
        print("\nВерификация (после синка):")
        rows = [verify_table(src, dst, t.name) for t in infos]
        print(tabulate(rows, headers="keys", tablefmt="github"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")

