import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables FIRST
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import database functions AFTER loading .env
from shared_context.infrastructure.persistence.configuration.database_configuration import init_db, close_db

# Fix for Windows + psycopg async mode
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Application lifecycle: startup and shutdown
    """
    # Startup
    logger.info("=" * 60)
    logger.info("Starting Smart Band Edge Service")
    logger.info("=" * 60)

    try:
        await init_db()
        logger.info("Connected to PostgreSQL (Supabase)")
        logger.info("Server ready to accept connections")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("\n" + "=" * 60)
    logger.info("Shutting down Smart Band Edge Service")
    await close_db()
    logger.info("=" * 60 + "\n")


# Import controller after event loop policy is set
from core_context.interface.rest.controllers.heart_rate_controller import create_app

# Create app with lifespan
app = create_app(lifespan)

if __name__ == "__main__":
    logger.info("""
    ═══════════════════════════════════════════════════════════════════════
    Smart Band Edge Service for ESP32 IoT Device                      
    ═══════════════════════════════════════════════════════════════════════

    Architecture Layers:
    ✓ Domain Layer: Entities, Value Objects, Domain Events
    ✓ Application Layer: Commands, Queries, Handlers
    ✓ Infrastructure Layer: PostgreSQL + SQLAlchemy
    ✓ API Layer: HTTP Controllers, DTOs

    Database:
    • PostgreSQL (Supabase)
    • SQLAlchemy 2.0 ORM
    • Connection Pooling: Optimized for Supabase

    Endpoints:
    • POST /api/v1/health-monitoring/data-records
    • GET  /api/v1/health-monitoring/data-records/{id}/history
    • GET  /api/v1/health-monitoring/data-records/{id}/statistics
    • GET  /health

    Starting server on port: 8000
    Documentation: http://localhost:8000/docs
    """)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )