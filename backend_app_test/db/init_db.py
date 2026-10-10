"""
PostgreSQL Schema Initializer & Verification Script
"""

import asyncio
import logging
from sqlalchemy import text
from backend_app_test.db.session import engine, Base
from backend_app_test.db import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def initialize_and_verify_database():
    logger.info("Connecting to PostgreSQL 16 database...")
    
    async with engine.begin() as conn:
        # Create all tables defined in models
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("Verifying tables in PostgreSQL schema...")
    
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        )
        tables = [row[0] for row in result.fetchall()]
        expected_tables = ["users", "repositories", "scans", "findings", "reports"]
        
        for t in expected_tables:
            if t in tables:
                logger.info(f"  [OK] Table '{t}' verified.")
            else:
                logger.error(f"  [FAIL] Missing table: '{t}'")
                raise RuntimeError(f"Database schema incomplete: missing '{t}'")

    logger.info("Database initialized successfully according to DDS v1.0!")


if __name__ == "__main__":
    asyncio.run(initialize_and_verify_database())