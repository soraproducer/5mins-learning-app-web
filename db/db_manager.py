#!/usr/bin/env python3
import subprocess
import asyncpg
import uuid
import asyncio
from argparse import ArgumentParser
from pathlib import Path
import sys

# Add project root to PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base, engine
from app.core.config import settings
# Import all models to ensure they're registered with Base.metadata
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message

class DatabaseManager:
    """Database management operations"""
    
    @staticmethod
    async def recreate_database():
        """Drop and recreate the database"""
        print("🔄 Recreating database...")
        db_name = settings.DATABASE_URL.split("/")[-1]
        subprocess.run(["dropdb", "-U", "sorap", db_name], check=True)
        subprocess.run(["createdb", "-U", "sorap", db_name], check=True)
        print(f"✅ Database '{db_name}' recreated")

    @staticmethod
    async def create_tables():
        """Create all database tables"""
        print("🛠️  Creating tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables created")

    @staticmethod
    async def create_test_user():
        """Create test user with fixed UUID"""
        print("👤 Creating test user...")
        # Strip SQLAlchemy dialect from connection URL
        pg_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
        conn = None
        try:
            conn = await asyncpg.connect(pg_url)
            await conn.execute(f'''
                INSERT INTO users 
                    (user_id, user_name, created_at, updated_at)
                VALUES
                    ($1, $2, NOW(), NOW())
            ''', uuid.UUID('00000000-0000-0000-0000-000000000000'), 'Test User')
            print("✅ Test user created")
        finally:
            if conn:
                await conn.close()

async def main():
    parser = ArgumentParser(description="Database management utility")
    parser.add_argument("--recreate", action="store_true", help="Recreate database")
    parser.add_argument("--tables", action="store_true", help="Create tables")
    parser.add_argument("--test-user", action="store_true", help="Create test user")
    parser.add_argument("--all", action="store_true", 
                      help="Full reset (recreate + tables + test user)")
    
    args = parser.parse_args()
    
    if args.all:
        # Execute in proper order with error handling
        try:
            await DatabaseManager.recreate_database()
            await DatabaseManager.create_tables()
            await DatabaseManager.create_test_user()
            print("\n✅ Database reset completed successfully")
        except Exception as e:
            print(f"\n❌ Error during database reset: {e}")
        return
    
    if args.recreate:
        await DatabaseManager.recreate_database()
    if args.tables:
        await DatabaseManager.create_tables()
    if args.test_user:
        await DatabaseManager.create_test_user()

if __name__ == "__main__":
    asyncio.run(main())
