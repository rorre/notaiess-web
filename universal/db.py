import sys
from pathlib import Path
sys.path.append(Path(__file__).resolve().parents[1])

import aiosqlite
import config
import sqlite3

db = None

async def connect():
    global db
    if not db:
        db = await aiosqlite.connect(config.db_file)
    return db


async def query(q):
    global db
    
    if not db:
        await connect()
    if type(q) is str:
        cursor = await db.execute(q)
    elif type(q) in [list, tuple]:
        cursor = await db.execute(q[0], q[1])
    
    async_res = await cursor.fetchall()
    await db.commit()
    return async_res


def create_db():
    db = sqlite3.connect(config.db_file)
    db.execute("""CREATE TABLE hooks (
        hook_url text NOT NULL,
        webhook_id text NOT NULL,
        webhook_token text NOT NULL,
        mode integer,
        push_status integer,
        status text,
        uid text
    ); """)
    db.commit()
    db.close()
