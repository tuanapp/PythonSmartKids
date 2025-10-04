"""
Database Initializer - Creates databases if they don't exist
"""
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """Utility class to create databases if they don't exist."""
    
    @staticmethod
    def ensure_postgres_database_exists(connection_params: Dict[str, Any]) -> bool:
        """
        Ensure that the PostgreSQL database exists, create it if it doesn't.
        
        Args:
            connection_params: Dictionary with connection parameters
                - dbname: Target database name
                - user: Database username  
                - password: Database password
                - host: Database host
                - sslmode: SSL mode (default: require)
                
        Returns:
            bool: True if database exists or was created successfully
        """
        dbname = connection_params.get('dbname')
        user = connection_params.get('user')
        password = connection_params.get('password')
        host = connection_params.get('host')
        sslmode = connection_params.get('sslmode', 'require')
        
        # First try to connect to the target database
        try:
            test_conn = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                sslmode=sslmode
            )
            test_conn.close()
            logger.info(f"Database '{dbname}' already exists")
            return True
            
        except psycopg2.OperationalError as e:
            error_msg = str(e).lower()
            
            # Check if error is due to database not existing
            if 'does not exist' in error_msg or f'database "{dbname}" does not exist' in error_msg:
                logger.info(f"Database '{dbname}' does not exist, attempting to create it...")
                
                try:
                    # Connect to default 'postgres' database to create the target database
                    admin_conn = psycopg2.connect(
                        dbname='postgres',  # Default database that should always exist
                        user=user,
                        password=password,
                        host=host,
                        sslmode=sslmode
                    )
                    admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                    
                    cursor = admin_conn.cursor()
                    
                    # Check if database already exists (race condition protection)
                    cursor.execute(
                        "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
                        (dbname,)
                    )
                    
                    if cursor.fetchone():
                        logger.info(f"Database '{dbname}' already exists (created by another process)")
                        admin_conn.close()
                        return True
                    
                    # Create the database
                    cursor.execute(f'CREATE DATABASE "{dbname}"')
                    logger.info(f"Successfully created database '{dbname}'")
                    
                    admin_conn.close()
                    
                    # Verify the database was created successfully
                    test_conn = psycopg2.connect(
                        dbname=dbname,
                        user=user,
                        password=password,
                        host=host,
                        sslmode=sslmode
                    )
                    test_conn.close()
                    
                    return True
                    
                except psycopg2.Error as create_error:
                    logger.error(f"Failed to create database '{dbname}': {create_error}")
                    return False
                    
            else:
                # Different error (authentication, host unreachable, etc.)
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                return False
                
    @staticmethod 
    def create_user_if_not_exists(connection_params: Dict[str, Any]) -> bool:
        """
        Create PostgreSQL user if it doesn't exist.
        
        Args:
            connection_params: Dictionary with connection parameters
                
        Returns:
            bool: True if user exists or was created successfully
        """
        dbname = connection_params.get('dbname')
        user = connection_params.get('user')
        password = connection_params.get('password')
        host = connection_params.get('host')
        sslmode = connection_params.get('sslmode', 'require')
        
        try:
            # Connect as superuser or with an existing user to create new user
            admin_conn = psycopg2.connect(
                dbname='postgres',
                user='postgres',  # Assuming postgres superuser exists
                password='postgres',  # Default password for development
                host=host,
                sslmode=sslmode
            )
            admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = admin_conn.cursor()
            
            # Check if user exists
            cursor.execute(
                "SELECT 1 FROM pg_catalog.pg_user WHERE usename = %s",
                (user,)
            )
            
            if cursor.fetchone():
                logger.info(f"User '{user}' already exists")
                admin_conn.close()
                return True
            
            # Create user with login privileges
            cursor.execute(
                f"CREATE USER \"{user}\" WITH LOGIN PASSWORD %s CREATEDB",
                (password,)
            )
            
            logger.info(f"Successfully created user '{user}'")
            admin_conn.close()
            return True
            
        except psycopg2.Error as e:
            logger.warning(f"Could not create user '{user}': {e}")
            # This is not critical - user might already exist or we might not have permissions
            return False