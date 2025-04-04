from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from app.models.transaction import Transaction
from app.utils.logger import logger
from app.models.statement import Statement

class TransactionRepository:
    """Repository for Transaction model operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, transaction: Transaction) -> Transaction:
        """Create a new transaction record."""
        try:
            self.db.add(transaction)
            self.db.commit()
            self.db.refresh(transaction)
            return transaction
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating transaction: {str(e)}")
            raise
    
    def bulk_create(self, transactions: List[Transaction]) -> List[Transaction]:
        """Create multiple transaction records."""
        try:
            self.db.bulk_save_objects(transactions)
            self.db.commit()
            return transactions
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error bulk creating transactions: {str(e)}")
            raise
    
    def get(self, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by ID."""
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    def get_by_statement(self, statement_id: int) -> List[Transaction]:
        """Get all transactions for a statement."""
        return self.db.query(Transaction)\
            .filter(Transaction.statement_id == statement_id)\
            .order_by(Transaction.date)\
            .all()
    
    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        account_id: Optional[int] = None
    ) -> List[Transaction]:
        """Get transactions within a date range."""
        query = self.db.query(Transaction)\
            .filter(and_(
                Transaction.date >= start_date,
                Transaction.date <= end_date
            ))
            
        if account_id:
            query = query.join(Transaction.statement)\
                .filter(Statement.account_id == account_id)
            
        return query.order_by(Transaction.date).all()
    
    def update(self, transaction: Transaction) -> Transaction:
        """Update a transaction record."""
        try:
            self.db.commit()
            self.db.refresh(transaction)
            return transaction
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating transaction: {str(e)}")
            raise
    
    def delete(self, transaction_id: int) -> bool:
        """Delete a transaction record."""
        try:
            transaction = self.get(transaction_id)
            if transaction:
                self.db.delete(transaction)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting transaction: {str(e)}")
            raise