import os
import sys
import argparse
from datetime import datetime
from alembic import command
from alembic.config import Config

def get_alembic_config():
    """Get Alembic configuration."""
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    
    # Set SQLAlchemy URL from environment
    from dotenv import load_dotenv
    load_dotenv()
    
    db_url = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    config.set_main_option("sqlalchemy.url", db_url)
    
    return config

def create_migration(message):
    """Create a new migration."""
    config = get_alembic_config()
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    command.revision(config, message=message, autogenerate=True)

def upgrade_database(revision='head'):
    """Upgrade database to specified revision."""
    config = get_alembic_config()
    command.upgrade(config, revision)

def downgrade_database(revision='-1'):
    """Downgrade database to specified revision."""
    config = get_alembic_config()
    command.downgrade(config, revision)

def show_history():
    """Show migration history."""
    config = get_alembic_config()
    command.history(config)

def show_current():
    """Show current revision."""
    config = get_alembic_config()
    command.current(config)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database migration script")
    parser.add_argument(
        'action',
        choices=['create', 'upgrade', 'downgrade', 'history', 'current'],
        help='Migration action to perform'
    )
    parser.add_argument(
        '--message', '-m',
        help='Migration message (required for create)'
    )
    parser.add_argument(
        '--revision', '-r',
        help='Revision for upgrade/downgrade (default: head/-1)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.action == 'create':
            if not args.message:
                parser.error("--message is required for create action")
            create_migration(args.message)
            print(f"Created new migration with message: {args.message}")
            
        elif args.action == 'upgrade':
            upgrade_database(args.revision or 'head')
            print("Database upgraded successfully")
            
        elif args.action == 'downgrade':
            downgrade_database(args.revision or '-1')
            print("Database downgraded successfully")
            
        elif args.action == 'history':
            show_history()
            
        elif args.action == 'current':
            show_current()
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)