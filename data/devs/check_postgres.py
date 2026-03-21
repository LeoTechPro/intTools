import asyncio
import os

import asyncpg


async def main() -> None:
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        database=os.getenv("DB_NAME", "postgres"),
    )
    value = await conn.fetchval("SELECT 1")
    print(f"PostgreSQL connection OK, test query returned {value}")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
