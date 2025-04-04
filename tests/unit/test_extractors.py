import pytest
from datetime import datetime
from app.core.extractors.pdf_extractor import PDFExtractor
from app.core.extractors.csv_extractor import CSVExtractor
from app.models.statement import StatementFormat

def test_pdf_extractor_init():
    """Test PDF extractor initialization."""
    extractor = PDFExtractor()
    assert extractor is not None
    assert extractor.template is None
    
    template = {"test": "template"}
    extractor = PDFExtractor(template=template)
    assert extractor.template == template

def test_pdf_extractor_extract(test_pdf_file):
    """Test PDF data extraction."""
    extractor = PDFExtractor()
    result = extractor.extract(str(test_pdf_file))
    
    assert isinstance(result, dict)
    assert "metadata" in result
    assert "transactions" in result

def test_csv_extractor_extract(test_csv_file):
    """Test CSV data extraction."""
    extractor = CSVExtractor()
    result = extractor.extract(str(test_csv_file))
    
    assert isinstance(result, dict)
    assert "metadata" in result
    assert "transactions" in result
    assert len(result["transactions"]) > 0
    
    tx = result["transactions"][0]
    assert isinstance(tx, dict)
    assert "date" in tx
    assert "description" in tx
    assert "amount" in tx

def test_csv_extractor_with_template(test_csv_file):
    """Test CSV extraction with template."""
    template = {
        "field_mapping": {
            "date": "Date",
            "description": "Description",
            "debit": "Debit",
            "credit": "Credit",
            "balance": "Balance"
        }
    }
    
    extractor = CSVExtractor(template=template)
    result = extractor.extract(str(test_csv_file))
    
    assert len(result["transactions"]) > 0
    tx = result["transactions"][0]
    assert tx["description"] == "Test"
    assert tx["amount"] == 100.00