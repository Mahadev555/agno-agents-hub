import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Get Database URL
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

logger.info("Initializing database connection...")

# Create SQLAlchemy engine
# NullPool is used to avoid connection pooling issues with psycopg2
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before using them
    poolclass=NullPool  # Don't pool connections
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session() -> Session:
    """
    Get a new database session.
    
    Returns:
        Session: SQLAlchemy session object
        
    Raises:
        OperationalError: If database connection fails
    """
    return SessionLocal()

def init_db(recreate_tables=False):
    """
    Initialize the database by creating all tables defined in the models.
    This function should be called once when the application starts.
    Handles connection errors gracefully.
    
    Args:
        recreate_tables: If True, drops existing tables before creating new ones
    """
    try:
        from models.agent import Base
        
        # Test connection first
        logger.info("Testing database connection...")
        with engine.connect() as conn:
            logger.info("[OK] Database connection successful")
        
        # Drop existing tables if requested (useful for schema changes)
        if recreate_tables:
            logger.info("Dropping existing tables...")
            Base.metadata.drop_all(bind=engine)
            logger.info("[OK] Tables dropped")
        
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("[OK] Database initialized successfully")
        
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