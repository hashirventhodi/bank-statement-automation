import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import tempfile
import random
from datetime import datetime, timedelta

from app.core.tasks import StatementProcessor
from app.core.extractors.pdf_extractor import PDFExtractor
from app.core.parsers.transaction_parser import TransactionParser
from app.core.normalizer import TransactionNormalizer
from app.models.statement import Statement, StatementFormat, ProcessingStatus
from app.database.repositories.statement_repository import StatementRepository
from app.database.repositories.transaction_repository import TransactionRepository

def generate_test_statement(size_kb: int) -> Path:
    """Generate a test statement file of specified size."""
    content = b"%PDF-1.4\n"
    # Add dummy content to reach desired size
    content += b"0" * (size_kb * 1024 - len(content))
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(content)
        return Path(f.name)

def generate_test_transactions(count: int) -> list:
    """Generate test transaction data."""
    transactions = []
    base_date = datetime(2025, 1, 1)
    balance = 10000.0
    
    for i in range(count):
        amount = round(random.uniform(10, 1000), 2)
        is_credit = random.choice([True, False])
        
        if is_credit:
            balance += amount
        else:
            balance -= amount
        
        transactions.append({
            "date": (base_date + timedelta(days=i)).strftime("%d/%m/%Y"),
            "description": f"Test Transaction {i+1}",
            "amount": amount,
            "transaction_type": "credit" if is_credit else "debit",
            "balance": round(balance, 2)
        })
    
    return transactions

@pytest.mark.performance
def test_extraction_performance():
    """Test PDF extraction performance with different file sizes."""
    file_sizes = [100, 500, 1000]  # KB
    results = []
    
    for size in file_sizes:
        test_file = generate_test_statement(size)
        extractor = PDFExtractor()
        
        start_time = time.time()
        extractor.extract(str(test_file))
        duration = time.time() - start_time
        
        results.append({
            "file_size_kb": size,
            "duration_seconds": duration
        })
        
        os.unlink(test_file)
    
    # Assert reasonable performance
    for result in results:
        # Expect processing time to be less than 2 seconds per 100KB
        expected_max_duration = (result["file_size_kb"] / 100) * 2
        assert result["duration_seconds"] < expected_max_duration

@pytest.mark.performance
def test_parser_performance():
    """Test transaction parser performance with different batch sizes."""
    batch_sizes = [100, 1000, 5000]
    results = []
    
    parser = TransactionParser()
    
    for size in batch_sizes:
        transactions = generate_test_transactions(size)
        
        start_time = time.time()
        parser.parse(transactions)
        duration = time.time() - start_time
        
        results.append({
            "batch_size": size,
            "duration_seconds": duration
        })
    
    # Assert reasonable performance
    for result in results:
        # Expect processing time to be less than 0.1 seconds per 100 transactions
        expected_max_duration = (result["batch_size"] / 100) * 0.1
        assert result["duration_seconds"] < expected_max_duration

@pytest.mark.performance
def test_concurrent_processing(db_session, test_account):
    """Test concurrent statement processing performance."""
    num_statements = 5
    statements = []
    
    # Create test statements
    for i in range(num_statements):
        test_file = generate_test_statement(100)  # 100KB each
        statement = Statement(
            account_id=test_account.id,
            bank_name="Test Bank",
            file_name=f"test_statement_{i+1}.pdf",
            file_path=str(test_file),
            file_format=StatementFormat.PDF,
            processing_status=ProcessingStatus.PENDING
        )
        db_session.add(statement)
        db_session.commit()
        statements.append(statement)
    
    # Process statements concurrently
    processor = StatementProcessor(max_workers=3)
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(processor._process_statement, statement, db_session)
            for statement in statements
        ]
        
        # Wait for all to complete
        for future in as_completed(futures):
            future.result()
    
    duration = time.time() - start_time
    
    # Clean up
    for statement in statements:
        try:
            os.unlink(statement.file_path)
        except:
            pass
    
    # Assert reasonable performance
    # Expect concurrent processing to be faster than sequential
    # Allow 5 seconds per statement when running concurrently
    assert duration < (num_statements * 5)

@pytest.mark.performance
def test_database_performance(db_session, test_account):
    """Test database operation performance."""
    # Test batch insert performance
    batch_sizes = [100, 1000, 5000]
    results = []
    
    for size in batch_sizes:
        # Generate test data
        statement = Statement(
            account_id=test_account.id,
            bank_name="Test Bank",
            file_name="test_statement.pdf",
            file_path="/tmp/test.pdf",
            file_format=StatementFormat.PDF,
            processing_status=ProcessingStatus.PENDING
        )
        db_session.add(statement)
        db_session.commit()
        
        transactions = generate_test_transactions(size)
        tx_repo = TransactionRepository(db_session)
        
        start_time = time.time()
        # Convert to Transaction objects
        tx_objects = [
            Transaction(
                statement_id=statement.id,
                **tx
            ) for tx in transactions
        ]
        tx_repo.bulk_create(tx_objects)
        duration = time.time() - start_time
        
        results.append({
            "batch_size": size,
            "duration_seconds": duration
        })
        
        # Cleanup
        db_session.query(Transaction).filter_by(statement_id=statement.id).delete()
        db_session.delete(statement)
        db_session.commit()
    
    # Assert reasonable performance
    for result in results:
        # Expect batch insert to be less than 0.5 seconds per 1000 records
        expected_max_duration = (result["batch_size"] / 1000) * 0.5
        assert result["duration_seconds"] < expected_max_duration

@pytest.mark.performance
def test_memory_usage():
    """Test memory usage during large file processing."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    base_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Process a large file
    test_file = generate_test_statement(5000)  # 5MB file
    extractor = PDFExtractor()
    normalizer = TransactionNormalizer()
    parser = TransactionParser()
    
    # Extract and process
    extracted_data = extractor.extract(str(test_file))
    parsed_data = parser.parse(extracted_data["transactions"])
    normalized_data = normalizer.normalize_transactions(parsed_data)
    
    # Check memory usage
    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = peak_memory - base_memory
    
    # Clean up
    os.unlink(test_file)
    
    # Assert reasonable memory usage
    # Expect memory usage to increase by no more than 100MB for a 5MB file
    assert memory_increase < 100

@pytest.mark.performance
def test_error_handling_performance():
    """Test performance of error handling under load."""
    # Test with malformed data
    parser = TransactionParser()
    normalizer = TransactionNormalizer()
    
    # Generate mix of valid and invalid transactions
    transactions = []
    for i in range(1000):
        if i % 3 == 0:  # Every third transaction is invalid
            tx = {
                "date": "invalid_date",
                "description": "Invalid Transaction",
                "amount": "not_a_number"
            }
        else:
            tx = {
                "date": "2025-04-03",
                "description": f"Valid Transaction {i}",
                "amount": 100.00,
                "transaction_type": "credit"
            }
        transactions.append(tx)
    
    start_time = time.time()
    
    # Process transactions with error handling
    try:
        parsed_data = parser.parse(transactions)
        normalized_data = normalizer.normalize_transactions(parsed_data)
    except Exception as e:
        assert False, f"Error handling failed: {str(e)}"
    
    duration = time.time() - start_time
    
    # Assert reasonable performance even with errors
    # Expect processing time to be less than 2 seconds for 1000 transactions with errors
    assert duration < 2