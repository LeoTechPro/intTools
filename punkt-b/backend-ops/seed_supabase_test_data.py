#!/usr/bin/env python3
"""Seed Supabase with demo specialists, clients, and diagnostic results.

The script connects directly to Postgres (through dockerised psql) and inserts
stable test data. Existing demo records are removed before re-seeding to keep
runs idempotent.

Usage:
    python3 backend/scripts/seed_supabase_test_data.py

Requirements:
    `.env` in the repository root must contain connection details for the self-hosted Supabase
    database (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, DB_HOST, DB_PORT).
    Environment variable `SERVICE_ACCOUNT_PASSWORD` must be provided to seed the
    сервисная учётка `service-account.local`.
"""

from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

ENV_PATH = Path(".env")
if not ENV_PATH.exists():
    print("❌ .env not found in repository root", file=sys.stderr)
    sys.exit(1)

# Load .env
for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    os.environ.setdefault(key, value)

POSTGRES_USER = os.environ.get("POSTGRES_USER", "supabase_admin")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")
POSTGRES_HOST = os.environ.get("DB_HOST", "127.0.0.1")
POSTGRES_PORT = os.environ.get("DB_PORT", "5432")

if not POSTGRES_PASSWORD:
    print("❌ POSTGRES_PASSWORD not set in root .env", file=sys.stderr)
    sys.exit(1)

PSQL_HOST = "127.0.0.1" if POSTGRES_HOST in {"host.docker.internal", "localhost"} else POSTGRES_HOST
CONN_STRING = (
    f"postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{PSQL_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

DEFAULT_PASSWORD = os.getenv("SEED_DEFAULT_PASSWORD", "Test1234!")
SERVICE_ACCOUNT_EMAIL = "service-account@example.local"
SERVICE_ACCOUNT_PASSWORD = os.getenv("SERVICE_ACCOUNT_PASSWORD")

if SERVICE_ACCOUNT_PASSWORD is None:
    print("❌ Set SERVICE_ACCOUNT_PASSWORD environment variable for the service account", file=sys.stderr)
    sys.exit(1)
AVAILABLE_DIAGNOSTICS = [0, 1, 3, 5, 6, 11, 13, 14]
DIAGNOSTICS = [
    (0, "riasec", "RIASEC профориентация"),
    (1, "interests", "Интересы и склонности"),
    (2, "values", "Ценности"),
    (3, "ideal_work", "Идеальная работа"),
    (4, "antirating", "Антирейтинг профессий"),
    (5, "needs", "Карьерные якоря"),
    (6, "motivation", "Мотивация"),
    (7, "skills", "Навыки"),
    (8, "behaviour", "Рабочие сценарии"),
    (9, "friends_interview", "Интервью с друзьями"),
    (10, "family_interview", "Интервью с семьёй"),
    (11, "career_story", "Варианты карьерных историй"),
    (12, "dream_roles", "Мечты и сценарии"),
    (13, "life_balance", "Баланс сфер жизни"),
    (14, "stress_profile", "Стресс-профиль"),
]
NAMESPACE = uuid.UUID("9f5ccbc1-e31f-4f37-95f6-6bbb6d954f61")
random.seed(20251027)


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def json_literal(obj: Dict) -> str:
    return sql_literal(json.dumps(obj, ensure_ascii=False)) + "::jsonb"


def deterministic_uuid(value: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, value)


def bool_sql(value: bool) -> str:
    return "true" if value else "false"


def int_array_literal(values: List[int]) -> str:
    if not values:
        return "ARRAY[]::int[]"
    return "ARRAY[" + ",".join(str(v) for v in values) + "]::int[]"


def slugify_candidate(value: str, fallback_seed: str) -> str:
    base = value.split("@", 1)[0].lower()
    base = re.sub(r"[^a-z0-9._-]", "-", base)
    base = re.sub(r"-{2,}", "-", base).strip("-")
    if len(base) < 6:
        suffix = uuid.uuid5(NAMESPACE, fallback_seed).hex[:6]
        base = f"{base}-{suffix}" if base else suffix
    return base[:64]


ADMINS: List[Dict] = [
    {"email": "seed-001@punctb.test", "name": "Анна", "surname": "Романова", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Москва"},
]

MANAGERS: List[Dict] = [
    {"email": "seed-002@punctb.test", "name": "Екатерина", "surname": "Кирсанова", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Москва"},
    {"email": "seed-003@punctb.test", "name": "Дмитрий", "surname": "Поляков", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Санкт-Петербург"},
    {"email": "seed-004@punctb.test", "name": "Гузель", "surname": "Нуриева", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Казань"},
]

SPECIALISTS: List[Dict] = [
    {"email": "seed-005@punctb.test", "name": "Иван", "surname": "Иванов", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Москва", "manager_index": 0},
    {"email": "seed-006@punctb.test", "name": "Арина", "surname": "Сутягина", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Казань", "manager_index": 1},
    {"email": "seed-007@punctb.test", "name": "Мария", "surname": "Чаврова", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Новосибирск", "manager_index": 2},
    {"email": "seed-008@punctb.test", "name": "Шамиль", "surname": "Абидов", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Уфа", "manager_index": 0},
    {"email": "seed-009@punctb.test", "name": "Серафима", "surname": "Полешак", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Екатеринбург", "manager_index": 1},
    {"email": "seed-010@punctb.test", "name": "Алина", "surname": "Можаева", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Самара", "manager_index": 2},
    {"email": "seed-011@punctb.test", "name": "Татьяна", "surname": "Павлова", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Санкт-Петербург", "manager_index": 0},
    {"email": "seed-012@punctb.test", "name": "Амирхан", "surname": "Бийбулатов", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Грозный", "manager_index": 1},
    {"email": "seed-013@punctb.test", "name": "Ислам", "surname": "Еркеев", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Хабаровск", "manager_index": 2},
    {"email": "seed-014@punctb.test", "name": "Артём", "surname": "Казюнь", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Воронеж", "manager_index": 0},
    {"email": "seed-015@punctb.test", "name": "Михаил", "surname": "Панаитов", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Красноярск", "manager_index": 1},
    {"email": "seed-016@punctb.test", "name": "Иван", "surname": "Дериш", "phone": "+7 900 000 00-00", "country": "Россия", "city": "Пермь", "manager_index": 2},
]

CLIENTS: List[Dict] = [
    {"email": "seed-017@punctb.test", "name": "Иван Иванов", "phone": "+7 900 000 00-00", "manager_index": 0, "city": "Москва", "country": "Россия"},
    {"email": "seed-018@punctb.test", "name": "Арина Сутягина", "phone": "+7 900 000 00-00", "manager_index": 1, "city": "Казань", "country": "Россия"},
    {"email": "seed-019@punctb.test", "name": "Мария Чаврова", "phone": "+7 900 000 00-00", "manager_index": 2, "city": "Новосибирск", "country": "Россия"},
    {"email": "seed-020@punctb.test", "name": "Шамиль Абидов", "phone": "+7 900 000 00-00", "manager_index": 3, "city": "Уфа", "country": "Россия"},
    {"email": "seed-021@punctb.test", "name": "Серафима Полешак", "phone": "+7 900 000 00-00", "manager_index": 4, "city": "Екатеринбург", "country": "Россия"},
    {"email": "seed-022@punctb.test", "name": "Алина Можаева", "phone": "+7 900 000 00-00", "manager_index": 5, "city": "Самара", "country": "Россия"},
    {"email": "seed-023@punctb.test", "name": "Татьяна Павлова", "phone": "+7 900 000 00-00", "manager_index": 6, "city": "Санкт-Петербург", "country": "Россия"},
    {"email": "seed-024@punctb.test", "name": "Амирхан Бийбулатов", "phone": "+7 900 000 00-00", "manager_index": 7, "city": "Грозный", "country": "Россия"},
    {"email": "seed-025@punctb.test", "name": "Ислам Еркеев", "phone": "+7 900 000 00-00", "manager_index": 8, "city": "Хабаровск", "country": "Россия"},
    {"email": "seed-026@punctb.test", "name": "Артём Казюнь", "phone": "+7 900 000 00-00", "manager_index": 9, "city": "Воронеж", "country": "Россия"},
    {"email": "seed-027@punctb.test", "name": "Михаил Панаитов", "phone": "+7 900 000 00-00", "manager_index": 10, "city": "Красноярск", "country": "Россия"},
    {"email": "seed-028@punctb.test", "name": "Иван Дериш", "phone": "+7 900 000 00-00", "manager_index": 11, "city": "Пермь", "country": "Россия"},
    {"email": "seed-029@punctb.test", "name": "Софья Олейник", "phone": "+7 900 000 00-00", "manager_index": 0, "city": "Москва", "country": "Россия"},
    {"email": "seed-030@punctb.test", "name": "Эльмира Магомедова", "phone": "+7 900 000 00-00", "manager_index": 1, "city": "Махачкала", "country": "Россия"},
    {"email": "seed-031@punctb.test", "name": "Елизавета Степанова", "phone": "+7 900 000 00-00", "manager_index": 2, "city": "Томск", "country": "Россия"},
    {"email": "seed-032@punctb.test", "name": "Арсений Федотов", "phone": "+7 900 000 00-00", "manager_index": 3, "city": "Сочи", "country": "Россия"},
    {"email": "seed-033@punctb.test", "name": "Артём Винокуров", "phone": "+7 900 000 00-00", "manager_index": 4, "city": "Белгород", "country": "Россия"},
    {"email": "seed-034@punctb.test", "name": "Татьяна Шумская", "phone": "+7 900 000 00-00", "manager_index": 5, "city": "Ярославль", "country": "Россия"},
    {"email": "seed-035@punctb.test", "name": "Мария Кунаева", "phone": "+7 900 000 00-00", "manager_index": 6, "city": "Омск", "country": "Россия"},
    {"email": "seed-036@punctb.test", "name": "Сергей Титаренко", "phone": "+7 900 000 00-00", "manager_index": 7, "city": "Краснодар", "country": "Россия"},
    {"email": "seed-037@punctb.test", "name": "Ксения Царь", "phone": "+7 900 000 00-00", "manager_index": 8, "city": "Калининград", "country": "Россия"},
    {"email": "seed-038@punctb.test", "name": "Анна Хажипова", "phone": "+7 900 000 00-00", "manager_index": 9, "city": "Сургут", "country": "Россия"},
    {"email": "seed-039@punctb.test", "name": "Анастасия Бахарева", "phone": "+7 900 000 00-00", "manager_index": 10, "city": "Тольятти", "country": "Россия"},
    {"email": "seed-040@punctb.test", "name": "Кристина Иончикова", "phone": "+7 900 000 00-00", "manager_index": 11, "city": "Нижний Новгород", "country": "Россия"},
]

LEADS: List[Dict] = [
    {"email": "seed-041@punctb.test", "name": "Алексей Погодин", "phone": "+7 900 000 00-00", "manager_index": 0, "city": "Москва", "country": "Россия", "intent": "diagnostic"},
    {"email": "seed-042@punctb.test", "name": "Мария Журавлёва", "phone": "+7 900 000 00-00", "manager_index": 3, "city": "Екатеринбург", "country": "Россия", "intent": "diagnostic"},
    {"email": "seed-043@punctb.test", "name": "Валерия Дроздова", "phone": "+7 900 000 00-00", "manager_index": 5, "city": "Самара", "country": "Россия", "intent": "franchise"},
    {"email": "seed-044@punctb.test", "name": "Никита Королёв", "phone": "+7 900 000 00-00", "manager_index": 8, "city": "Хабаровск", "country": "Россия", "intent": "franchise"},
]


def riasec_payload() -> Dict[str, float]:
    return {
        "realism": round(random.uniform(0.1, 0.9), 2),
        "artistry": round(random.uniform(0.2, 1.0), 2),
        "sociality": round(random.uniform(0.2, 0.95), 2),
        "enterprise": round(random.uniform(0.2, 0.9), 2),
        "intelligence": round(random.uniform(0.2, 0.8), 2),
        "conventionality": round(random.uniform(0.2, 0.8), 2),
    }


def motivation_payload() -> Dict[str, int]:
    return {
        "anger": random.randint(5, 35),
        "anxiety": random.randint(5, 35),
        "levelOfMotivation": random.randint(0, 35),
        "сognitiveActivity": random.randint(20, 35),
        "achievementMotivation": random.randint(15, 35),
    }


def values_payload() -> Dict[str, int]:
    return {
        "creativity": random.randint(20, 40),
        "ownPrestige": random.randint(15, 40),
        "achievements": random.randint(20, 40),
        "socialContacts": random.randint(20, 40),
        "selfDevelopment": random.randint(20, 40),
        "ownIndividuality": random.randint(20, 40),
        "financialPosition": random.randint(20, 40),
        "spiritualSatisfaction": random.randint(20, 40),
    }


def needs_payload() -> Dict[str, int]:
    return {
        "service": random.randint(4, 10),
        "autonomy": random.randint(4, 10),
        "challenge": random.randint(1, 9),
        "lifestyle": random.randint(4, 9),
        "management": random.randint(3, 9),
        "сompetence": random.randint(3, 9),
        "jobStability": random.randint(4, 10),
        "entrepreneurship": random.randint(3, 9),
        "residenceStability": random.randint(3, 9),
    }


def build_sql() -> str:
    timestamp = datetime.utcnow().isoformat()
    manager_records = []
    client_records = []
    identities_records = []
    profiles_records = []
    user_diag_records = []

    target_emails = []

    if not MANAGERS:
        raise RuntimeError("MANAGERS list cannot be empty")
    if not SPECIALISTS:
        raise RuntimeError("SPECIALISTS list cannot be empty")

    # Service account (единственная сервисная учётка с полными правами)
    target_emails.append(SERVICE_ACCOUNT_EMAIL)
    service_user_id = deterministic_uuid(SERVICE_ACCOUNT_EMAIL)
    service_app_meta = {"provider": "email", "providers": ["email"]}
    service_user_meta = {
        "name": "PunctB Service",
        "surname": "Account",
        "phone": None,
    }
    manager_records.append(
        f"({sql_literal('00000000-0000-0000-0000-000000000000')}::uuid, {sql_literal(str(service_user_id))}::uuid, 'authenticated', 'authenticated',"
        f" {sql_literal(SERVICE_ACCOUNT_EMAIL)}, crypt({sql_literal(SERVICE_ACCOUNT_PASSWORD)}, gen_salt('bf', 10)), now(),"
        f" {json_literal(service_app_meta)}, {json_literal(service_user_meta)}, now(), now())"
    )
    identities_records.append(
        f"({sql_literal(str(service_user_id))}, {sql_literal(str(service_user_id))}::uuid, {json_literal({'email': SERVICE_ACCOUNT_EMAIL, 'sub': str(service_user_id), 'email_verified': True, 'phone_verified': False})}, 'email', now(), now(), now())"
    )
    service_profile_metadata = {
        "name": "PunctB Service",
        "email": SERVICE_ACCOUNT_EMAIL,
    }
    service_slug = slugify_candidate(SERVICE_ACCOUNT_EMAIL, SERVICE_ACCOUNT_EMAIL)
    profiles_records.append(
        "("
        f"{sql_literal(str(service_user_id))}::uuid, "
        f"'admin', "
        f"{sql_literal(SERVICE_ACCOUNT_EMAIL)}, "
        "NULL, "
        f"{sql_literal('PunctB')}, "
        f"{sql_literal('Service')}, "
        "NULL, "
        f"{sql_literal('internal:service')}, "
        f"{sql_literal('active')}, "
        f"{sql_literal(service_slug)}, "
        "NULL, NULL, "
        f"{bool_sql(True)}, "
        "NULL, "
        f"{bool_sql(True)}, "
        "NULL, "
        f"{bool_sql(False)}, "
        "NULL, NULL, "
        f"{json_literal(service_profile_metadata)}, "
        "now(), NULL, now(), NULL, NULL, NULL)"
    )

    for admin in ADMINS:
        target_emails.append(admin["email"])
        user_id = deterministic_uuid(admin["email"])
        app_meta = {"provider": "email", "providers": ["email"]}
        user_meta = {
            "name": admin["name"],
            "surname": admin["surname"],
            "phone": admin["phone"],
            "country": admin["country"],
            "city": admin["city"],
        }
        manager_records.append(
            f"({sql_literal('00000000-0000-0000-0000-000000000000')}::uuid, {sql_literal(str(user_id))}::uuid, 'authenticated', 'authenticated',"
            f" {sql_literal(admin['email'])}, crypt({sql_literal(DEFAULT_PASSWORD)}, gen_salt('bf', 10)), now(),"
            f" {json_literal(app_meta)}, {json_literal(user_meta)}, now(), now())"
        )
        identities_records.append(
            f"({sql_literal(str(user_id))}, {sql_literal(str(user_id))}::uuid, {json_literal({'email': admin['email'], 'sub': str(user_id), 'email_verified': True, 'phone_verified': False})}, 'email', now(), now(), now())"
        )
        metadata = {
            "name": admin["name"],
            "surname": admin["surname"],
            "phone": admin["phone"],
            "country": admin["country"],
            "city": admin["city"],
            "role_label": "Admin",
        }
        admin_slug = slugify_candidate(admin["email"], admin["email"])
        profiles_records.append(
            "("
            f"{sql_literal(str(user_id))}::uuid, "
            f"'admin', "
            f"{sql_literal(admin['email'])}, "
            f"{sql_literal(admin['phone'])}, "
            f"{sql_literal(admin['name'])}, "
            f"{sql_literal(admin['surname'])}, "
            "NULL, "
            f"{sql_literal('internal:admin')}, "
            f"{sql_literal('active')}, "
            f"{sql_literal(admin_slug)}, "
            f"{sql_literal(admin['country'])}, "
            f"{sql_literal(admin['city'])}, "
            f"{bool_sql(True)}, "
            "NULL, "
            f"{bool_sql(True)}, "
            "NULL, "
            f"{bool_sql(False)}, "
            "NULL, NULL, "
            f"{json_literal(metadata)}, "
            "now(), NULL, now(), NULL, NULL, NULL)"
        )

    for manager in MANAGERS:
        target_emails.append(manager["email"])
        user_id = deterministic_uuid(manager["email"])
        app_meta = {"provider": "email", "providers": ["email"]}
        user_meta = {
            "name": manager["name"],
            "surname": manager["surname"],
            "phone": manager["phone"],
            "country": manager["country"],
            "city": manager["city"],
        }
        manager_records.append(
            f"({sql_literal('00000000-0000-0000-0000-000000000000')}::uuid, {sql_literal(str(user_id))}::uuid, 'authenticated', 'authenticated',"
            f" {sql_literal(manager['email'])}, crypt({sql_literal(DEFAULT_PASSWORD)}, gen_salt('bf', 10)), now(),"
            f" {json_literal(app_meta)}, {json_literal(user_meta)}, now(), now())"
        )
        identities_records.append(
            f"({sql_literal(str(user_id))}, {sql_literal(str(user_id))}::uuid, {json_literal({'email': manager['email'], 'sub': str(user_id), 'email_verified': True, 'phone_verified': False})}, 'email', now(), now(), now())"
        )
        metadata = {
            "name": manager["name"],
            "surname": manager["surname"],
            "phone": manager["phone"],
            "country": manager["country"],
            "city": manager["city"],
            "role_label": "Care Manager",
        }
        manager_slug = slugify_candidate(manager["email"], manager["email"])
        profiles_records.append(
            "("
            f"{sql_literal(str(user_id))}::uuid, "
            f"'user', "
            f"{sql_literal(manager['email'])}, "
            f"{sql_literal(manager['phone'])}, "
            f"{sql_literal(manager['name'])}, "
            f"{sql_literal(manager['surname'])}, "
            "NULL, "
            f"{sql_literal('care')}, "
            f"{sql_literal('active')}, "
            f"{sql_literal(manager_slug)}, "
            f"{sql_literal(manager['country'])}, "
            f"{sql_literal(manager['city'])}, "
            f"{bool_sql(True)}, "
            "NULL, "
            f"{bool_sql(True)}, "
            "NULL, "
            f"{bool_sql(False)}, "
            "NULL, NULL, "
            f"{json_literal(metadata)}, "
            "now(), NULL, now(), NULL, NULL, NULL)"
        )

    for specialist in SPECIALISTS:
        target_emails.append(specialist["email"])
        user_id = deterministic_uuid(specialist["email"])
        manager_idx = specialist.get("manager_index")
        if manager_idx is None:
            manager_idx = 0
        manager_idx = manager_idx % len(MANAGERS)
        manager_email = MANAGERS[manager_idx]["email"]
        manager_id = deterministic_uuid(manager_email)
        app_meta = {"provider": "email", "providers": ["email"]}
        user_meta = {
            "name": specialist["name"],
            "surname": specialist["surname"],
            "phone": specialist["phone"],
            "country": specialist["country"],
            "city": specialist["city"],
        }
        manager_records.append(
            f"({sql_literal('00000000-0000-0000-0000-000000000000')}::uuid, {sql_literal(str(user_id))}::uuid, 'authenticated', 'authenticated',"
            f" {sql_literal(specialist['email'])}, crypt({sql_literal(DEFAULT_PASSWORD)}, gen_salt('bf', 10)), now(),"
            f" {json_literal(app_meta)}, {json_literal(user_meta)}, now(), now())"
        )
        identities_records.append(
            f"({sql_literal(str(user_id))}, {sql_literal(str(user_id))}::uuid, {json_literal({'email': specialist['email'], 'sub': str(user_id), 'email_verified': True, 'phone_verified': False})}, 'email', now(), now(), now())"
        )
        metadata = {
            "name": specialist["name"],
            "surname": specialist["surname"],
            "phone": specialist["phone"],
            "country": specialist["country"],
            "city": specialist["city"],
            "care_manager_email": manager_email,
        }
        specialist_slug = slugify_candidate(specialist["email"], specialist["email"])
        profiles_records.append(
            "("
            f"{sql_literal(str(user_id))}::uuid, "
            f"'user', "
            f"{sql_literal(specialist['email'])}, "
            f"{sql_literal(specialist['phone'])}, "
            f"{sql_literal(specialist['name'])}, "
            f"{sql_literal(specialist['surname'])}, "
            "NULL, "
            f"{sql_literal('franchisee')}, "
            f"{sql_literal('active')}, "
            f"{sql_literal(specialist_slug)}, "
            f"{sql_literal(specialist['country'])}, "
            f"{sql_literal(specialist['city'])}, "
            f"{bool_sql(True)}, "
            f"{int_array_literal(AVAILABLE_DIAGNOSTICS)}, "
            f"{sql_literal(str(manager_id))}::uuid, "
            f"{bool_sql(True)}, "
            "NULL, "
            f"{bool_sql(False)}, "
            "NULL, NULL, "
            f"{json_literal(metadata)}, "
            "now(), NULL, now(), NULL, NULL, NULL)"
        )

    for client in CLIENTS:
        target_emails.append(client["email"])
        client_id = deterministic_uuid(client["email"])
        specialist_idx = client.get("specialist_index", client["manager_index"])
        specialist_idx = specialist_idx % len(SPECIALISTS)
        specialist_email = SPECIALISTS[specialist_idx]["email"]
        specialist_id = deterministic_uuid(specialist_email)
        app_meta = {"provider": "email", "providers": ["email"]}
        user_meta = {
            "name": client["name"],
            "phone": client["phone"],
            "email": client["email"],
            "city": client["city"],
            "country": client["country"],
        }
        client_records.append(
            f"({sql_literal('00000000-0000-0000-0000-000000000000')}::uuid, {sql_literal(str(client_id))}::uuid, 'authenticated', 'authenticated',"
            f" {sql_literal(client['email'])}, crypt({sql_literal(DEFAULT_PASSWORD)}, gen_salt('bf', 10)), now(),"
            f" {json_literal(app_meta)}, {json_literal(user_meta)}, now(), now())"
        )
        identities_records.append(
            f"({sql_literal(str(client_id))}, {sql_literal(str(client_id))}::uuid, {json_literal({'email': client['email'], 'sub': str(client_id), 'email_verified': True, 'phone_verified': False})}, 'email', now(), now(), now())"
        )
        metadata = {
            "city": client["city"],
            "country": client["country"],
            "specialist_email": specialist_email,
        }
        client_slug = slugify_candidate(client["email"], client["email"])
        profiles_records.append(
            "("
            f"{sql_literal(str(client_id))}::uuid, "
            f"'user', "
            f"{sql_literal(client['email'])}, "
            f"{sql_literal(client['phone'])}, "
            f"{sql_literal(client['name'])}, "
            "NULL, "
            "NULL, "
            f"{sql_literal('diagnostic')}, "
            f"{sql_literal('new')}, "
            f"{sql_literal(client_slug)}, "
            f"{sql_literal(client['country'])}, "
            f"{sql_literal(client['city'])}, "
            f"{bool_sql(True)}, "
            f"{sql_literal(str(specialist_id))}::uuid, "
            f"{bool_sql(True)}, "
            "NULL, "
            f"{bool_sql(False)}, "
            "NULL, NULL, "
            f"{json_literal(metadata)}, "
            "now(), NULL, now(), NULL, NULL, NULL)"
        )
        # Generate four diagnostic results per client
        for diag_id, payload in [
            (0, riasec_payload()),
            (5, needs_payload()),
            (13, values_payload()),
            (14, motivation_payload()),
        ]:
            user_diag_records.append(
                f"({sql_literal(str(client_id))}::uuid, {sql_literal(str(specialist_id))}::uuid, {diag_id}, {json_literal(payload)}, ''::text, now(), now())"
            )

    for lead in LEADS:
        target_emails.append(lead["email"])
        lead_id = deterministic_uuid(lead["email"])
        manager_idx = lead.get("manager_index")
        if manager_idx is None:
            manager_idx = random.randrange(len(MANAGERS))
        else:
            manager_idx = manager_idx % len(MANAGERS)
        lead_manager_id = deterministic_uuid(MANAGERS[manager_idx]["email"])
        lead_password = uuid.uuid4().hex
        app_meta = {"provider": "email", "providers": ["email"]}
        user_meta = {
            "name": lead["name"],
            "phone": lead["phone"],
            "email": lead["email"],
        }
        client_records.append(
            f"({sql_literal('00000000-0000-0000-0000-000000000000')}::uuid, {sql_literal(str(lead_id))}::uuid, 'authenticated', 'authenticated',"
            f" {sql_literal(lead['email'])}, crypt({sql_literal(lead_password)}, gen_salt('bf', 10)), now(),"
            f" {json_literal(app_meta)}, {json_literal(user_meta)}, now(), now())"
        )
        identities_records.append(
            f"({sql_literal(str(lead_id))}, {sql_literal(str(lead_id))}::uuid, {json_literal({'email': lead['email'], 'sub': str(lead_id), 'email_verified': False, 'phone_verified': False})}, 'email', NULL, now(), now())"
        )
        lead_intent = lead.get("intent", "diagnostic")
        lead_type = "lead:franchise" if lead_intent == "franchise" else "lead:diagnostic"
        lead_metadata = {
            "city": lead.get("city"),
            "country": lead.get("country"),
            "intent_label": "На франшизу" if lead_intent == "franchise" else "На диагностику",
        }
        lead_slug = slugify_candidate(lead["email"], lead["email"])
        profiles_records.append(
            "("
            f"{sql_literal(str(lead_id))}::uuid, "
            f"'no_access', "
            f"{sql_literal(lead['email'])}, "
            f"{sql_literal(lead.get('phone', ''))}, "
            f"{sql_literal(lead['name'])}, "
            "NULL, "
            "NULL, "
            f"{sql_literal(lead_type)}, "
            f"{sql_literal('lead')}, "
            f"{sql_literal(lead_slug)}, "
            f"{sql_literal(lead.get('country', ''))}, "
            f"{sql_literal(lead.get('city', ''))}, "
            f"{bool_sql(True)}, "
            f"{sql_literal(str(lead_manager_id))}::uuid, "
            f"{bool_sql(True)}, "
            "NULL, "
            f"{bool_sql(False)}, "
            "NULL, NULL, "
            f"{json_literal(lead_metadata)}, "
            "now(), NULL, now(), NULL, NULL, NULL)"
        )

    email_literals = ", ".join(sql_literal(email) for email in target_emails)
    diagnostics_records = [
        f"({diag_id}, {sql_literal(slug)}, {sql_literal(title)}, true, now(), now())"
        for diag_id, slug, title in DIAGNOSTICS
    ]

    sql_parts = [
        "BEGIN;",
        f"CREATE TEMP TABLE seed_target_users ON COMMIT DROP AS SELECT id FROM auth.users WHERE email = ANY(ARRAY[{email_literals}]);",
        "DELETE FROM app.user_diag WHERE target_id IN (SELECT id FROM seed_target_users) OR supervisor_id IN (SELECT id FROM seed_target_users);",
        "DELETE FROM app.user_profiles WHERE id IN (SELECT id FROM seed_target_users);",
        "DELETE FROM auth.identities WHERE user_id IN (SELECT id FROM seed_target_users);",
        "DELETE FROM auth.users WHERE id IN (SELECT id FROM seed_target_users);",
        "",
        "INSERT INTO app.diagnostics (id, slug, title, is_active, created_at, updated_at) VALUES",
        ",\n".join(diagnostics_records) + "\nON CONFLICT (id) DO UPDATE SET slug = EXCLUDED.slug, title = EXCLUDED.title, is_active = EXCLUDED.is_active, updated_at = EXCLUDED.updated_at;",
        "",
        "INSERT INTO auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at, raw_app_meta_data, raw_user_meta_data, created_at, updated_at) VALUES",
        ",\n".join(manager_records + client_records) + "\nON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, raw_user_meta_data = EXCLUDED.raw_user_meta_data, updated_at = EXCLUDED.updated_at;",
        "",
        "INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at) VALUES",
        ",\n".join(identities_records) + "\nON CONFLICT (provider_id, provider) DO UPDATE SET identity_data = EXCLUDED.identity_data, updated_at = EXCLUDED.updated_at;",
        "",
        "INSERT INTO app.user_profiles (id, rls, email, phone, first_name, family_name, patronymic, type, status, slug, country, city, active, supervisor_id, contact_permission, is_phone_adult, is_blocked_royalty, first_result_at, last_result_at, metadata, created_at, created_by, updated_at, updated_by, removed_at, removed_by) VALUES",
        ",\n".join(profiles_records) + "\nON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, phone = EXCLUDED.phone, first_name = COALESCE(EXCLUDED.first_name, app.user_profiles.first_name), family_name = COALESCE(EXCLUDED.family_name, app.user_profiles.family_name), patronymic = COALESCE(EXCLUDED.patronymic, app.user_profiles.patronymic), type = COALESCE(EXCLUDED.type, app.user_profiles.type), status = COALESCE(EXCLUDED.status, app.user_profiles.status), slug = COALESCE(EXCLUDED.slug, app.user_profiles.slug), country = EXCLUDED.country, city = EXCLUDED.city, supervisor_id = COALESCE(app.user_profiles.supervisor_id, EXCLUDED.supervisor_id), contact_permission = COALESCE(EXCLUDED.contact_permission, app.user_profiles.contact_permission), is_phone_adult = COALESCE(EXCLUDED.is_phone_adult, app.user_profiles.is_phone_adult), metadata = jsonb_strip_nulls(app.user_profiles.metadata || EXCLUDED.metadata), active = EXCLUDED.active, updated_at = EXCLUDED.updated_at, updated_by = EXCLUDED.updated_by;",
        "INSERT INTO app.user_diag (target_id, supervisor_id, diagnostic_id, payload, open_answer, created_at, updated_at) VALUES",
        ",\n".join(user_diag_records) + "\nON CONFLICT DO NOTHING;",
        "COMMIT;",
    ]

    return "\n".join(sql_parts)


def execute_sql(sql: str) -> None:
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "host",
        "-i",
        "postgres",
        "psql",
        CONN_STRING,
    ]
    subprocess.run(cmd, input=sql.encode("utf-8"), check=True)


def main() -> None:
    sql = build_sql()
    with Path("backend/scripts/seed_supabase_test_data.sql").open("w", encoding="utf-8") as f:
        f.write(sql)
    execute_sql(sql)
    print("✅ Seed data inserted.")
    print(
        "Роли: "
        f"admin={len(ADMINS)}, manager={len(MANAGERS)}, specialist={len(SPECIALISTS)}, "
        f"client={len(CLIENTS)}, lead={len(LEADS)}"
    )
    print(f"Service account: {SERVICE_ACCOUNT_EMAIL} (password from SERVICE_ACCOUNT_PASSWORD)")
    print(f"Default password for demo users: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    main()
