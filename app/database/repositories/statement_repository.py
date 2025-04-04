from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.statement import Statement
from app.utils.logger import logger

class StatementRepository:
    """Repository for Statement model operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, statement: Statement) -> Statement:
        """Create a new statement record."""
        try:
            self.db.add(statement)
            self.db.commit()
            self.db.refresh(statement)
            return statement
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating statement: {str(e)}")
            raise
    
    def get(self, statement_id: int) -> Optional[Statement]:
        """Get statement by ID."""
        return self.db.query(Statement).filter(Statement.id == statement_id).first()
    
    def get_by_account(self, account_id: int) -> List[Statement]:
        """Get all statements for an account."""
        return self.db.query(Statement).filter(Statement.account_id == account_id).all()
    
    def update(self, statement: Statement) -> Statement:
        """Update a statement record."""
        try:
            self.db.commit()
            self.db.refresh(statement)
            return statement
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating statement: {str(e)}")
            raise
    
    def delete(self, statement_id: int) -> bool:
        """Delete a statement record."""
        try:
            statement = self.get(statement_id)
            if statement:
                self.db.delete(statement)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting statement: {str(e)}")
            raise