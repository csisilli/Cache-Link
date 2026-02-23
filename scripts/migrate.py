#!/usr/bin/env python
"""
Database Migration and Initialization Script

Manages database schema creation, updates, and maintenance.

This script provides commands for:
1. Creating initial database tables (create)
2. Initializing Alembic for version control (init)
3. Running migrations (upgrade, downgrade)
4. Checking database status (status)
5. Resetting database (reset - WARNING: destructive)

Two Approaches Supported:
1. Direct SQLAlchemy: Create tables directly from ORM models
   - Fastest for initial setup
   - No version history
   - Used: python migrate.py create

2. Alembic Migrations: Version-controlled schema changes
   - Supports rollback
   - Tracks all changes
   - Used: python migrate.py upgrade/downgrade

Database Initialization Flow:
1. First time: Run 'python migrate.py create' to bootstrap
2. Development: Modify models, manually create migration files
3. Production: Use 'python migrate.py upgrade' for schema changes

Connection String:
- Configured via DATABASE_URL in config.config
- Format: mysql+pymysql://user:password@host/database
- Format: postgresql://user:password@host/database

Usage Examples:
    python migrate.py create              # Initial setup
    python migrate.py status              # Check database
    python migrate.py reset               # Clear all data
    python migrate.py upgrade             # Apply migrations
    python migrate.py downgrade base      # Revert all changes
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect
from app.models import Base, init_db
from config.config import settings
import logging

# Configure logging for migration operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables():
    """
    Create all database tables directly from SQLAlchemy models.
    
    Uses SQLAlchemy ORM metadata to create schema directly.
    This is the fastest way to initialize the database for development.
    
    Tables created:
    - urls: Core URL mappings (indexed for fast lookups)
    - clicks: Click analytics records (denormalized)
    - rate_limits: Rate limiting state per IP (token bucket)
    
    Process:
    1. Connect to database
    2. Create tables if they don't exist (idempotent)
    3. Verify tables were created
    4. Log table names and columns
    
    Returns:
        bool: True if successful, False on error
        
    Examples:
        >>> create_tables()
        True
        
    Note:
        Idempotent - safe to run multiple times
        Won't drop existing tables
    """
    try:
        logger.info(f"Creating tables in database...")
        engine, _ = init_db(settings.DATABASE_URL)
        
        # Create all tables defined in models.py
        # Base.metadata contains all ORM model definitions
        Base.metadata.create_all(bind=engine)
        
        # Verify tables were created by introspecting database
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"Successfully created tables: {', '.join(tables)}")
        logger.info("Database migration complete!")
        
        engine.dispose()
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False


def init_alembic():
    """
    Initialize Alembic for database version control.
    
    Alembic is a lightweight database migration tool for SQLAlchemy.
    Enables:
    - Version-controlled schema changes
    - Upgrade/downgrade migrations
    - Rollback capability
    - Team collaboration on schema
    
    Creates directory structure:
    - alembic/versions/: Migration scripts
    - alembic/env.py: Migration environment config
    - alembic.ini: Main config file
    
    Returns:
        bool: True if successful, False on error
        
    Note:
        Only needed if using Alembic for migrations
        Direct create_tables() works without this
    """
    try:
        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        alembic_cfg.set_main_option("script_location", "alembic")
        
        if not os.path.exists("alembic"):
            logger.info("Initializing Alembic...")
            command.init(alembic_cfg, "alembic")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing Alembic: {e}")
        return False


def upgrade_database():
    """
    Run database schema upgrades (apply migrations).
    
    Reads migration files in alembic/versions/ and applies them to database.
    Migrations are applied in order to get to HEAD (latest) revision.
    
    Process:
    1. Read all migration files
    2. Detect current revision
    3. Execute all migrations between current and HEAD
    4. Update schema
    
    Returns:
        bool: True if successful, False on error
        
    Used for:
    - Initial schema setup via migrations
    - Applying schema changes in production
    - Syncing database schema across environments
    """
    try:
        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        alembic_cfg.set_main_option("script_location", "alembic")
        
        logger.info("Running database upgrades...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database upgrade complete!")
        return True
    except Exception as e:
        logger.error(f"Error upgrading database: {e}")
        return False


def downgrade_database(revision="base"):
    """
    Downgrade database schema to a specific revision.
    
    Rolls back migration changes to a previous state.
    Enables recovery from failed migrations or schema rollback.
    
    Args:
        revision: Target revision (default: "base" = initial state)
                 Examples:
                 - "base": Empty database (revert all migrations)
                 - "abc123def456": Specific migration hash
                 - "-1": One migration back from current
        
    Returns:
        bool: True if successful, False on error
        
    WARNING:
    - May cause data loss (dropped columns, etc.)
    - Should be tested in non-production first
    - Requires backup of important data
    
    Examples:
        >>> downgrade_database()  # Revert all
        >>> downgrade_database("-1")  # Back one version
    """
    try:
        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        alembic_cfg.set_main_option("script_location", "alembic")
        
        logger.info(f"Downgrading database to {revision}...")
        command.downgrade(alembic_cfg, revision)
        logger.info("Database downgrade complete!")
        return True
    except Exception as e:
        logger.error(f"Error downgrading database: {e}")
        return False


def check_database_status():
    """
    Check current database status and schema.
    
    Introspects database to show:
    - Number of tables
    - Table names
    - Number of columns per table
    - Overall schema structure
    
    Returns:
        bool: True if successful, False on error
        
    Useful for:
    - Verifying database initialization
    - Debugging schema issues
    - Understanding current state
    
    Examples:
        >>> check_database_status()
        Database Status:
          Tables: 3
            - urls (9 columns)
            - clicks (6 columns)
            - rate_limits (4 columns)
    """
    try:
        engine, _ = init_db(settings.DATABASE_URL)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info("Database Status:")
        logger.info(f"  Tables: {len(tables)}")
        for table in tables:
            columns = inspector.get_columns(table)
            logger.info(f"    - {table} ({len(columns)} columns)")
        
        engine.dispose()
        return True
    except Exception as e:
        logger.error(f"Error checking database status: {e}")
        return False


def reset_database():
    """
    Reset entire database (DROP all tables and recreate).
    
    DESTRUCTIVE OPERATION:
    - Deletes ALL data
    - Removes all tables
    - Recreates empty schema
    - Requires user confirmation
    
    Use Cases:
    - Development: Clear test data
    - Testing: Reset to clean state
    - Debugging: Remove corrupted data
    
    Returns:
        bool: True if reset successful, False if cancelled or error
        
    WARNING:
    - Requires typing 'yes' to confirm
    - No recovery possible once executed
    - Backup data before running
    - Never run in production without backups
    
    Examples:
        >>> reset_database()  # Will prompt for confirmation
        Resetting database - this will DELETE all data!
        Are you sure? Type 'yes' to continue: yes
        [... reset proceeds ...]
    """
    try:
        logger.warning("Resetting database - this will DELETE all data!")
        confirm = input("Are you sure? Type 'yes' to continue: ")
        
        if confirm.lower() != "yes":
            logger.info("Reset cancelled")
            return False
        
        engine, _ = init_db(settings.DATABASE_URL)
        logger.info("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        
        logger.info("Recreating tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database reset complete!")
        engine.dispose()
        return True
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False


def main():
    """
    Main entry point - parse commands and execute migrations.
    
    Handles command-line arguments and routes to appropriate function.
    Provides help if no command or invalid command provided.
    
    Returns:
        int: Exit code (0 = success, 1 = error)
    """
    if len(sys.argv) < 2:
        logger.info("Usage: python migrate.py [command]")
        logger.info("Commands:")
        logger.info("  create      - Create all database tables from models")
        logger.info("  init        - Initialize Alembic migration system")
        logger.info("  upgrade     - Apply database migrations (upgrade to HEAD)")
        logger.info("  downgrade   - Rollback migrations to revision (def: base)")
        logger.info("  status      - Check database status and schema")
        logger.info("  reset       - Reset database (DELETE all data!)")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "create":
        success = create_tables()
    elif command == "init":
        success = init_alembic()
    elif command == "upgrade":
        success = upgrade_database()
    elif command == "downgrade":
        # Support optional revision argument: migrate.py downgrade base
        revision = sys.argv[2] if len(sys.argv) > 2 else "base"
        success = downgrade_database(revision)
    elif command == "status":
        success = check_database_status()
    elif command == "reset":
        success = reset_database()
    else:
        logger.error(f"Unknown command: {command}")
        return 1
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
