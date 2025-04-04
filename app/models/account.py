from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database.db import Base

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Account details
    user_id = Column(Integer, nullable=False)  # Foreign key to users table if you have one
    account_name = Column(String, nullable=False)
    account_number = Column(String)
    bank_name = Column(String, nullable=False)
    bank_branch = Column(String)
    ifsc_code = Column(String)  # For Indian banks
    
    # Integration details
    tally_ledger_name = Column(String)
    is_integrated = Column(Boolean, default=False)
    integration_settings = Column(String)  # JSON string for integration-specific settings
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - use strings for forward references
    statements = relationship("Statement", back_populates="account", cascade="all, delete-orphan")

    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_name": self.account_name,
            "account_number": self.account_number,
            "bank_name": self.bank_name,
            "bank_branch": self.bank_branch,
            "ifsc_code": self.ifsc_code,
            "tally_ledger_name": self.tally_ledger_name,
            "is_integrated": self.is_integrated,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }