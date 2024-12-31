# SPDX-License-Identifier: MIT
"""
Statistic counting code.
"""

from .config import config

import asyncio
import time
import datetime
from typing import List
import traceback
import hashlib
import uuid

STATS_DB_TYPE = config.get("stats_db_type", "sqlite")
if STATS_DB_TYPE == "sqlite":
    import aiosqlite

    STATS_DB = config.get("stats_db", "stats.db")
elif STATS_DB_TYPE == "postgres":
    import psycopg

    PSQL_DSN = ' '.join([
                            f"host={config['stats_db_host']}",
                            f"port={config['stats_db_port']}",
                            f"user={config['stats_db_user']}",
                            f"password={config['stats_db_password']}",
                            f"dbname={config['stats_db_name']}",
                        ])

else:
    raise ValueError("stats_db_type must be one of: sqlite, postgres")
STATS_IGNORE = config.get("stats_ignore", [])
STATS_LOCK = asyncio.Lock()
TABLE_EXISTS = False


def hash_post(blogname: str, postid: str):
    return hashlib.sha256(str.encode(f"{blogname}-{postid}")).hexdigest()


async def register_hit(
    blogname: str, postid: str, modifiers: List[str] = [], failed: bool = False
):
    if f"{blogname}-{postid}" in STATS_IGNORE:
        return
    async with STATS_LOCK:
        now = datetime.datetime.now()
        # Round time down to closest 10 minutes
        now = now.replace(minute=((now.minute // 10) * 10), second=0)

        data = {
            "id": str(uuid.uuid4()),
            "time": int(now.timestamp()),
            "post": hash_post(blogname, postid),
            "modifiers": ",".join(modifiers),
            "failed": failed,
        }

        try:
            if STATS_DB_TYPE == "sqlite":
                async with aiosqlite.connect(STATS_DB) as db:
                    await setup_db(db)
                    await db.execute(
                        "INSERT INTO fxtumblr_stats (id, time, post, modifiers, failed) VALUES (:id, :time, :post, :modifiers, :failed);",
                        data,
                    )
                    await db.commit()
            elif STATS_DB_TYPE == "postgres":
                async with await psycopg.AsyncConnection.connect(PSQL_DSN) as aconn:
                    async with aconn.cursor() as acur:
                        await setup_db(acur)
                        await acur.execute(
                            "INSERT INTO fxtumblr_stats (id, time, post, modifiers, failed) VALUES (%s, %s, %s, %s, %s);", (data["id"], data["time"], data["post"], data["modifiers"], data["failed"])
                        )
                    await aconn.commit()
        except:
            traceback.print_exc()


async def setup_db(db):
    """
    Sets up the database for statistics.
    """
    global TABLE_EXISTS

    # Check if fxtumblr_stats table exists
    if not TABLE_EXISTS:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS fxtumblr_stats(
            id VARCHAR(48) PRIMARY KEY,
            time INTEGER,
            post VARCHAR(256),
            modifiers TEXT,
            failed BOOLEAN
            );
            """)

        TABLE_EXISTS = True
