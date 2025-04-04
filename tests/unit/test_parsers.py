import pytest
from datetime import datetime
from app.core.parsers.transaction_parser import TransactionParser
from app.core.parsers.ml_parser import MLParser
from app.models.transaction import TransactionType

@pytest.fixture
def sample_transactions():
    """Sample transaction data for testing."""
    return [
        {
            "date": "2025-04-03",
            "description": "Test Credit",
            "credit": 100.00,
            "debit": None,
            "balance": 1000.00
        },
        {
            "date": "2025-04-03",
            "description": "Test Debit",
            "credit": None,
            "debit": 50.00,
            "balance": 950.00
        }
    ]

def test_transaction_parser_init():
    """Test parser initialization."""
    parser = TransactionParser()
    assert parser is not None
    assert parser.template is None
    
    template = {"test": "template"}
    parser = TransactionParser(template=template)
    assert parser.template == template

def test_transaction_parser_parse(sample_transactions):
    """Test basic transaction parsing."""
    parser = TransactionParser()
    result = parser.parse(sample_transactions)
    
    assert len(result) == 2
    
    # Test credit transaction
    credit_tx = result[0]
    assert credit_tx["amount"] == 100.00
    assert credit_tx["transaction_type"] == TransactionType.CREDIT
    assert credit_tx["balance"] == 1000.00
    
    # Test debit transaction
    debit_tx = result[1]
    assert debit_tx["amount"] == 50.00
    assert debit_tx["transaction_type"] == TransactionType.DEBIT
    assert debit_tx["balance"] == 950.00

def test_ml_parser_training():
    """Test ML parser training."""
    parser = MLParser()
    training_data = [
        {
            "raw_description": "SALARY CREDIT",
            "bank_category": "SALARY"
        },
        {
            "raw_description": "ATM WITHDRAWAL",
            "bank_category": "ATM"
        }
    ]
    
    parser.train(training_data)
    assert parser.is_trained == True
    
    # Test prediction
    test_tx = {
        "date": "2025-04-03",
        "raw_description": "SALARY PAYMENT",
        "amount": 5000.00
    }
    
    result = parser.parse([test_tx])
    assert len(result) == 1
    assert result[0]["bank_category"] == "SALARY"
    assert isinstance(result[0]["confidence_score"], float)