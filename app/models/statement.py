from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
import enum
from app.database.db import Base

class StatementFormat(enum.Enum):
    PDF = "pdf"
    IMAGE = "image"
    CSV = "csv"
    EXCEL = "excel"
    UNKNOWN = "unknown"
    
class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"

class Statement(Base):
    __tablename__ = "statements"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    bank_name = Column(String, nullable=False)
    statement_period_start = Column(DateTime)
    statement_period_end = Column(DateTime)
    opening_balance = Column(Float)
    closing_balance = Column(Float)
    
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_format = Column(Enum(StatementFormat), nullable=False)
    file_size = Column(Integer)
    
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    processing_notes = Column(Text)
    parser_used = Column(String)
    extraction_duration = Column(Float)
    
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime)
    
    account = relationship("Account", back_populates="statements")
    transactions = relationship("Transaction", back_populates="statement", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "bank_name": self.bank_name,
            "statement_period_start": self.statement_period_start.isoformat() if self.statement_period_start else None,
            "statement_period_end": self.statement_period_end.isoformat() if self.statement_period_end else None,
            "opening_balance": self.opening_balance,
            "closing_balance": self.closing_balance,
            "file_name": self.file_name,
            "file_format": self.file_format.value,
            "processing_status": self.processing_status.value,
            "created_at": self.created_at.isoformat(),
            "transaction_count": len(self.transactions) if self.transactions else 0,
        }
