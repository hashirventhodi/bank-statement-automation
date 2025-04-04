from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import tempfile

from app.core.document_analyzer import DocumentAnalyzer
from app.core.extractors.pdf_extractor import PDFExtractor
from app.core.extractors.image_extractor import ImageExtractor
from app.core.extractors.csv_extractor import CSVExtractor
from app.core.parsers.transaction_parser import TransactionParser
from app.core.parsers.ml_parser import MLParser
from app.core.normalizer import TransactionNormalizer
from app.core.validator import TransactionValidator, StatementValidator
from app.database.repositories.statement_repository import StatementRepository
from app.database.repositories.transaction_repository import TransactionRepository
from app.models.statement import Statement, ProcessingStatus
from app.models.transaction import Transaction
from app.utils.logger import logger

class StatementProcessor:
    """Handles background processing of bank statements."""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.document_analyzer = DocumentAnalyzer({})  # Initialize with bank templates
        self.normalizer = TransactionNormalizer()
        self.validator = TransactionValidator()
        
    async def process_statement_async(self, statement_id: int, db_session) -> None:
        """Process a statement asynchronously."""
        try:
            # Get statement from database
            statement_repo = StatementRepository(db_session)
            statement = statement_repo.get(statement_id)
            
            if not statement:
                logger.error(f"Statement {statement_id} not found")
                return
                
            # Update status
            statement.processing_status = ProcessingStatus.PROCESSING
            statement_repo.update(statement)
            
            # Process in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._process_statement,
                statement,
                db_session
            )
            
        except Exception as e:
            logger.error(f"Error processing statement {statement_id}: {str(e)}")
            try:
                statement.processing_status = ProcessingStatus.FAILED
                statement.error_message = str(e)
                statement_repo.update(statement)
            except:
                pass
    
    def _process_statement(self, statement: Statement, db_session) -> None:
        """Process statement in background thread."""
        try:
            # Analyze document structure
            analysis = self.document_analyzer.analyze_structure(
                statement.file_path,
                statement.file_format
            )
            
            # Select appropriate extractor
            extractor = self._get_extractor(
                statement.file_format,
                analysis.get("detected_template")
            )
            
            # Extract data in chunks
            extracted_data = self._extract_in_chunks(
                extractor,
                statement.file_path
            )
            
            # Process transactions in batches
            self._process_transactions_in_batches(
                extracted_data,
                statement,
                db_session
            )
            
            # Update statement metadata
            self._update_statement_metadata(
                statement,
                extracted_data.get("metadata", {}),
                db_session
            )
            
            # Cleanup
            self._cleanup_temporary_files(statement.file_path)
            
        except Exception as e:
            logger.error(f"Error in statement processing: {str(e)}")
            statement.processing_status = ProcessingStatus.FAILED
            statement.error_message = str(e)
            StatementRepository(db_session).update(statement)
    
    def _get_extractor(self, file_format, template=None):
        """Get appropriate extractor for file format."""
        if file_format == "PDF":
            return PDFExtractor(template=template)
        elif file_format == "IMAGE":
            return ImageExtractor()
        else:
            return CSVExtractor(template=template)
    
    def _extract_in_chunks(self, extractor, file_path: str, chunk_size: int = 1000) -> Dict[str, Any]:
        """Extract data in chunks to handle large files."""
        extracted_data = {
            "metadata": {},
            "transactions": []
        }
        
        try:
            # Extract metadata first
            initial_extract = extractor.extract(file_path, limit=1)
            extracted_data["metadata"] = initial_extract.get("metadata", {})
            
            # Extract transactions in chunks
            offset = 0
            while True:
                chunk = extractor.extract(
                    file_path,
                    offset=offset,
                    limit=chunk_size
                )
                
                if not chunk.get("transactions"):
                    break
                    
                extracted_data["transactions"].extend(chunk["transactions"])
                offset += chunk_size
                
                if len(chunk["transactions"]) < chunk_size:
                    break
                    
        except Exception as e:
            logger.error(f"Error extracting in chunks: {str(e)}")
            raise
            
        return extracted_data
    
    def _process_transactions_in_batches(
        self,
        extracted_data: Dict[str, Any],
        statement: Statement,
        db_session,
        batch_size: int = 500
    ) -> None:
        """Process and save transactions in batches."""
        try:
            parser = MLParser()  # or TransactionParser() based on preference
            tx_repo = TransactionRepository(db_session)
            
            transactions = extracted_data.get("transactions", [])
            total_batches = (len(transactions) + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min((batch_num + 1) * batch_size, len(transactions))
                batch = transactions[start_idx:end_idx]
                
                # Parse batch
                parsed_batch = parser.parse(batch)
                
                # Normalize batch
                normalized_batch = self.normalizer.normalize_transactions(parsed_batch)
                
                # Create transaction records
                batch_records = []
                for tx_data in normalized_batch:
                    transaction = Transaction(**tx_data)
                    transaction.statement_id = statement.id
                    batch_records.append(transaction)
                
                # Bulk insert
                tx_repo.bulk_create(batch_records)
                
        except Exception as e:
            logger.error(f"Error processing transactions in batches: {str(e)}")
            raise
    
    def _update_statement_metadata(
        self,
        statement: Statement,
        metadata: Dict[str, Any],
        db_session
    ) -> None:
        """Update statement with extracted metadata."""
        try:
            statement.bank_name = metadata.get("bank_name")
            
            if metadata.get("statement_period"):
                start_date, end_date = metadata["statement_period"].split(" to ")
                statement.statement_period_start = datetime.strptime(start_date.strip(), "%d/%m/%Y")
                statement.statement_period_end = datetime.strptime(end_date.strip(), "%d/%m/%Y")
            
            statement.opening_balance = metadata.get("opening_balance")
            statement.closing_balance = metadata.get("closing_balance")
            statement.processing_status = ProcessingStatus.COMPLETED
            statement.processed_at = datetime.utcnow()
            
            StatementRepository(db_session).update(statement)
            
        except Exception as e:
            logger.error(f"Error updating statement metadata: {str(e)}")
            raise
    
    def _cleanup_temporary_files(self, file_path: str) -> None:
        """Clean up temporary files."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary file: {str(e)}")