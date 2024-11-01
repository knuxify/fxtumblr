# SPDX-License-Identifier: MIT
"""
Statistic counting code.
"""

from .config import config

import aiosqlite
import asyncio
import time
import datetime
from typing import List
import traceback
import hashlib
import uuid

STATS_DB = config.get("stats_db", "stats.db")
STATS_LOCK = asyncio.Lock()
TABLE_EXISTS = False

def hash_post(blogname: str, postid: str):
    return hashlib.sha256(str.encode(f"{blogname}-{postid}")).hexdigest()

async def register_hit(blogname: str, postid: str, modifiers: List[str] = [], failed: bool = False):
    async with STATS_LOCK:
        now = datetime.datetime.now()
        # Round time down to closest 10 minutes
        now = now.replace(minute=((now.minute // 10) * 10), second=0)

        data = {
            "id": str(uuid.uuid4()),
            "time": int(now.timestamp()),
            "post": hash_post(blogname, postid),
            "modifiers": ",".join(modifiers),
            "failed": failed
        }

        try:
            async with aiosqlite.connect(STATS_DB) as db:
                await setup_db(db)
                await db.execute("INSERT INTO fxtumblr_stats (id, time, post, modifiers, failed) VALUES (:id, :time, :post, :modifiers, :failed);", data)
                await db.commit()
        except:
            traceback.print_exc()

async def setup_db(db):
    """
    Sets up the SQLite database for statistics.
    """
    global TABLE_EXISTS

    # Check if fxtumblr_stats table exists
    if not TABLE_EXISTS:
        ret = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fxtumblr_stats';")
        ret = await ret.fetchall()
        if ret:
            TABLE_EXISTS = True
            return

        # If it does not exist, create it
        await db.execute("""CREATE TABLE fxtumblr_stats(
            id VARCHAR(48) PRIMARY KEY,
            time INTEGER,
            post VARCHAR(256),
            modifiers TEXT,
            failed BOOLEAN
        );""")

        TABLE_EXISTS = True
