import os
import logging
from dotenv import load_dotenv
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Get Database URL
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

logger.info("Initializing database connection...")

# Pooled connections. Previously NullPool, which opened a fresh TCP+TLS
# connection to Neon for every single query (~50-100ms of blocked event loop
# each). pool_pre_ping discards connections the server dropped, and
# pool_recycle stays under Neon's idle timeout.
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "280")),
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session() -> Session:
    """
    Get a new database session.

    Caller owns the session and must close it. Prefer session_scope() for new
    code.

    Returns:
        Session: SQLAlchemy session object
    """
    return SessionLocal()


@contextmanager
def session_scope():
    """
    Session context manager that commits on success and rolls back on error.

    Usage:
        with session_scope() as session:
            session.add(obj)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db(recreate_tables=False):
    """
    Initialize the database by creating all tables defined in the models.
    This function should be called once when the application starts.
    Handles connection errors gracefully.
    
    Args:
        recreate_tables: If True, drops existing tables before creating new ones
    """
    try:
        # Import every model module before create_all so its table is in the
        # shared metadata. A model that is never imported is never created.
        from models.base import Base
        from models import agent as _agent_models  # noqa: F401
        from models import run as _run_models  # noqa: F401

        # Test connection first
        logger.info("Testing database connection...")
        with engine.connect() as conn:
            logger.info("[OK] Database connection successful")
        
        if recreate_tables:
            logger.warning("Dropping existing tables...")
            Base.metadata.drop_all(bind=engine)
            logger.warning("[OK] Tables dropped")
            Base.metadata.create_all(bind=engine)
            logger.info("[OK] Tables recreated")
            return

        # Schema is owned by Alembic. create_all() cannot ALTER existing tables,
        # so relying on it would silently skip column changes and drift from the
        # migration history. Run: python -m alembic upgrade head
        logger.info("[OK] Database reachable (schema managed by Alembic)")
        
    except OperationalError as e:
        logger.error(f"[ERROR] Database connection failed: {str(e)}")
        logger.error("Make sure:")
        logger.error("  1. Your DATABASE_URL is correct in .env")
        logger.error("  2. The database host is reachable")
        logger.error("  3. Your network connection is working")
        logger.error("  4. Firewall is not blocking the connection")
        # Don't raise - let app continue, database operations will fail later
        
    except Exception as e:
        logger.error(f"[ERROR] Error initializing database: {str(e)}")
        logger.error("Please check your database configuration")