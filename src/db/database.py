"""
database.py - Async database engine
Provides the SQLAlchemy async engine used across the application.
No ORM - all queries are written in raw SQL.
"""

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


class Database:
    """
    Manages the async database connection lifecycle.
    Initialized once at application startup and shared across services.
    """

    def __init__(self, url):
        self._engine = create_async_engine(url, echo=False)

    def connection(self):
        """Returns a new async connection context manager."""
        return self._engine.connect()

    async def create_tables(self):
        """Creates the messages table if it does not already exist."""
        async with self._engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id VARCHAR PRIMARY KEY,
                    content VARCHAR NOT NULL,
                    sender_name VARCHAR NOT NULL,
                    sender_email VARCHAR NOT NULL,
                    sender_phone VARCHAR NOT NULL,
                    destination VARCHAR NOT NULL,
                    customer_type VARCHAR NOT NULL,
                    status VARCHAR NOT NULL DEFAULT 'Received',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
