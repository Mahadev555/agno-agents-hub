import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_connection():
    """
    Creates and returns a connection to the PostgreSQL database.
    The connection parameters are read from DATABASE_URL environment variable.
    
    Returns:
        psycopg2.extensions.connection: A PostgreSQL database connection object
    
    Raises:
        psycopg2.Error: If connection to the database fails
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
            
        connection = psycopg2.connect(database_url)
        return connection
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        raise