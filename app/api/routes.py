from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import tempfile
import os
from datetime import datetime

from app.core.document_analyzer import DocumentAnalyzer
from app.core.extractors.pdf_extractor import PDFExtractor
from app.core.extractors.image_extractor import ImageExtractor
from app.core.extractors.csv_extractor import CSVExtractor
from app.core.parsers.transaction_parser import TransactionParser
from app.core.parsers.ml_parser import MLParser
from app.core.normalizer import TransactionNormalizer
from app.core.validator import TransactionValidator, StatementValidator
from app.database.db import get_db
from app.models.statement import Statement, StatementFormat, ProcessingStatus
from app.models.transaction import Transaction
from app.database.repositories.statement_repository import StatementRepository
from app.database.repositories.transaction_repository import TransactionRepository
from app.utils.logger import logger

router = APIRouter()

ALLOWED_EXTENSIONS = {
    '.pdf': StatementFormat.PDF,
    '.jpg': StatementFormat.IMAGE,
    '.jpeg': StatementFormat.IMAGE,
    '.png': StatementFormat.IMAGE,
    '.csv': StatementFormat.CSV,
    '.xlsx': StatementFormat.EXCEL,
    '.xls': StatementFormat.EXCEL
}

@router.post("/statements/upload")
async def upload_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    account_id: int = None,
    use_ml: bool = False,
    db: Session = Depends(get_db)
):
    """
    Upload and process a bank statement.
    
    Args:
        file: The statement file
        account_id: Optional account ID to associate with
        use_ml: Whether to use ML-enhanced parsing
        db: Database session
    """
    try:
        # Validate file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Create statement record
        statement_repo = StatementRepository(db)
        statement = Statement(
            account_id=account_id,
            file_name=file.filename,
            file_path=temp_path,
            file_format=ALLOWED_EXTENSIONS[file_ext],
            processing_status=ProcessingStatus.PENDING
        )
        statement = statement_repo.create(statement)
        
        # Schedule background processing
        background_tasks.add_task(
            process_statement,
            statement_id=statement.id,
            file_path=temp_path,
            use_ml=use_ml,
            db=db
        )
        
        return {"message": "Statement upload accepted", "statement_id": statement.id}
        
    except Exception as e:
        logger.error(f"Error in statement upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/statements/{statement_id}")
def get_statement_status(statement_id: int, db: Session = Depends(get_db)):
    """Get the processing status and results of a statement."""
    try:
        statement_repo = StatementRepository(db)
        statement = statement_repo.get(statement_id)
        
        if not statement:
            raise HTTPException(status_code=404, detail="Statement not found")
        
        # Get associated transactions if processing is complete
        transactions = []
        if statement.processing_status == ProcessingStatus.COMPLETED:
            tx_repo = TransactionRepository(db)
            transactions = tx_repo.get_by_statement(statement_id)
            transactions = [tx.to_dict() for tx in transactions]
        
        return {
            "statement": statement.to_dict(),
            "transactions": transactions if statement.processing_status == ProcessingStatus.COMPLETED else None
        }
        
    except Exception as e:
        logger.error(f"Error getting statement status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/statements/{statement_id}/verify")
def verify_statement(statement_id: int, db: Session = Depends(get_db)):
    """Verify a processed statement's transactions."""
    try:
        statement_repo = StatementRepository(db)
        statement = statement_repo.get(statement_id)
        
        if not statement:
            raise HTTPException(status_code=404, detail="Statement not found")
            
        if statement.processing_status != ProcessingStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Statement processing not completed")
        
        tx_repo = TransactionRepository(db)
        transactions = tx_repo.get_by_statement(statement_id)
        
        # Create validators
        tx_validator = TransactionValidator()
        statement_validator = StatementValidator(tx_validator)
        
        # Prepare data for validation
        statement_data = {
            "metadata": {
                "account_number": statement.account.account_number if statement.account else None,
                "statement_period": f"{statement.statement_period_start.strftime('%d/%m/%Y')} to {statement.statement_period_end.strftime('%d/%m/%Y')}" if statement.statement_period_start and statement.statement_period_end else None,
                "opening_balance": statement.opening_balance,
                "closing_balance": statement.closing_balance
            },
            "transactions": [tx.to_dict() for tx in transactions]
        }
        
        # Validate
        validation_result = statement_validator.validate_statement(statement_data)
        
        # Update statement and transactions based on validation
        statement.processing_status = ProcessingStatus.VALIDATED if validation_result["is_valid"] else ProcessingStatus.FAILED
        statement_repo.update(statement)
        
        # Update transaction statuses
        for tx_data in validation_result["transactions"]:
            tx = next((t for t in transactions if t.id == tx_data["id"]), None)
            if tx:
                tx.status = tx_data["status"]
                tx.validation_errors = tx_data.get("validation_errors", [])
                tx_repo.update(tx)
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error verifying statement: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_statement(statement_id: int, file_path: str, use_ml: bool, db: Session):
    """Background task for processing statements."""
    try:
        # Get statement record
        statement_repo = StatementRepository(db)
        statement = statement_repo.get(statement_id)
        
        if not statement:
            logger.error(f"Statement {statement_id} not found")
            return
        
        # Update status to processing
        statement.processing_status = ProcessingStatus.PROCESSING
        statement_repo.update(statement)
        
        # Initialize components
        document_analyzer = DocumentAnalyzer(bank_templates={})  # Load templates as needed
        normalizer = TransactionNormalizer()
        parser = MLParser() if use_ml else TransactionParser()
        
        # Analyze document
        file_format = statement.file_format
        analysis = document_analyzer.analyze_structure(file_path, file_format)
        
        # Select appropriate extractor
        if file_format == StatementFormat.PDF:
            extractor = PDFExtractor(template=analysis.get("detected_template"))
        elif file_format == StatementFormat.IMAGE:
            extractor = ImageExtractor()
        else:
            extractor = CSVExtractor(template=analysis.get("detected_template"))
        
        # Extract data
        extracted_data = extractor.extract(file_path)
        
        # Parse transactions
        parsed_transactions = parser.parse(extracted_data["transactions"])
        
        # Normalize transactions
        normalized_transactions = normalizer.normalize_transactions(parsed_transactions)
        
        # Create transaction records
        tx_repo = TransactionRepository(db)
        for tx_data in normalized_transactions:
            transaction = Transaction(**tx_data)
            transaction.statement_id = statement_id
            tx_repo.create(transaction)
        
        # Update statement metadata
        metadata = extracted_data.get("metadata", {})
        statement.bank_name = metadata.get("bank_name")
        statement.statement_period_start = datetime.strptime(metadata["statement_period"].split(" to ")[0], "%d/%m/%Y") if metadata.get("statement_period") else None
        statement.statement_period_end = datetime.strptime(metadata["statement_period"].split(" to ")[1], "%d/%m/%Y") if metadata.get("statement_period") else None
        statement.opening_balance = metadata.get("opening_balance")
        statement.closing_balance = metadata.get("closing_balance")
        statement.processing_status = ProcessingStatus.COMPLETED
        statement.processed_at = datetime.utcnow()
        
        statement_repo.update(statement)
        
        # Cleanup temporary file
        try:
            os.remove(file_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error processing statement {statement_id}: {str(e)}")
        try:
            statement.processing_status = ProcessingStatus.FAILED
            statement.error_message = str(e)
            statement_repo.update(statement)
        except:
            pass