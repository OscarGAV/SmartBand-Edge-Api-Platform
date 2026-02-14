import os
from typing import AsyncGenerator
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not found in environment variables. "
        "Please create a .env file with DATABASE_URL or set it as an environment variable."
    )

# Validate async driver
if not DATABASE_URL.startswith("postgresql+psycopg://"):
    raise ValueError(
        f"DATABASE_URL must use 'postgresql+psycopg://' driver for async support. "
        f"Current: {DATABASE_URL.split('://')[0] if '://' in DATABASE_URL else 'invalid'}"
    )

# Detect connection type (pooler vs direct)
is_pooler = ":6543/" in DATABASE_URL
connection_type = "Connection Pooler (port 6543)" if is_pooler else "Direct Connection (port 5432)"
logger.info(f"Database connection type: {connection_type}")

# Connection pool configuration - optimized for Supabase
if is_pooler:
    # Pooler: use smaller pool to avoid timeout
    pool_config = {
        "pool_size": 3,
        "max_overflow": 5,
        "pool_recycle": 300,  # 5 minutes
        "pool_timeout": 30,
        "pool_pre_ping": True,
    }
else:
    # Direct: can handle more connections
    pool_config = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 1800,  # 30 minutes
        "pool_timeout": 30,
        "pool_pre_ping": True,
    }

# Create async engine - NO connect_args needed for psycopg3
# The pooler handles SSL automatically
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    **pool_config
)


# Configure timezone on connection
@event.listens_for(engine.sync_engine, "connect")
def set_timezone(dbapi_conn, connection_record):
    """Set connection timezone to UTC"""
    try:
        cursor = dbapi_conn.cursor()
        cursor.execute("SET TIME ZONE 'UTC'")
        cursor.close()
    except Exception as e:
        logger.warning(f"Could not set timezone: {e}")


# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.
    Automatically handles session lifecycle.
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables (creates if not exist)"""
    from shared_context.domain.model.heart_rate_reading_model import Base

    logger.info("Initializing database...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


async def close_db():
    """Close database connections gracefully"""
    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("Database connections closed")