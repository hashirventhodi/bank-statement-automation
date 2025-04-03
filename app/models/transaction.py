from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
import enum
from app.database.db import Base

class TransactionType(enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    
class TransactionStatus(enum.Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    VERIFIED = "verified"

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=False)
    
    date = Column(DateTime, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    balance = Column(Float)
    reference_number = Column(String)
    
    raw_description = Column(String)
    bank_category = Column(String)
    normalized_description = Column(String)
    
    confidence_score = Column(Float, default=1.0)
    extraction_method = Column(String)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    is_duplicate = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    statement = relationship("Statement", back_populates="transactions")
    
    def to_dict(self):
        return {
            "id": self.id,
            "statement_id": self.statement_id,
            "date": self.date.isoformat(),
            "description": self.description,
            "amount": self.amount,
            "transaction_type": self.transaction_type.value,
            "balance": self.balance,
            "reference_number": self.reference_number,
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
