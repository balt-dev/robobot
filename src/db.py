import re

import asqlite


class Database:
    conn: asqlite.Connection
    bot: None

    def __init__(self, bot):
        self.bot = bot

    async def connect(self, db: str):
        self.conn = await asqlite.connect(db)

        def regexp(pattern, string):
            return bool(re.search(pattern, string))
        self.conn.get_connection().create_function('regexp', 2, regexp)
        await self.create_tables()

    async def close(self):
        await self.conn.close()

    async def create_tables(self):
        async with self.conn.cursor() as cur:
            await cur.execute("""
            CREATE TABLE IF NOT EXISTS tiles (
                name TEXT PRIMARY KEY ASC NOT NULL UNIQUE,
                color TEXT NOT NULL DEFAULT "0,3",
                sprite TEXT NOT NULL,
                layer INTEGER,
                painted INTEGER
            ) WITHOUT ROWID;
            """)
            await cur.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                name TEXT NOT NULL,
                author TEXT,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                palette TEXT NOT NULL DEFAULT "default",
                background_sprite TEXT
            );
            """)