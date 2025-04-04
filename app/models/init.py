# First import all model classes
from app.models.account import Account
from app.models.statement import Statement
from app.models.transaction import Transaction

# Then configure mappers or do any initialization needed
from sqlalchemy.orm import configure_mappers
configure_mappers()

# Export all models
__all__ = ['Account', 'Statement', 'Transaction']