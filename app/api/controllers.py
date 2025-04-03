import os
import tempfile
from app.core.document_analyzer import DocumentAnalyzer
from app.core.extractors.pdf_extractor import PDFExtractor
from app.core.extractors.image_extractor import ImageExtractor
from app.core.extractors.csv_extractor import CSVExtractor
from config.config import BANK_TEMPLATES

def process_statement(file_bytes: bytes, filename: str):
    """
    Process the uploaded bank statement file.
    Steps:
      1. Save file to a temporary location.
      2. Identify document format and structure.
      3. Choose the appropriate extractor.
      4. Extract metadata and transactions.
      5. (Optional) Validate and normalize data.
      6. Return extracted data.
    """
    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # Initialize document analyzer with bank templates
        analyzer = DocumentAnalyzer(BANK_TEMPLATES)
        strategy = analyzer.get_extraction_strategy(tmp_path)

        file_format = strategy["file_format"]
        extractor = None

        if file_format.name.lower() == "pdf":
            # Use bank template if detected
            template = strategy["structure"].get("detected_template")
            extractor = PDFExtractor(template=template)
        elif file_format.name.lower() == "image":
            extractor = ImageExtractor()
        elif file_format.name.lower() in ["csv", "excel"]:
            template = strategy["structure"].get("detected_template")
            extractor = CSVExtractor(template=template)
        else:
            raise Exception("Unsupported file format")

        # Extract data
        extracted_data = extractor.extract(tmp_path)

        # Optionally add parsing, normalization, and validation here
        # e.g., using transaction_parser, normalizer, and validator modules

        return extracted_data
    finally:
        # Clean up temporary file
        os.remove(tmp_path)
