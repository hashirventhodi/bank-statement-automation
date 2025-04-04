import pytest
from pathlib import Path
from app.core.document_analyzer import DocumentAnalyzer
from app.core.extractors.pdf_extractor import PDFExtractor
from app.core.parsers.transaction_parser import TransactionParser
from app.core.normalizer import TransactionNormalizer
from app.core.validator import TransactionValidator
from app.models.statement import StatementFormat

def test_full_processing_pipeline(test_pdf_file):
    """Test entire processing pipeline."""
    # Initialize components
    analyzer = DocumentAnalyzer({})
    extractor = PDFExtractor()
    parser = TransactionParser()
    normalizer = TransactionNormalizer()
    validator = TransactionValidator()
    
    # Analyze document
    file_format = analyzer.identify_format(str(test_pdf_file))
    assert file_format in [StatementFormat.PDF, StatementFormat.IMAGE, StatementFormat.CSV, StatementFormat.EXCEL]
    
    analysis = analyzer.analyze_structure(str(test_pdf_file), file_format)
    assert isinstance(analysis, dict)
    
    # Extract data
    extracted_data = extractor.extract(str(test_pdf_file))
    assert isinstance(extracted_data, dict)
    assert "metadata" in extracted_data
    assert "transactions" in extracted_data
    
    # Parse transactions
    parsed_transactions = parser.parse(extracted_data["transactions"])
    assert isinstance(parsed_transactions, list)
    
    # Normalize transactions
    normalized_transactions = normalizer.normalize_transactions(parsed_transactions)
    assert isinstance(normalized_transactions, list)
    
    # Validate transactions
    validated_transactions = validator.validate_transactions(
        normalized_transactions,
        opening_balance=extracted_data["metadata"].get("opening_balance"),
        closing_balance=extracted_data["metadata"].get("closing_balance")
    )
    assert isinstance(validated_transactions, list)

def test_database_integration(db_session, test_account, test_statement, test_transaction):
    """Test database integration."""
    # Test relationships
    assert test_statement.account_id == test_account.id
    assert test_transaction.statement_id == test_statement.id
    
    # Test queries
    from app.database.repositories.statement_repository import StatementRepository
    from app.database.repositories.transaction_repository import TransactionRepository
    
    statement_repo = StatementRepository(db_session)
    transaction_repo = TransactionRepository(db_session)
    
    # Get statement
    statement = statement_repo.get(test_statement.id)
    assert statement is not None
    assert statement.id == test_statement.id
    
    # Get transactions
    transactions = transaction_repo.get_by_statement(test_statement.id)
    assert len(transactions) > 0
    assert transactions[0].id == test_transaction.id