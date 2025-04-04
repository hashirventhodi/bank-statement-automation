import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import tempfile
from pathlib import Path

from app.database.db import Base
from app.models.account import Account
from app.models.statement import Statement, StatementFormat, ProcessingStatus
from app.models.transaction import Transaction, TransactionType, TransactionStatus

@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create new database session for a test."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    
    yield session
    
    session.rollback()
    session.close()

@pytest.fixture
def test_account(db_session):
    """Create test account."""
    account = Account(
        user_id=1,
        account_name="Test Account",
        account_number="1234567890",
        bank_name="Test Bank",
        bank_branch="Test Branch",
        ifsc_code="TEST0001",
        tally_ledger_name="Test Ledger"
    )
    db_session.add(account)
    db_session.commit()
    return account

@pytest.fixture
def test_statement(db_session, test_account):
    """Create test statement."""
    statement = Statement(
        account_id=test_account.id,
        bank_name="Test Bank",
        file_name="test_statement.pdf",
        file_path="/tmp/test_statement.pdf",
        file_format=StatementFormat.PDF,
        processing_status=ProcessingStatus.PENDING
    )
    db_session.add(statement)
    db_session.commit()
    return statement

@pytest.fixture
def test_transaction(db_session, test_statement):
    """Create test transaction."""
    transaction = Transaction(
        statement_id=test_statement.id,
        date="2025-04-03",
        description="Test Transaction",
        amount=100.00,
        transaction_type=TransactionType.CREDIT,
        balance=1000.00,
        status=TransactionStatus.PENDING
    )
    db_session.add(transaction)
    db_session.commit()
    return transaction

@pytest.fixture
def test_pdf_file():
    """Create test PDF file."""
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(content)
        return Path(f.name)

@pytest.fixture
def test_csv_file():
    """Create test CSV file."""
    content = "Date,Description,Debit,Credit,Balance\n2025-04-03,Test,100.00,,1000.00"
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        f.write(content.encode())
        return Path(f.name)

@pytest.fixture(autouse=True)
def cleanup_files(test_pdf_file, test_csv_file):
    """Clean up test files after tests."""
    yield
    for file in [test_pdf_file, test_csv_file]:
        try:
            os.unlink(file)
        except:
            pass