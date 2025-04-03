# Bank Statement Processor

This project automates bank statement processing and integrates with accounting software such as Tally. It supports various file formats (PDF, scanned images, CSV, Excel) and uses multiple extraction techniques (regex, OCR, ML) to extract, normalize, and validate transaction data.

## Features

- **Document Analysis:** Automatic format detection and structure analysis.
- **Extraction:** PDF extraction (using PyPDF2 and Tabula), OCR (using Tesseract and Google Vision), CSV/Excel parsing.
- **Parsing:** Transaction parsing with both rule‐based and ML-based options.
- **Normalization & Validation:** Consistent data formatting and error handling.
- **Integrations:** Ready for integration with accounting software like Tally.
- **Testing:** Includes unit, integration, and performance tests.

## Getting Started

1. Clone the repository.
2. Create a virtual environment and install dependencies:
   ```bash
   pip install -r requirements.txt
3. Configure your environment variables in the .env file.
4. Run database migrations (if using Alembic) and start the API:
    ```bash
    uvicorn app.main:app --reload