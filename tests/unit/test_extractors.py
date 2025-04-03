import os
from app.core.extractors.pdf_extractor import PDFExtractor

def test_pdf_extraction():
    # Replace with the path to a sample PDF in your fixtures
    sample_pdf = os.path.join(os.getcwd(), "tests", "fixtures", "pdf_statements", "sample.pdf")
    extractor = PDFExtractor()
    data = extractor.extract(sample_pdf)
    assert "transactions" in data
